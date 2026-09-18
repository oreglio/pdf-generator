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
import base64
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageFilter
from PIL.PngImagePlugin import PngInfo
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

import note_archive


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


# --- grafting into the notebook the tablet itself made ---------------------

def note_identity(archive, names):
    """The notebook's own name and identifier, as the archive states them."""
    entry = next((name for name in names if name.endswith("NoteFileInfo.json")), None)
    if entry is None:
        raise ValueError("Cette archive ne dit pas quel carnet elle décrit : "
                         "elle ne vient pas d’un carnet AiPaper.")
    info = json.loads(archive.read(entry))
    return info["fileName"], info["id"]


def template_entry(names):
    """The archive member holding the PDF the notebook was written on."""
    found = [name for name in names if name.lower().endswith(".pdf")]
    if len(found) != 1:
        raise ValueError("Cette archive ne contient pas exactement un gabarit PDF : "
                         "elle ne vient pas d’un carnet AiPaper.")
    return found[0]


def move_layer(data, dx, dy):
    """The same transparent canvas, with the ink slid across it."""
    layer = Image.open(io.BytesIO(data))
    moved = Image.new(layer.mode, layer.size, (0, 0, 0, 0))
    moved.paste(layer, (dx, dy))
    keep, index = PngInfo(), 8
    while index < len(data):   # keep the chunks the tablet writes beside the pixels
        size = int.from_bytes(data[index:index + 4], "big")
        kind = data[index + 4:index + 8]
        if kind in (b"sRGB", b"sBIT", b"gAMA", b"cHRM", b"pHYs"):
            keep.add(kind, data[index + 8:index + 8 + size])
        index += 12 + size
    buffer = io.BytesIO()
    moved.save(buffer, format="PNG", pnginfo=keep)
    return buffer.getvalue()


def move_strokes(data, dx, dy):
    """Every recorded point slid by the same amount.

    The first two numbers of each point are its screen coordinates — rasterising
    them reproduces the handwriting exactly. What the third holds, and how the
    points group into strokes, stays unknown; moving them all by one offset does
    not need to know, because nothing is reordered and nothing is regrouped.
    """
    points = json.loads(data)
    for point in points:
        point[0] += dx
        point[1] += dy
    return json.dumps(points, separators=(",", ":")).encode()


def written_pages(source):
    """{page: share of ink} for a `.note`, ignoring pages opened but left blank."""
    with zipfile.ZipFile(Path(source)) as ink:
        declared = note_archive.resources(ink)
        present = set(ink.namelist())
        found = {}
        for page, kinds in declared.items():
            name = kinds.get(note_archive.LAYER)
            if name in present:
                share = coverage(Image.open(io.BytesIO(ink.read(name))).convert("RGBA"))
                if share > 0:
                    found[page] = share
    return found


def inventory(source):
    """What a written notebook holds, in the order it holds it.

    Returns [(section, [(page, label, share of ink), …]), …] — sections in page
    order, which is reading order. Thumbnails are deliberately left out: they
    cost a second per handful of pages, and a notebook filled for a year has
    hundreds. They are drawn for the section being looked at.
    """
    pages = written_pages(source)
    named = page_sections(source, pages)
    sections = []
    for page in sorted(pages):
        section, label = named[page]
        if not sections or sections[-1][0] != section:
            sections.append((section, []))
        sections[-1][1].append((page, label, pages[page]))
    return sections


def page_previews(source, pages, width=260):
    """A thumbnail of the handwriting itself, as a data URI, for each page.

    Cropped to the ink rather than shrunk from the whole sheet: a page is
    mostly blank, and a postage stamp of blankness tells nobody anything.
    """
    previews = {}
    with zipfile.ZipFile(Path(source)) as ink:
        declared = note_archive.resources(ink)
        present = set(ink.namelist())
        for page in pages:
            name = declared.get(page, {}).get(note_archive.LAYER)
            if name not in present:
                continue
            layer = Image.open(io.BytesIO(ink.read(name))).convert("RGBA")
            box = layer.getbbox()
            if box is None:
                continue
            margin = 24
            box = (max(0, box[0] - margin), max(0, box[1] - margin),
                   min(layer.width, box[2] + margin), min(layer.height, box[3] + margin))
            crop = layer.crop(box)
            sheet = Image.new("RGB", crop.size, "white")
            sheet.paste(crop, mask=crop)
            height = max(1, round(sheet.height * width / sheet.width))
            sheet = sheet.resize((width, min(height, width * 2)), Image.LANCZOS)
            buffer = io.BytesIO()
            sheet.save(buffer, format="PNG", optimize=True)
            previews[page] = ("data:image/png;base64,"
                              + base64.b64encode(buffer.getvalue()).decode())
    return previews


