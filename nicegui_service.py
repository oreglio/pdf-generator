"""Picklable planner operations, independent of either UI framework."""

from dataclasses import dataclass, replace
from datetime import datetime
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


def file_stem(label: str) -> str:
    """A profile name turned into something a file system will accept."""
    kept = ''.join(character if character.isalnum() or character in '-_' else ' '
                   for character in label)
    return '-'.join(kept.split())[:64]


def stamped_name(filename: str, label: str | None = None,
                 moment: datetime | None = None) -> str:
    """The download name: the profile it came from, and when it was made.

    A carnet regenerated four times in an afternoon is four files called the
    same thing. The stamp tells them apart, and the profile name says which
    set of settings produced this one — which the generated name never did.
    """
    stem = file_stem(label or '') or Path(filename).stem
    when = (moment or datetime.now()).strftime('%Y%m%d%H%M%S')
    return f'{stem}-{when}.pdf'


def generate_artifact(mode: str, payload: dict, *, samples: bool = False,
                      short: bool = False, compact: bool = False,
                      label: str | None = None) -> PDFArtifact:
    if type(samples) is not bool or type(short) is not bool or type(compact) is not bool:
        raise ValueError("Les options samples, short et compact doivent être des booléens.")
    if short and (samples or mode != 'undated'):
        raise ValueError("Le carnet court concerne uniquement le PDF non daté complet.")
    config = parse_config(mode, payload)
    if short:
        config = replace(config, days=min(config.days, 3))
    output = BytesIO()
    if samples:
        # The preview draws one page per section: the manifest says how many.
        if mode == 'dated':
            pages = generate_dated_samples(config, output)
            filename = f'aipaper-dated-preview-{config.base.language}.pdf'
        else:
            pages = generate_samples(config, output)
            filename = ('aipaper-apercu.pdf' if config.language == 'fr'
                        else 'aipaper-preview-en.pdf')
    else:
        engine = generate_dated_pdf if mode == 'dated' else generate_pdf
        pages = engine(config, output)
        filename = config.pdf_filename
    data = output.getvalue()
    if compact and not samples:   # An eight-page preview has nothing to gain.
        import pdf_compact
        data = pdf_compact.compact(data, report=lambda line: None)
    if not samples:
        filename = stamped_name(filename, label)
    return PDFArtifact(data, filename, pages)


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
