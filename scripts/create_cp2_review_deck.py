"""Create the CINT-11 CP-2 Review-II deck from the team's reference deck.

The reference deck is intentionally used as a template so the slide count,
section order, footer, spacing, and visual language match the review format.
Replace the bracketed team/guide metadata on slide 1 before submission.
"""

from copy import deepcopy
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.util import Inches


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path("/home/nsaivighnesh/Downloads/CLOUD-04_CSE-2_Review-II.pptx")
OUTPUT = PROJECT_ROOT / "download" / "CINT-11_CP2_Review-II.pptx"
REVIEW_DATE = "23-09-2026"
FOOTER = "Review-II                                                        Department of CSE-2"


def set_text(slide, shape_index: int, text: str) -> None:
    """Replace a template text box's content without changing its geometry/style."""
    shape = slide.shapes[shape_index]
    if not shape.has_text_frame:
        raise TypeError(f"Shape {shape_index} on slide is not a text shape")

    # python-pptx's ``text_frame.text = ...`` creates a new run and drops
    # direct formatting from the template. Capture the first run's visual
    # style, then replace only the content so the reference deck remains the
    # visual template.
    old_runs = [run for paragraph in shape.text_frame.paragraphs for run in paragraph.runs]
    source = old_runs[0] if old_runs else None
    font_props = {}
    if source is not None:
        font = source.font
        font_props = {
            "name": font.name,
            "size": font.size,
            "bold": font.bold,
            "italic": font.italic,
            "underline": font.underline,
        }
        try:
            font_props["rgb"] = font.color.rgb
        except (AttributeError, ValueError):
            font_props["rgb"] = None
        try:
            font_props["theme_color"] = font.color.theme_color
        except (AttributeError, ValueError):
            font_props["theme_color"] = None

    shape.text_frame.clear()
    paragraph = shape.text_frame.paragraphs[0]
    run = paragraph.add_run()
    run.text = text
    if source is not None:
        run.font.name = font_props["name"]
        run.font.size = font_props["size"]
        run.font.bold = font_props["bold"]
        run.font.italic = font_props["italic"]
        run.font.underline = font_props["underline"]
        if font_props["rgb"] is not None:
            run.font.color.rgb = font_props["rgb"]
        elif font_props["theme_color"] is not None:
            run.font.color.theme_color = font_props["theme_color"]
    shape.text_frame.word_wrap = True


def clone_text_box(
    slide,
    source_index: int,
    left_in: float,
    top_in: float,
    width_in: float | None = None,
    height_in: float | None = None,
) -> int:
    """Clone a text box from the reference slide and return its new index."""
    source = slide.shapes[source_index]
    element = deepcopy(source._element)
    slide.shapes._spTree.append(element)
    clone = slide.shapes[-1]
    clone.left = Inches(left_in)
    clone.top = Inches(top_in)
    if width_in is not None:
        clone.width = Inches(width_in)
    if height_in is not None:
        clone.height = Inches(height_in)
    existing_ids = [shape.shape_id for shape in slide.shapes if shape is not clone]
    new_id = max(existing_ids) + 1
    clone._element.nvSpPr.cNvPr.id = new_id
    clone._element.nvSpPr.cNvPr.name = f"TextBox {new_id}"
    return len(slide.shapes) - 1


def set_common(slide, slide_number: int) -> None:
    # The template uses these same indices on every slide.
    set_text(slide, 1 if slide_number in (2, 3, 4, 5, 6, 7, 8) else 1, REVIEW_DATE)
    set_text(slide, 2, FOOTER)
    # Keep the existing slide number shape; explicitly setting it avoids stale
    # numbering if the template is edited later.
    set_text(slide, 3, str(slide_number))


def update_chart(slide) -> None:
    """Replace the reference FinOps chart with CP-2 policy counts."""
    chart = slide.shapes[16].chart
    data = CategoryChartData()
    data.categories = ["Completed", "Unresolved", "Rejected"]
    data.add_series("FIFO", (5, 7, 0))
    data.add_series("Greedy", (7, 5, 0))
    data.add_series("Deadlock-aware", (7, 0, 5))
    chart.replace_data(data)
    chart.has_legend = True
    chart.legend.include_in_layout = False
    chart.value_axis.has_major_gridlines = True
    chart.value_axis.maximum_scale = 8
    chart.value_axis.minimum_scale = 0
    chart.value_axis.major_unit = 2


