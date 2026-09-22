# Ray Issue #47439 Reproduction Container

This directory contains a Docker-based reproduction of the Ray placement-group
deadlock described in https://github.com/ray-project/ray/issues/47439.

## Quick Start

```bash
cd ray-repro
docker compose up --build
```

The container runs `reproduce_47439.py` which:

1. Initializes a 4-CPU Ray cluster
2. Creates a parent placement group reserving all 4 CPUs (PACK: [{"CPU": 1}, {"CPU": 3}])
3. From inside an actor belonging to the parent PG, requests a 3-CPU child placement group
4. Waits up to 90s for the child PG to become ready
5. Dumps evidence: `ray status`, placement-group table, resource accounting, logs

All captured output is saved under `evidence/` (mounted from the host).

## Reproducing

```bash
cd "/home/nsaivighnesh/Downloads/capstone project/ray-repro"
docker compose up --build
```

## Cleanup

```bash
docker compose down -v --remove-orphans
```

## Files

- `docker-compose.yml` — container orchestration
- `Dockerfile` — builds the reproduction image
- `reproduce_47439.py` — the reproduction script (runs inside the container)
- `evidence/` — captured output (host-mounted, persists after container stops)
