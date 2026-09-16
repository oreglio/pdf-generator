"""Assembly of dated planners; deliberately separate from planner_pdf."""

from pathlib import Path

from reportlab.pdfgen import canvas

from dated_planner_pages import DatedPlannerPages
from planner_config import PAGE_WIDTH, PAGE_HEIGHT


def _canvas(config, target):
    if isinstance(target, (str, Path)):
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target = str(target)
    pdf = canvas.Canvas(target, pagesize=(PAGE_WIDTH, PAGE_HEIGHT),
                        pageCompression=1, invariant=1, pdfVersion=(1, 4))
    pdf.setTitle(config.base.title)
    pdf.setAuthor("AiPaper Planner")
    pdf.setSubject(f"Dated planner / {config.start_date} - {config.end_date.isoformat()}")
    return pdf


def generate_dated_pdf(config, target):
    pdf = _canvas(config, target)
    pages = DatedPlannerPages(pdf, config)
    pages.home()
    for index in range(len(config.calendar_months)):
        pages.calendar(index)
    for monday in config.weeks:
        for part in range(1, config.week_pages + 1):
            pages.weekly(monday, part)
    for day in range(1, len(config.dates) + 1):
        pages.meeting(day)
        for part in range(1, config.base.notes_pages + 1):
            pages.meeting_notes(day, part)
    for number in range(1, config.base.list_count + 1):
        pages.task_list(number)
        for item in range(1, config.base.tasks_per_list + 1):
            for part in range(1, config.base.detail_pages + 1):
                pages.task_notes(number, item, part)
    if pages.ordinal != config.total_pages:
        raise RuntimeError("Le nombre de pages datées ne correspond pas à la configuration.")
    pdf.save()
    return pages.ordinal


def generate_dated_samples(config, target):
    pdf = _canvas(config, target)
    pages = DatedPlannerPages(pdf, config, interactive=False)
    pages.calendar(0)
    pages.weekly(config.weeks[0], 1)
    pages.meeting(1)
    pages.task_list(1)
    pages.task_notes(1, 1, 1)
    pdf.save()
