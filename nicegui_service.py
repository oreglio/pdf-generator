"""Picklable planner operations, independent of either UI framework."""

from dataclasses import dataclass, replace
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from dated_planner_config import DatedPlannerConfig
from dated_planner_pdf import generate_dated_pdf, generate_dated_samples
from planner_config import PlannerConfig
from planner_pdf import generate_pdf, generate_samples


@dataclass(frozen=True)
class PDFArtifact:
    pdf_bytes: bytes
    filename: str
    pages: int


def _validate_object(payload):
    if not isinstance(payload, dict) or any(not isinstance(key, str) for key in payload):
        raise ValueError("La configuration doit être un objet JSON avec des clés texte.")


def parse_config(mode: str, payload: dict) -> PlannerConfig | DatedPlannerConfig:
    if not isinstance(mode, str) or mode not in ('dated', 'undated'):
        raise ValueError("Le mode doit être dated ou undated.")
    _validate_object(payload)
    if mode == 'dated':
        if 'base' in payload:
            _validate_object(payload['base'])
        return DatedPlannerConfig.from_dict(payload)
    return PlannerConfig.from_dict(payload)


def generate_artifact(mode: str, payload: dict, *, samples: bool = False,
                      short: bool = False) -> PDFArtifact:
    if type(samples) is not bool or type(short) is not bool:
        raise ValueError("Les options samples et short doivent être des booléens.")
    if short and (samples or mode != 'undated'):
        raise ValueError("Le carnet court concerne uniquement le PDF non daté complet.")
    config = parse_config(mode, payload)
    if short:
        config = replace(config, days=min(config.days, 3))
    output = BytesIO()
    if samples:
        if mode == 'dated':
            generate_dated_samples(config, output)
            filename = f'aipaper-dated-preview-{config.base.language}.pdf'
            pages = 5
        else:
            generate_samples(config, output)
            filename = ('aipaper-apercu.pdf' if config.language == 'fr'
                        else 'aipaper-preview-en.pdf')
            pages = 3
    else:
        engine = generate_dated_pdf if mode == 'dated' else generate_pdf
        pages = engine(config, output)
        filename = config.pdf_filename
    return PDFArtifact(output.getvalue(), filename, pages)


def render_preview(pdf_bytes: bytes, page: int = 1) -> bytes:
    """Render one 1-based page; delete all temporary PDF and image files afterwards."""
    if not isinstance(pdf_bytes, bytes) or not pdf_bytes.startswith(b'%PDF-'):
        raise ValueError("Un document PDF valide est requis pour l’aperçu.")
    if type(page) is not int or page < 1:
        raise ValueError("Le numéro de page doit être un entier positif.")

    from pdf2image import convert_from_path, pdfinfo_from_path
    from pdf2image.exceptions import PDFPageCountError

    with TemporaryDirectory(prefix='aipaper-preview-') as directory:
        pdf_path = Path(directory) / 'planner.pdf'
        pdf_path.write_bytes(pdf_bytes)
        try:
            page_count = pdfinfo_from_path(pdf_path, timeout=15)['Pages']
        except PDFPageCountError as exc:
            raise ValueError("Impossible de lire ce document PDF.") from exc
        if page > page_count:
            raise ValueError("La page demandée n’existe pas dans ce document PDF.")
        images = convert_from_path(
            pdf_path, first_page=page, last_page=page, fmt='png',
            output_folder=directory, output_file='preview', paths_only=True,
            single_file=True, thread_count=1, size=1200, timeout=30,
        )
        if len(images) != 1:
            raise ValueError("La page demandée n’a pas pu être rendue.")
        return Path(images[0]).read_bytes()
