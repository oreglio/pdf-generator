"""Carry the handwriting of a Viwoods AiPaper notebook over to a new edition.

Two sources are accepted, and they are not equal.

A `.note` archive is the tablet's own format: JSON metadata, the template PDF
it was written on, and one `mainBmp_*.png` per written page — the ink alone,
black on a fully transparent background, at the panel's 1920 × 2560. Nothing is
reconstructed and nothing is lost. Prefer it.

An exported PDF is the fallback. The app flattens each written page into one
opaque full-page JPEG covering the printed layout as well as the ink, so the
ink has to be recovered by subtracting the page as it was printed. It works —
the vector page survives underneath — but it costs a lossy round trip.

The archive is read, never written: the format is undocumented and the tablet
should stay the only thing that authors it. The ink lands in a PDF, which is
what the tablet knows how to open.

Pages are matched by index, which both sources state outright. When the new
edition moved the layout — a reserved toolbar band, another device — the offset
is measured by phase correlation over the writing column, so the ink falls back
onto its lines instead of beside them.
"""

import argparse
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageFilter
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


PANEL_DPI = 300
SAMPLE_DPI = 150
MM = 72 / 25.4
# The tablet's renderer does not anti-alias like ours, so every printed edge
# would survive a plain subtraction. Growing the background by this much wipes
# the haloes; a stroke crossing a rule loses a pixel or two, which nobody sees.
BACKGROUND_GROWTH = 5
INK_THRESHOLD = 60


# --- sources ---------------------------------------------------------------

def read_archive(path):
    """Ink layers of a `.note`, as {page: RGBA image}, with its template PDF."""
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())

        def load(suffix):
            for name in names:
                if name.endswith(suffix):
                    return json.loads(archive.read(name))
            raise ValueError(f"{Path(path).name} : {suffix} introuvable, "
                             "ce n’est pas une archive AiPaper.")

        order = {entry["id"]: entry["order"] for entry in load("PageListFileInfo.json")}
        layers = {}
        for entry in load("PageResource.json"):
            name = entry.get("fileName", "")
            # Every page declares a layer; only the written ones ship a file.
            if not name.startswith("mainBmp_") or name not in names:
                continue
            page = order.get(entry.get("pid"))
            if page is not None:
                layers[page + 1] = Image.open(io.BytesIO(archive.read(name))).convert("RGBA")
        template = next((n for n in names if n.lower().endswith(".pdf")), None)
        if template is None:
            raise ValueError(f"{Path(path).name} : aucun gabarit PDF dans l’archive.")
        return layers, archive.read(template)


def stamped_pages(pdf):
    """Pages the tablet flattened: the appended stream draws a full-page image."""
    reader = PdfReader(str(pdf))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        contents = page.get("/Contents")
        contents = contents if isinstance(contents, list) else getattr(contents, "get_object",
                                                                      lambda: None)()
        if isinstance(contents, list) and len(contents) > 1:
            pages.append(index)
    return pages


def read_flattened(path, report):
    """Ink recovered from an exported PDF, by subtracting the printed page."""
    pages = stamped_pages(path)
    if not pages:
        raise ValueError(f"{Path(path).name} : aucune page écrite. Exportez plutôt "
                         "l’archive .note, qui garde l’encre sur un calque à part.")
    report(f"PDF aplati : {len(pages)} page(s) à reconstituer par soustraction.")
    layers = {}
    for page in pages:
        printed = Image.fromarray(render(path, page, PANEL_DPI, clean=True)
                                  .astype(np.uint8)).convert("L")
        flattened = Image.fromarray(render(path, page, PANEL_DPI).astype(np.uint8)).convert("L")
        # Ink is positive here, so growing the printed marks is a maximum
        # filter; a minimum filter would eat them and let the layout through.
        grown = printed.filter(ImageFilter.MaxFilter(BACKGROUND_GROWTH))
        # Both images carry ink as positive values, so the difference is the
        # ink the flattened page has and the printed page never had.
        alpha = ImageChops.subtract(flattened, grown).point(
            lambda value: 0 if value < INK_THRESHOLD else min(255, int(value * 255 / 200)))
        layer = Image.new("RGBA", alpha.size, (0, 0, 0, 0))
        layer.putalpha(alpha)
        layers[page] = layer
    return layers, Path(path).read_bytes()


def read_source(path, report):
    path = Path(path)
    if zipfile.is_zipfile(path):
        return read_archive(path)
    return read_flattened(path, report)


# --- alignment -------------------------------------------------------------

def render(pdf, page, dpi, clean=False):
    """One page as an array, ink positive; `clean` leaves every image out."""
    command = ["gs", "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pnggray", f"-r{dpi}",
               f"-dFirstPage={page}", f"-dLastPage={page}", "-sOutputFile=-", str(pdf)]
    if clean:
        command.insert(-1, "-dFILTERIMAGE")
    try:
        out = subprocess.run(command, capture_output=True, check=True).stdout
    except FileNotFoundError:
        raise ValueError("Ghostscript est introuvable : installez-le "
                         "(brew install ghostscript), ou imposez le décalage.") from None
    return 255.0 - np.asarray(Image.open(io.BytesIO(out)).convert("L"), dtype=np.float64)


def writing_area(page):
    """The page without its navigation rail, where the handwriting lives.

    The rail is anchored to the sheet, so it stays put when a left-hand band
    pushes everything else across: correlating on the whole page would answer
    that nothing moved. The writing column answers the question that matters —
    where the ink has to land.
    """
    height, width = page.shape
    return page[int(height * 0.08):int(height * 0.92), :int(width * 0.82)]