def page_sections(source, pages):
    """Name each page after its outline entry, and the section that holds it.

    A list of page numbers says nothing three weeks later. The template carries
    the notebook's own bookmarks, so « 53 » becomes « Mer 16 septembre 2026 »
    under « Septembre 2026 ». Starting a new period, one rarely wants the whole
    of the old notebook — one wants its backlog, or its projects, or a single
    list. The section is the grain that choice is made in.

    The section comes from the outline tree, never from page order: a week's
    pages sit after the last month in the file while belonging to neither.
    """
    import bisect
    with zipfile.ZipFile(Path(source)) as archive:
        reader = PdfReader(io.BytesIO(archive.read(note_archive.template_entry(archive))))
        flat = []

        def walk(items, depth=0, inherited=None):
            """Carry the second-level title down the tree, never up the pages."""
            section = inherited
            for item in items:
                if isinstance(item, list):
                    walk(item, depth + 1, section)
                    continue
                try:
                    page = reader.get_destination_page_number(item)
                except Exception:  # noqa: BLE001 — a stale bookmark is not fatal
                    continue
                # A month, a week, a backlog list, the projects: the second
                # level is the unit. Deeper entries inherit the one above them.
                section = item.title if depth <= 1 else (inherited or item.title)
                flat.append((page, section, item.title))

        try:
            walk(reader.outline)
        except Exception:  # noqa: BLE001 — a notebook without bookmarks still works
            flat = []
    flat.sort(key=lambda entry: entry[0])
    starts = [entry[0] for entry in flat]
    named = {}
    for page in sorted(pages):
        index = bisect.bisect_right(starts, page - 1) - 1
        if index < 0:
            named[page] = ("Carnet", f"Page {page}")
            continue
        _, section, label = flat[index]
        offset = page - 1 - flat[index][0]
        named[page] = (section, label if not offset else f"{label} +{offset}")
    return named


def graft_note(source, target, output, report=print, pages=None):
    """Add the handwriting of one notebook to one the tablet has just made.

    The tablet will not install a template it does not already have, and refuses
    any archive whose bytes it did not write — recompressing one, contents
    unchanged, is enough to have it rejected. So the new edition is imported on
    the tablet first, exported empty, and that export is what receives the ink:
    its notebook, its template, its identifiers, its bytes. Every page it holds
    already declares a layer and a stroke file; only the contents are missing.
    """
    source, target, output = Path(source), Path(target), Path(output)
    for path, role in ((source, "le carnet écrit"), (target, "le nouveau carnet")):
        if not zipfile.is_zipfile(path):
            raise ValueError(f"Pour garder des tracés modifiables, {role} doit être "
                             "une archive .note de la tablette.")
    with zipfile.ZipFile(source) as ink, zipfile.ZipFile(target) as base:
        dx, dy = graft_offset(ink, base, output, report)
        written, declared = note_archive.resources(ink), note_archive.resources(base)
        present, taken = set(ink.namelist()), set(base.namelist())
        wanted = None if pages is None else set(pages)
        added, grafted = [], set()
        for page in sorted(written):
            if wanted is not None and page not in wanted:
                continue
            slots = declared.get(page, {})
            # A page the tablet wrote itself keeps everything it has: grafting
            # old strokes under a newer layer would leave the two disagreeing.
            if any(slots.get(kind) in taken for kind in
                   (note_archive.LAYER, note_archive.STROKES)):
                continue
            for kind in (note_archive.LAYER, note_archive.STROKES):
                name = written[page].get(kind)
                slot = slots.get(kind)
                if name not in present or slot is None:
                    continue
                data = ink.read(name)
                if (dx, dy) != (0, 0):
                    data = (move_layer(data, dx, dy) if kind == note_archive.LAYER
                            else move_strokes(data, dx, dy))
                added.append((slot, data))
                grafted.add(page)
        if not added:
            raise ValueError(f"{source.name} : aucune page écrite à reporter, ou le "
                             "nouveau carnet n’a pas les mêmes pages.")
    report(f"{len(grafted)} page(s) greffée(s) : "
           + ", ".join(str(page) for page in sorted(grafted)))
    total = note_archive.append(target, output, added)
    report(f"Carnet de la tablette conservé octet pour octet ; {len(added)} fichiers "
           f"ajoutés, {total} entrées au total.")
    report(f"→ {output} ({output.stat().st_size / 1e6:.1f} Mo)")
    return sorted(grafted)


