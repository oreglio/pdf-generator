"""PDF assembly. Shared task destinations are independent of day numbers."""

from dataclasses import replace
from pathlib import Path

from reportlab.pdfgen import canvas

from planner_config import PAGE_HEIGHT, PAGE_WIDTH, TYPOGRAPHIES
from planner_pages import PlannerPages, LEFT, RIGHT, WIDTH


def generate_pdf(config, target):
    if isinstance(target, (str, Path)):
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target = str(target)
    pdf = canvas.Canvas(target, pagesize=(PAGE_WIDTH, PAGE_HEIGHT),
                        pageCompression=1, invariant=1, pdfVersion=(1, 4))
    pdf.setTitle(config.title)
    pdf.setAuthor("AiPaper Planner")
    pdf.setSubject("Meetings non datés et tâches partagées - Viwoods AiPaper")
    pages = PlannerPages(pdf, config)
    pages.home()
    for block in range(config.index_pages):
        pages.day_index(block)
    for day in range(1, config.days + 1):
        pages.meeting(day)
        for number in range(1, config.notes_pages + 1):
            pages.meeting_notes(day, number)
    for number in range(1, config.list_count + 1):
        pages.task_list(number)
        for item in range(1, config.tasks_per_list + 1):
            for part in range(1, config.detail_pages + 1):
                pages.task_notes(number, item, part)
    if pages.ordinal != config.total_pages:
        raise RuntimeError("Le nombre de pages générées ne correspond pas à la configuration.")
    pdf.save()
    return pages.ordinal


def generate_samples(config, target):
    """Three visual-only pages: no dangling destinations to omitted pages."""
    pdf = canvas.Canvas(str(target) if isinstance(target, Path) else target,
                        pagesize=(PAGE_WIDTH, PAGE_HEIGHT), pageCompression=1, invariant=1)
    pdf.setTitle("Aperçu - " + config.title)
    pages = PlannerPages(pdf, config, interactive=False)
    pages.meeting(1)
    pages.task_list(1)
    pages.task_notes(1, 1, 1)
    pdf.save()


def generate_comparison(config, target):
    """Ten visual-only pages with the same layouts at the same physical size."""
    pdf = canvas.Canvas(str(target) if isinstance(target, Path) else target,
                        pagesize=(PAGE_WIDTH, PAGE_HEIGHT), pageCompression=1, invariant=1)
    pdf.setTitle("AiPaper - comparaison des polices")
    page = PlannerPages(pdf, config, interactive=False)
    page.start("comparison")
    page.header("VIWOODS AIPAPER / ESSAI TYPOGRAPHIQUE", "Trois façons de lire.")
    page.text(LEFT, PAGE_HEIGHT - 119, "Même format. Même contenu. Trois rendus.", 11)
    entries = (("01", "Manrope", "Pages 2 à 4 / fin et équilibré."),
               ("02", "Manrope contraste", "Pages 5 à 7 / traits plus présents."),
               ("03", "Atkinson Hyperlegible Next", "Pages 8 à 10 / lettres très différenciées."))
    for i, (number, title, description) in enumerate(entries):
        y = PAGE_HEIGHT - 190 - i * 78
        page.text(LEFT, y, number, 12, gray=0.4)
        page.text(LEFT + 35, y, title, 16, bold=True, max_width=WIDTH - 35)
        page.text(LEFT + 35, y - 22, description, 9, gray=0.35)
        page.line(LEFT, y - 40, RIGHT, y - 40)
    page.text(LEFT, 139, "Sur la tablette", 13, bold=True)
    for i, line in enumerate((
        "Affichez une page entière, avec le même zoom pour les trois essais.",
        "Comparez les petits numéros, les onglets et les lignes d’écriture.",
        "Ces pages comparent le rendu : leurs onglets ne sont pas actifs.",
        "Pour tester les liens, ouvrez l’un des trois carnets complets.",
    )):
        page.text(LEFT, 116 - i * 17, line, 9, max_width=WIDTH)
    page.end()
    ordinal = 1
    for key, label in TYPOGRAPHIES.items():
        current = replace(config, typography=key)
        page = PlannerPages(pdf, current, interactive=False)
        page.ordinal = ordinal
        for draw in (lambda: page.meeting(1), lambda: page.task_list(1), lambda: page.task_notes(1, 1, 1)):
            draw()
        ordinal += 3
    pdf.save()
