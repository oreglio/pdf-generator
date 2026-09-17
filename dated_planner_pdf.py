"""Assembly of dated planners; deliberately separate from planner_pdf."""

from pathlib import Path

from reportlab.pdfgen import canvas

from dated_planner_pages import DatedPlannerPages
from planner_layout import make_layout
from planner_manifest import build_manifest, preview_specs


def _canvas(config, target):
    if isinstance(target, (str, Path)):
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target = str(target)
    pdf = canvas.Canvas(target, pagesize=make_layout(config.render_config).pagesize,
                        pageCompression=1, invariant=1, pdfVersion=(1, 4))
    pdf.setTitle(config.base.title)
    pdf.setAuthor("AiPaper Planner")
    pdf.setSubject(f"Dated planner / {config.start_date} - {config.end_date.isoformat()}")
    return pdf


def generate_dated_pdf(config, target):
    pdf = _canvas(config, target)
    pages = DatedPlannerPages(pdf, config)
    manifest = build_manifest(config)
    for spec in manifest:
        pages.draw(spec)
    if pages.ordinal != len(manifest):
        raise RuntimeError("Le nombre de pages datées ne correspond pas à la configuration.")
    pdf.save()
    return pages.ordinal


def generate_dated_samples(config, target):
    pdf = _canvas(config, target)
    pages = DatedPlannerPages(pdf, config, interactive=False)
    for spec in preview_specs(build_manifest(config), "dated"):
        pages.draw(spec)
    pdf.save()
    return pages.ordinal
