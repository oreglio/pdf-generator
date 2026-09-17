"""PDF assembly. Shared task destinations are independent of day numbers."""

from dataclasses import replace
from pathlib import Path

from reportlab.pdfgen import canvas

from planner_config import TYPOGRAPHIES
from planner_layout import make_layout
from planner_manifest import build_manifest, preview_specs
from planner_pages import PlannerPages


def generate_pdf(config, target):
    if isinstance(target, (str, Path)):
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target = str(target)
    pdf = canvas.Canvas(target, pagesize=make_layout(config).pagesize,
                        pageCompression=1, invariant=1, pdfVersion=(1, 4))
    pdf.setTitle(config.title)
    pdf.setAuthor("AiPaper Planner")
    pdf.setSubject(config.text("Meetings non datés et tâches partagées - Viwoods AiPaper"))
    pages = PlannerPages(pdf, config)
    manifest = build_manifest(config)
    for spec in manifest:
        pages.draw(spec)
    if pages.ordinal != len(manifest):
        raise RuntimeError("Le nombre de pages générées ne correspond pas à la configuration.")
    pdf.save()
    return pages.ordinal


def generate_samples(config, target):
    """Three visual-only pages: no dangling destinations to omitted pages."""
    pdf = canvas.Canvas(str(target) if isinstance(target, Path) else target,
                        pagesize=make_layout(config).pagesize, pageCompression=1, invariant=1)
    pdf.setTitle(config.text("Aperçu - ") + config.title)
    pages = PlannerPages(pdf, config, interactive=False)
    for spec in preview_specs(build_manifest(config), "undated"):
        pages.draw(spec)
    pdf.save()
    return pages.ordinal


def generate_comparison(config, target):
    """Ten visual-only pages with the same layouts at the same physical size."""
    pdf = canvas.Canvas(str(target) if isinstance(target, Path) else target,
                        pagesize=make_layout(config).pagesize, pageCompression=1, invariant=1)
    pdf.setTitle(config.text("AiPaper - comparaison des polices"))
    page = PlannerPages(pdf, config, interactive=False)
    LEFT, RIGHT, WIDTH, PAGE_HEIGHT = page.left, page.right, page.width, page.h
    page.start("comparison")
    page.header(config.text("VIWOODS AIPAPER / ESSAI TYPOGRAPHIQUE"), config.text("Trois façons de lire."))
    page.text(LEFT, PAGE_HEIGHT - 119, config.text("Même format. Même contenu. Trois rendus."), 11)
    entries = (("01", "Manrope", config.text("Pages 2 à 4 / fin et équilibré.")),
               ("02", config.text("Manrope contraste"), config.text("Pages 5 à 7 / traits plus présents.")),
               ("03", "Atkinson Hyperlegible Next", config.text("Pages 8 à 10 / lettres très différenciées.")))
    for i, (number, title, description) in enumerate(entries):
        y = PAGE_HEIGHT - 190 - i * 78
        page.text(LEFT, y, number, 12, gray=0.4)
        page.text(LEFT + 35, y, title, 16, bold=True, max_width=WIDTH - 35)
        page.text(LEFT + 35, y - 22, description, 9, gray=0.35)
        page.line(LEFT, y - 40, RIGHT, y - 40)
    page.text(LEFT, 139, config.text("Sur la tablette"), 13, bold=True)
    for i, line in enumerate((
        config.text("Affichez une page entière, avec le même zoom pour les trois essais."),
        config.text("Comparez les petits numéros, les onglets et les lignes d’écriture."),
        config.text("Ces pages comparent le rendu : leurs onglets ne sont pas actifs."),
        config.text("Pour tester les liens, ouvrez l’un des trois carnets complets."),
    )):
        page.text(LEFT, 116 - i * 17, line, 9, max_width=WIDTH)
    page.end()
    ordinal = 1
    for key, label in TYPOGRAPHIES.items():
        current = replace(config, typography=key)
        page = PlannerPages(pdf, current, interactive=False)
        page.ordinal = ordinal
        manifest = build_manifest(current)
        for kind in ("meeting", "task-list", "task-notes"):
            page.draw(next(spec for spec in manifest if spec.kind == kind))
        ordinal += 3
    pdf.save()