def build() -> Path:
    if not TEMPLATE.exists():
        raise FileNotFoundError(TEMPLATE)

    prs = Presentation(str(TEMPLATE))
    if len(prs.slides) != 12:
        raise ValueError(f"Expected 12 reference slides, found {len(prs.slides)}")

    # Slide 1 — title / team metadata.
    s = prs.slides[0]
    set_text(s, 0, REVIEW_DATE)
    set_text(s, 1, FOOTER)
    set_text(s, 2, "1")
    set_text(s, 3, "REVIEW-II")
    set_text(s, 4, "NestedTune Guard: Deadlock-Aware Distributed Hyperparameter Tuning for Nested Trainers")
    set_text(s, 5, "Project ID: CINT-11  |  Batch: CSE-2")
    set_text(s, 6, "KONERU LAKSHMAIAH EDUCATION FOUNDATION")
    # The supplied team list is four members. Put the user/presenter first,
    # then preserve the remaining order from the supplied image.
    set_text(s, 10, "2300030455")
    set_text(s, 11, "NEKKANTI SAI VIGHNESH")
    set_text(s, 12, "Member")
    set_text(s, 13, "2300030062")
    set_text(s, 14, "BAGADI PAVAN KUMAR")
    set_text(s, 15, "2300030983")
    set_text(s, 16, "BHIMISETTY MAHESH ADITHYA")

    # Add the missing fourth row and role labels while keeping the reference
    # deck's typography and alignment.
    role_row_2 = clone_text_box(s, 12, 6.56, 4.10, 0.98, 0.30)
    set_text(s, role_row_2, "Member")
    role_row_3 = clone_text_box(s, 12, 6.56, 4.62, 0.98, 0.30)
    set_text(s, role_row_3, "Member")
    reg_row_4 = clone_text_box(s, 10, 1.18, 5.14, 1.52, 0.30)
    name_row_4 = clone_text_box(s, 11, 2.78, 5.14, 4.20, 0.32)
    role_row_4 = clone_text_box(s, 12, 6.56, 5.14, 0.98, 0.30)
    set_text(s, reg_row_4, "2300031256")
    set_text(s, name_row_4, "CHOPPARAPU JESWANTH VARUN")
    set_text(s, role_row_4, "Member")
    set_text(s, 21, "8199")
    set_text(s, 23, "Mr.Rambabu Kalathoti")

    # Slide 2 — preserve the reference outline and update its chrome.
    s = prs.slides[1]
    set_text(s, 1, REVIEW_DATE)
    set_text(s, 2, FOOTER)
    set_text(s, 3, "2")

    # Slide 3 — introduction.
    s = prs.slides[2]
    set_text(s, 1, REVIEW_DATE)
    set_text(s, 2, FOOTER)
    set_text(s, 3, "3")
    set_text(s, 6, "WHY NESTED TUNING?")
    set_text(s, 7, "Outer trial owns parent PG\nInner training requests child PG\nParent can hold resources child needs")
    set_text(s, 10, "PROJECT RESPONSE")
    set_text(s, 11, "Model nested resource demand\nCompare FIFO, Greedy, Deadlock-aware\nMeasure cycles and unresolved trials\nReproduce on Ray 2.10.0")
    set_text(s, 12, "THE RESULT IS MEASURABLE")
    set_text(s, 13, "4/4/1/3")
    set_text(s, 14, "real-Ray resource accounting")
    set_text(s, 15, "70")
    set_text(s, 16, "automated tests passed")
    set_text(s, 17, "0")
    set_text(s, 18, "unresolved CP-2 deadlocks")

    # Slide 4 — problem and objectives.
    s = prs.slides[3]
    set_text(s, 1, REVIEW_DATE)
    set_text(s, 2, FOOTER)
    set_text(s, 3, "4")
    set_text(s, 6, "PROBLEM STATEMENT")
    set_text(s, 7, "Parent placement group can reserve the whole cluster\nNested child cannot be admitted although aggregate capacity looks sufficient\nFIFO and Greedy are hierarchy-blind\nUnbounded hangs are hard to compare or test")
    set_text(s, 8, "Four measurable objectives")
    set_text(s, 9, "01")
    set_text(s, 10, "Model hierarchy")
    set_text(s, 11, "Parent + child placement")
    set_text(s, 12, "02")
    set_text(s, 13, "Compare policies")
    set_text(s, 14, "FIFO vs Greedy")
    set_text(s, 15, "03")
    set_text(s, 16, "Prevent deadlocks")
    set_text(s, 17, "Reject / defer unsafe fit")
    set_text(s, 18, "04")
    set_text(s, 19, "Produce evidence")
    set_text(s, 20, "30s bound + metrics + trace")

    # Slide 5 — requirements and acceptance.
    s = prs.slides[4]
    set_text(s, 1, REVIEW_DATE)
    set_text(s, 2, FOOTER)
    set_text(s, 3, "5")
    set_text(s, 4, "FUNCTIONAL REQUIREMENTS")
    set_text(s, 5, "FR-1")
    set_text(s, 6, "Validate workloads")
    set_text(s, 7, "Schema + 7 dev fixtures")
    set_text(s, 8, "FR-2")
    set_text(s, 9, "Simulate hierarchy")
    set_text(s, 10, "Atomic parent + child")
    set_text(s, 11, "FR-3")
    set_text(s, 12, "Compare policies")
    set_text(s, 13, "FIFO / Greedy / CP-2")
    set_text(s, 14, "FR-4")
    set_text(s, 15, "Prevent unsafe admission")
    set_text(s, 16, "Reject / defer / recover")
    set_text(s, 17, "FR-5")
    set_text(s, 18, "Expose evidence")
    set_text(s, 19, "API + dashboard + reports")
    set_text(s, 20, "NON-FUNCTIONAL REQUIREMENTS")
    set_text(s, 22, "NFR-1")
    set_text(s, 23, "Deterministic output")
    set_text(s, 25, "NFR-2")
    set_text(s, 26, "30-second bounded execution")
    set_text(s, 28, "NFR-3")
    set_text(s, 29, "Docker + pinned Ray 2.10.0")
    set_text(s, 31, "NFR-4")
    set_text(s, 32, "CI validates; no prod claim")
    set_text(s, 33, "Acceptance: 70 tests + oracle + frozen CP-1 + CP-2 result")

    # Slide 6 — alternatives plus literature basis.
    s = prs.slides[5]
    set_text(s, 1, REVIEW_DATE)
    set_text(s, 2, FOOTER)
    set_text(s, 3, "6")
    set_text(s, 5, "BASELINE 1 · FIFO")
    set_text(s, 6, "FIFO baseline")
    set_text(s, 7, "Simple arrival-order reference")
    set_text(s, 8, "Head-of-line blocking; hierarchy-blind")
    set_text(s, 10, "BASELINE 2 · GREEDY")
    set_text(s, 11, "Greedy / backfilling")
    set_text(s, 12, "Skips blocked head; improves throughput")
    set_text(s, 13, "Still admits unsafe parent-only fits")
    set_text(s, 15, "CP-2 CONTROLLER")
    set_text(s, 16, "Deadlock-aware policy")
    set_text(s, 17, "Checks parent + child before admission")
    set_text(s, 18, "Rejects infeasible; defers unsafe; explains why")
    set_text(s, 19, "Research basis: Ray [1] • Tune [2] • DRF [3] • deadlock detection [4] • Hyperband/ASHA [5][6]")

    # Slide 7 — architecture.
    s = prs.slides[6]
    set_text(s, 1, REVIEW_DATE)
    set_text(s, 2, FOOTER)
    set_text(s, 3, "7")
    set_text(s, 6, "JSON fixtures")
    set_text(s, 7, "Cluster + trials")
    set_text(s, 11, "Validation")
    set_text(s, 12, "Schema checks")
    set_text(s, 16, "Simulator")
    set_text(s, 17, "0.1s ticks")
    set_text(s, 21, "Policy engine")
    set_text(s, 22, "FIFO • Greedy • CP-2")
    set_text(s, 26, "Telemetry")
    set_text(s, 27, "Cycles + stranding")
    set_text(s, 31, "API + UI")
    set_text(s, 32, "FastAPI + Next.js")
    set_text(s, 33, "Frozen CP-1 baseline → CP-2 controller → evidence")
    set_text(s, 34, "Python • FastAPI • Next.js • Docker • K8s • Helm • Ray 2.10")

    # Slide 8 — detailed flow.
    s = prs.slides[7]
    set_text(s, 1, REVIEW_DATE)
    set_text(s, 2, FOOTER)
    set_text(s, 3, "8")
    set_text(s, 5, "INPUT")
    set_text(s, 6, "Workload JSON")
    set_text(s, 7, "Capacity | arrival | duration | parent/child bundles")
    set_text(s, 10, "INTELLIGENCE")
    set_text(s, 11, "Simulation tick")
    set_text(s, 12, "Policy decides → parent admit → child fit → state/event")
    set_text(s, 15, "OUTPUT")
    set_text(s, 16, "Evidence + interfaces")
    set_text(s, 17, "JSON/CSV/PNG | /health /scenarios /simulate /benchmark /validate")
    set_text(s, 18, "WAITING_CHILD → observer self-cycle → CP-2 reject/defer → bounded result")

    # Slide 9 — implementation status.
    s = prs.slides[8]
    set_text(s, 1, REVIEW_DATE)
    set_text(s, 2, FOOTER)
    set_text(s, 3, "9")
    set_text(s, 4, "10 review deliverables implemented")
    rows = [
        (7, 9, "Schema + fixtures", "Verified"),
        (10, 12, "Simulator + telemetry", "Verified"),
        (13, 15, "FIFO / Greedy baselines", "Verified"),
        (16, 18, "Deadlock-aware controller", "Verified"),
        (19, 21, "Oracle + deterministic gate", "70 PASS"),
        (22, 24, "FastAPI + advisor", "Verified"),
        (25, 27, "Next.js dashboard", "Built"),
        (28, 30, "Ray 2.10 Docker repro", "Verified"),
        (31, 33, "K8s + Helm packaging", "CI PASS"),
        (34, 36, "Viva metadata / literature", "Pending"),
    ]
    for name_idx, status_idx, name, status in rows:
        set_text(s, name_idx, name)
        set_text(s, status_idx, status)
    set_text(s, 37, "Next critical path: rehearse the viva, fill names/guide, read the cited papers, and choose a venue.")

    # Slide 10 — results.
    s = prs.slides[9]
    set_text(s, 1, REVIEW_DATE)
    set_text(s, 2, FOOTER)
    set_text(s, 3, "10")
    set_text(s, 4, "5/12")
    set_text(s, 5, "FIFO baseline")
    set_text(s, 6, "7 unresolved")
    set_text(s, 7, "7/12")
    set_text(s, 8, "Greedy baseline")
    set_text(s, 9, "5 unresolved")
    set_text(s, 10, "7/12")
    set_text(s, 11, "CP-2 completed")
    set_text(s, 12, "0 unresolved")
    set_text(s, 13, "70/70")
    set_text(s, 14, "pytest")
    set_text(s, 15, "14/14 oracle + gate")
    update_chart(s)
    set_text(s, 17, "CP-2 policy comparison (counts across 12 trials)")
    set_text(s, 20, "REAL-RAY EVIDENCE")
    set_text(s, 21, "Ray 2.10.0: child PG PENDING for 91.8s | 4 total / 4 reserved / 1 useful / 3 stranded")

    # Slide 11 — conclusion and next work.
    s = prs.slides[10]
    set_text(s, 1, REVIEW_DATE)
    set_text(s, 2, FOOTER)
    set_text(s, 3, "11")
    set_text(s, 4, "CONCLUSION")
    set_text(s, 5, "CP-1 establishes FIFO and Greedy baselines.\nCP-2 checks parent + child before admission.\nUnresolved cases become explicit rejections: 7/5 → 0 unresolved.\nValidated by simulator evidence and a Ray 2.10.0 reproduction.")
    set_text(s, 6, "FUTURE SCOPE / COMPLETION PLAN")
    set_text(s, 7, "W1")
    set_text(s, 8, "Read papers + literature review")
    set_text(s, 10, "W2")
    set_text(s, 11, "Fill team/guide + rehearse demo")
    set_text(s, 13, "W3")
    set_text(s, 14, "Test newer Ray / multi-node")
    set_text(s, 16, "W4")
    set_text(s, 17, "Add traces and workload diversity")
    set_text(s, 19, "W5")
    set_text(s, 20, "Submit preprint or workshop paper")
    set_text(s, 22, "Limitation: the simulator is deterministic and atomic; real multi-node production behavior remains future work.")

    # Slide 12 — closing.
    s = prs.slides[11]
    set_text(s, 0, REVIEW_DATE)
    set_text(s, 1, FOOTER)
    set_text(s, 2, "12")
    set_text(s, 3, "THANK YOU")
    set_text(s, 4, "NestedTune Guard")
    set_text(s, 5, "Questions & Discussion")
    set_text(s, 6, "Project ID CINT-11  |  Batch: CSE-2")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUTPUT))
    return OUTPUT


if __name__ == "__main__":
    print(build())