def shift(before, after):
    """Translation in pixels carrying `before` onto `after`, by phase correlation."""
    if before.shape != after.shape:
        raise ValueError("Les deux carnets n’ont pas la même définition de page : "
                         "régénérez le nouveau pour le même appareil.")
    before, after = writing_area(before), writing_area(after)
    spectrum = np.fft.rfft2(after) * np.conj(np.fft.rfft2(before))
    spectrum /= np.abs(spectrum) + 1e-9
    correlation = np.fft.irfft2(spectrum, before.shape)
    peak = np.unravel_index(np.argmax(correlation), before.shape)
    height, width = before.shape
    return (peak[1] - width if peak[1] > width // 2 else peak[1],
            peak[0] - height if peak[0] > height // 2 else peak[0])


def measure(template, clean, target, pages, report):
    """The offset between the two editions, agreed on by several pages."""
    found = []
    for page in pages:
        try:
            dx, dy = shift(render(template, page, SAMPLE_DPI, clean=clean),
                           render(target, page, SAMPLE_DPI))
        except (subprocess.CalledProcessError, ValueError) as error:
            report(f"  page {page} : calage impossible ({error})")
            continue
        found.append((dx, dy))
        report(f"  page {page} : {dx:+d}, {dy:+d} px")
    if not found:
        raise ValueError("Aucune page n’a pu être calée : imposez le décalage.")
    scale = PANEL_DPI / SAMPLE_DPI
    dx = float(np.median([point[0] for point in found])) * scale
    dy = float(np.median([point[1] for point in found])) * scale
    spread = max(max(abs(point[0] * scale - dx), abs(point[1] * scale - dy))
                 for point in found)
    return dx, dy, spread


# --- transfer --------------------------------------------------------------

def coverage(layer):
    return 100.0 * (np.asarray(layer)[..., 3] > 0).sum() / (layer.width * layer.height)


def overlay(layer, box, dx, dy):
    """A one-page PDF holding the ink alone, shifted onto the new layout."""
    width, height = box
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(width, height))
    pdf.drawImage(ImageReader(layer), dx * 72 / PANEL_DPI, -dy * 72 / PANEL_DPI,
                  width, height, mask="auto")
    pdf.showPage()
    pdf.save()
    return PdfReader(io.BytesIO(buffer.getvalue())).pages[0]


def transfer(source, target, output, offset_mm=None, report=print):
    """Report the handwriting of `source` onto `target`, saving to `output`."""
    source, target, output = Path(source), Path(target), Path(output)
    layers, template = read_source(source, report)
    written = {page: layer for page, layer in layers.items() if coverage(layer) > 0}
    blank = sorted(set(layers) - set(written))
    if not written:
        raise ValueError(f"{source.name} : aucune page écrite dans ce carnet.")
    report(f"{len(written)} page(s) écrite(s) : "
           + ", ".join(str(page) for page in sorted(written)))
    if blank:
        report("Ignorées, car vides : " + ", ".join(str(page) for page in blank))

    reader = PdfReader(str(target))
    highest = max(written)
    if highest > len(reader.pages):
        raise ValueError(f"{target.name} ne compte que {len(reader.pages)} pages, "
                         f"alors que l’encre va jusqu’à la page {highest}. Régénérez "
                         "le carnet avec les mêmes réglages de durée, de backlog et "
                         "de projets.")

    if offset_mm is not None:
        dx, dy = offset_mm * MM * PANEL_DPI / 72, 0.0
        report(f"Décalage imposé : {offset_mm:+.2f} mm horizontal.")
    else:
        holder = output.with_suffix(".gabarit.pdf")
        holder.write_bytes(template)
        try:
            report("Calage sur le carnet d’origine :")
            dx, dy, spread = measure(holder, source.suffix.lower() == ".pdf", target,
                                     sorted(written)[:3], report)
        finally:
            holder.unlink(missing_ok=True)
        report(f"Décalage retenu : {dx / PANEL_DPI * 25.4:+.2f} × "
               f"{dy / PANEL_DPI * 25.4:+.2f} mm"
               + (f" (dispersion {spread:.0f} px)" if spread else " (unanime)"))
        if spread > 4:
            report("  Les pages ne s’accordent pas sur le décalage : vérifiez le "
                   "résultat, ou imposez-le à la main.")

    # An incremental update keeps the original bytes and appends only the pages
    # that changed: cloning a 2 400-page object graph exhausts the interpreter
    # stack, and would rewrite every link and bookmark for nothing.
    writer = PdfWriter(str(target), incremental=True)
    for page, layer in sorted(written.items()):
        target_page = writer.pages[page - 1]
        box = (float(target_page.mediabox.width), float(target_page.mediabox.height))
        target_page.merge_page(overlay(layer, box, dx, dy))
        report(f"  page {page:>5} · {coverage(layer):5.2f} % d’encre reportée")
    with open(output, "wb") as handle:
        writer.write(handle)
    report(f"→ {output} ({output.stat().st_size / 1e6:.1f} Mo)")
    return sorted(written)


def transfer_report(source, target, output, offset_mm=None):
    """`transfer`, with its running commentary returned instead of printed.

    A worker process has nowhere to print, so the lines come back together
    with the result for whoever asked.
    """
    lines = []
    pages = transfer(source, target, output, offset_mm, report=lines.append)
    return pages, lines


def main():
    parser = argparse.ArgumentParser(
        description="Reporter l’écriture d’un carnet AiPaper sur une nouvelle édition.")
    parser.add_argument("--from", dest="source", type=Path, required=True,
                        help="Archive .note de la tablette, ou PDF exporté aplati")
    parser.add_argument("--into", type=Path, required=True,
                        help="PDF régénéré qui doit recevoir l’encre")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offset-mm", type=float,
                        help="Décalage horizontal imposé, au lieu du calage automatique")
    args = parser.parse_args()
    try:
        transfer(args.source, args.into, args.output, args.offset_mm)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    sys.exit(main())
