"""Wait-for observer — independent cycle detection.

The observer is the heart of the CP-1 evaluation framework. It builds a
wait-for graph from trial dependencies and detects cycles via DFS.

CRITICAL DESIGN CONSTRAINT: the observer is observer-only. It never
modifies scheduling decisions. This is what keeps the CP-1 baseline fair
and prevents CP-2 behaviour from leaking into the baseline results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..model import Trial


@dataclass
class WaitForEdge:
    """A directed edge `waiter -> holder` in the wait-for graph."""

    waiter: str  # trial id that is waiting
    holder: str  # trial id that holds the resource

    def __repr__(self) -> str:
        return f"{self.waiter} -> {self.holder}"


@dataclass
class Cycle:
    """A detected wait-for cycle."""

    members: tuple[str, ...]  # trial ids in the cycle
    edges: tuple[WaitForEdge, ...]
    kind: str  # "self_cycle" or "mutual"


@dataclass
class ObserverResult:
    """A snapshot of the wait-for graph and detected cycles."""

    edges: list[WaitForEdge] = field(default_factory=list)
    cycles: list[Cycle] = field(default_factory=list)

    @property
    def cycle_count(self) -> int:
        return len(self.cycles)

    def to_dict(self) -> dict:
        return {
            "edges": [{"waiter": e.waiter, "holder": e.holder} for e in self.edges],
            "cycles": [
                {
                    "members": list(c.members),
                    "edges": [{"waiter": e.waiter, "holder": e.holder} for e in c.edges],
                    "kind": c.kind,
                }
                for c in self.cycles
            ],
            "cycle_count": self.cycle_count,
        }


def build_wait_for_graph(trials: list["Trial"]) -> list[WaitForEdge]:
    """Build the wait-for graph from trial states.

    An edge `waiter -> holder` exists iff:
      - `waiter` is in WAITING_PARENT or WAITING_CHILD state, AND
      - `holder` currently holds a placement group that `waiter` is
        waiting for. With our nested-trainer model, a child PG that
        cannot be admitted is a self-edge back to the parent (because
        the parent's PG is what makes the child infeasible).
    """
    edges: list[WaitForEdge] = []
    for t in trials:
        # Only consider trials that are actively waiting.
        from ..model import TrialState
        if t.state not in (TrialState.WAITING_CHILD, TrialState.WAITING_PARENT):
            continue
        # Self-cycle: child cannot be admitted because the parent's PG
        # is holding the resources the child needs. In Ray #47439 this is
        # the canonical case — the parent is WAITING_CHILD and the child
        # request can never succeed because the parent itself holds the
        # CPUs the child needs.
        if t.state == TrialState.WAITING_CHILD and t.parent_pg is not None:
            edges.append(WaitForEdge(waiter=t.id, holder=t.id))
        elif t.state == TrialState.WAITING_PARENT and t.parent_pg is not None:
            # Parent PG is pending because some other trial holds resources.
            # In our model this never actually happens (parents are admitted
            # or trials stay PENDING) but we record the edge for completeness.
            edges.append(WaitForEdge(waiter=t.id, holder=t.id))
    return edges


def detect_cycles(edges: list[WaitForEdge]) -> list[Cycle]:
    """Detect all simple cycles in the wait-for graph.

    For our model the only kind of cycle is a self-cycle (a trial waiting
    on itself) — this is the exact deadlock condition from Ray #47439.
    But we implement general cycle detection anyway, so the observer is
    honest about whatever topology the simulator actually produces.
    """
    # Build adjacency list
    adjacency: dict[str, list[str]] = {}
    for e in edges:
        adjacency.setdefault(e.waiter, []).append(e.holder)

    cycles: list[Cycle] = []
    seen_signatures: set[tuple[str, ...]] = set()

    # Detect self-cycles directly (most common case in our model)
    for e in edges:
        if e.waiter == e.holder:
            cycle = Cycle(
                members=(e.waiter,),
                edges=(e,),
                kind="self_cycle",
            )
            sig = (e.waiter,)
            if sig not in seen_signatures:
                cycles.append(cycle)
                seen_signatures.add(sig)

    # General cycle detection via DFS for non-self cycles
    # (covers mutual wait-for between two distinct trials, which our
    # current fixtures do not exercise but the observer should still
    # detect honestly).
    color: dict[str, str] = {}  # white/grey/black
    stack: list[str] = []

    def dfs(node: str) -> None:
        color[node] = "grey"
        stack.append(node)
        for neighbor in adjacency.get(node, []):
            if neighbor == node:
                continue  # self-cycle handled above
            if color.get(neighbor) == "grey":
                # Found a back-edge → cycle. Extract the cycle from the stack.
                try:
                    start_idx = stack.index(neighbor)
                except ValueError:
                    continue
                cycle_members = tuple(stack[start_idx:])
                # Normalize signature (rotate to start with smallest id).
                sig = _normalize_signature(cycle_members)
                if sig in seen_signatures:
                    continue
                seen_signatures.add(sig)
                # Build edge list
                cycle_edges: list[WaitForEdge] = []
                for i in range(len(cycle_members)):
                    a = cycle_members[i]
                    b = cycle_members[(i + 1) % len(cycle_members)]
                    cycle_edges.append(WaitForEdge(waiter=a, holder=b))
                cycles.append(Cycle(
                    members=cycle_members,
                    edges=tuple(cycle_edges),
                    kind="mutual",
                ))
            elif color.get(neighbor) is None:
                dfs(neighbor)
        stack.pop()
        color[node] = "black"

    for node in list(adjacency.keys()):
        if color.get(node) is None:
            dfs(node)

    return cycles


def _normalize_signature(members: tuple[str, ...]) -> tuple[str, ...]:
    """Rotate a cycle's member tuple so it starts with the lexicographically
    smallest id — this makes equivalent cycles (same members, different
    starting point) compare equal for deduplication."""
    if not members:
        return members
    min_idx = min(range(len(members)), key=lambda i: members[i])
    return members[min_idx:] + members[:min_idx]


def observe(trials: list["Trial"]) -> ObserverResult:
    """Build the wait-for graph and detect cycles for the given trial set."""
    edges = build_wait_for_graph(trials)
    cycles = detect_cycles(edges)
    return ObserverResult(edges=edges, cycles=cycles)