def graft_offset(ink, base, output, report):
    """How far the new edition moved its writing column, in panel pixels."""
    holders = []
    try:
        for archive in (ink, base):
            holder = output.with_suffix(f".gabarit-{len(holders)}.pdf")
            holder.write_bytes(archive.read(note_archive.template_entry(archive)))
            holders.append(holder)
        report("Calage sur le carnet d’origine :")
        dx, dy, spread = measure(holders[0], False, holders[1], [1, 2], report)
    finally:
        for holder in holders:
            holder.unlink(missing_ok=True)
    report(f"Décalage retenu : {dx / PANEL_DPI * 25.4:+.2f} × "
           f"{dy / PANEL_DPI * 25.4:+.2f} mm"
           + (f" (dispersion {spread:.0f} px)" if spread else " (unanime)"))
    return round(dx), round(dy)


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


def carry(source, target, output, offset_mm=None, report=print, pages=None):
    """Carry handwriting over, in the shape the destination asks for.

    A `.note` destination is a notebook the tablet just made: the ink is grafted
    into it and stays strokes. A PDF destination receives the ink as an image.
    """
    if zipfile.is_zipfile(Path(target)):
        return graft_note(source, target, output, report=report, pages=pages)
    return transfer(source, target, output, offset_mm, report=report)


def transfer_report(source, target, output, offset_mm=None, pages=None):
    """`carry`, with its commentary returned instead of printed.

    A worker process has nowhere to print, so the lines come back together
    with the result for whoever asked.
    """
    lines = []
    done = carry(source, target, output, offset_mm, report=lines.append, pages=pages)
    return done, lines


def parse_pages(text):
    """« 268-374,2279 » as a set of page numbers, or None for everything."""
    if not text:
        return None
    chosen = set()
    for part in text.replace(" ", "").split(","):
        if not part:
            continue
        bounds = part.split("-")
        try:
            first = int(bounds[0])
            last = int(bounds[-1]) if len(bounds) <= 2 else None
        except ValueError:
            last = None
        if last is None or first < 1 or last < first:
            raise ValueError(f"Sélection de pages illisible : « {part} ». "
                             "Attendu : 12, ou 12-30, séparés par des virgules.")
        chosen.update(range(first, last + 1))
    return chosen or None


def print_inventory(source):
    for section, rows in inventory(source):
        print(f"{section}  ({len(rows)} page(s))")
        for page, label, share in rows:
            print(f"    {page:>6}  {share:5.2f} %  {label}")


def main():
    parser = argparse.ArgumentParser(
        description="Reporter l’écriture d’un carnet AiPaper sur une nouvelle édition.")
    parser.add_argument("--from", dest="source", type=Path, required=True,
                        help="Archive .note de la tablette, ou PDF exporté aplati")
    parser.add_argument("--into", type=Path,
                        help="PDF régénéré, ou archive .note que la tablette vient "
                             "d’exporter — auquel cas les tracés restent modifiables")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pages",
                        help="Ne reprendre que ces pages : « 268-374,2279-2282 ». "
                             "Par défaut, toutes les pages écrites")
    parser.add_argument("--list", action="store_true",
                        help="Afficher ce que le carnet écrit contient, par section, "
                             "sans rien produire")
    parser.add_argument("--offset-mm", type=float,
                        help="Décalage horizontal imposé, au lieu du calage automatique")
    args = parser.parse_args()
    try:
        if args.list:
            print_inventory(args.source)
            return
        if not args.into or not args.output:
            parser.error("--into et --output sont requis, sauf avec --list.")
        carry(args.source, args.into, args.output, args.offset_mm,
              pages=parse_pages(args.pages))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    sys.exit(main())
