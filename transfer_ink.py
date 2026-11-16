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

Pages are matched by what they are — the bookmark that names them — never by
their number: a new period moves the backlog and the projects dozens of pages
away. When the new edition moved the layout — a reserved toolbar band, another
device — the offset is measured by phase correlation over the writing column,
between pages that were matched, so the ink falls back onto its lines.
"""

import argparse
import base64
import io
import json
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
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
# Panel pixels two sampled pages may disagree by before the journal says so.
SPREAD_TOLERANCE = 4


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


# Decoding one panel-sized layer costs 55 ms, and a notebook filled for a year
# holds hundreds: read serially, the inventory would take half a minute. The
# compressed size looked like a shortcut — a blank layer from the tablet
# deflates to 267 bytes against 23 kB for the lightest written one — but that
# gap belongs to one encoder's settings, and another writes a blank layer at
# 19 kB. So every layer is looked at, and Pillow releases the interpreter lock
# while it decodes: eight threads turn twenty-two seconds into under four.
INVENTORY_THREADS = 8


def template_bytes(path):
    """The printed pages of a notebook: the PDF itself, or the one a `.note` holds."""
    path = Path(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            return archive.read(note_archive.template_entry(archive))
    return path.read_bytes()


def occupied_pages(target):
    """Pages of the destination the tablet already wrote on, which stay as they are.

    A PDF has none: it is a printed notebook nobody has opened yet.
    """
    if not zipfile.is_zipfile(Path(target)):
        return set()
    with zipfile.ZipFile(Path(target)) as base:
        taken = set(base.namelist())
        return {page for page, slots in note_archive.resources(base).items()
                if any(slots.get(kind) in taken
                       for kind in (note_archive.LAYER, note_archive.STROKES))}


def written_pages(source):
    """{page: weight of its layer} for a `.note`, blank pages left out."""
    with zipfile.ZipFile(Path(source)) as ink:
        declared = note_archive.resources(ink)
        weights = {info.filename: info.compress_size for info in ink.infolist()}
        candidates = [(page, kinds[note_archive.LAYER]) for page, kinds
                      in sorted(declared.items())
                      if kinds.get(note_archive.LAYER) in weights]
        blobs = [ink.read(name) for _, name in candidates]

    def inked(data):
        return Image.open(io.BytesIO(data)).convert("RGBA").getbbox() is not None

    with ThreadPoolExecutor(max_workers=INVENTORY_THREADS) as pool:
        verdicts = list(pool.map(inked, blobs))
    return {page: weights[name]
            for (page, name), written in zip(candidates, verdicts) if written}


def inventory(source):
    """What a written notebook holds, in the order it holds it.

    Returns [(section, [(page, label), …]), …] — sections in page order, which
    is reading order. Thumbnails are deliberately left out: they cost a quarter
    of a second each, and a notebook filled for a year has hundreds. They are
    drawn for the section being looked at.
    """
    pages = written_pages(source)
    named = page_sections(source, pages)
    sections = []
    for page in sorted(pages):
        section, label = named[page]
        if not sections or sections[-1][0] != section:
            sections.append((section, []))
        sections[-1][1].append((page, label))
    return sections


def page_previews(source, pages, target=None, offset=(0, 0), width=320,
                  where=None):
    """{page: (thumbnail, share of ink)} — each page as it will read once carried.

    The handwriting alone says what was written; the page under it says what it
    was written on, and where the new edition will put it. Proportions are the
    sheet's, so a glance places the writing on its lines.

    Without a destination the ink is shown on its own, cropped to itself: a
    page is mostly blank, and a postage stamp of blankness tells nobody
    anything. `where` says which page of the destination each one lands on,
    since a section rarely keeps its rank between two editions.
    """
    previews, sheet_of = {}, {}
    holder = None
    try:
        if target is not None:
            holder = Path(target).with_suffix(".apercu.pdf")
            holder.write_bytes(template_bytes(target))
        with zipfile.ZipFile(Path(source)) as ink:
            declared = note_archive.resources(ink)
            present = set(ink.namelist())
            for page in pages:
                name = declared.get(page, {}).get(note_archive.LAYER)
                if name not in present:
                    continue
                layer = Image.open(io.BytesIO(ink.read(name))).convert("RGBA")
                if layer.getbbox() is None:
                    continue
                arrival = page if where is None else where.get(page)
                sheet = (_sheet(holder, arrival, width)
                         if holder and arrival else None)
                previews[page] = (_compose(layer, sheet, offset, width),
                                  coverage(layer))
    finally:
        if holder is not None:
            holder.unlink(missing_ok=True)
    return previews


def _sheet(template, page, width):
    """One page of the destination, drawn small, in its own proportions."""
    try:
        out = subprocess.run(["pdftoppm", "-png", "-r", str(round(width / 6.4)),
                              "-f", str(page), "-l", str(page), str(template)],
                             capture_output=True, check=True).stdout
        return Image.open(io.BytesIO(out)).convert("RGB")
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None  # A preview is a convenience, never a reason to stop.


def _compose(layer, sheet, offset, width):
    if sheet is None:            # No destination page: show the writing itself.
        box = layer.getbbox()
        margin = 24
        box = (max(0, box[0] - margin), max(0, box[1] - margin),
               min(layer.width, box[2] + margin), min(layer.height, box[3] + margin))
        crop = layer.crop(box)
        sheet = Image.new("RGB", crop.size, "white")
        sheet.paste(crop, mask=crop)
        height = max(1, round(sheet.height * width / sheet.width))
        sheet = sheet.resize((width, min(height, width * 2)), Image.LANCZOS)
    else:
        scale = sheet.width / layer.width
        small = layer.resize((sheet.width, round(layer.height * scale)), Image.LANCZOS)
        sheet = sheet.copy()
        sheet.paste(small, (round(offset[0] * scale), round(offset[1] * scale)), small)
    buffer = io.BytesIO()
    sheet.save(buffer, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


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
    reader = PdfReader(io.BytesIO(template_bytes(source)))
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


def page_count(archive_path):
    """How many pages a notebook has, from the template it was built on.

    The template is what the outline describes, so it is what page numbers are
    counted against — the page list should agree, and does on a notebook the
    tablet made itself.
    """
    return len(PdfReader(io.BytesIO(template_bytes(archive_path))).pages)


def landing(source, target, pages):
    """Where each page goes in the new notebook: {page: (label, destination)}.

    A page number means nothing across two notebooks: a period of fifty-two
    days instead of forty-seven pushes the backlog twenty-five pages down, and
    grafting by number would write a backlog onto a Thursday. Pages are matched
    by **what they are** — the outline entry that names them, « TODO 01 -
    Liste 01 +101 » — so a section keeps its writing wherever the new edition
    happens to put it.

    A page whose name no longer exists has nowhere to go, and says so. That is
    the right answer too: a dated page from September does not belong in a
    notebook that starts in December, while a backlog and its projects do.
    """
    here = page_sections(source, pages)
    total = page_count(target)
    there = page_sections(target, range(1, total + 1))
    index = {}
    for page, (_, label) in there.items():
        index.setdefault(label, page)
    return {page: (here.get(page, ("", f"Page {page}"))[1],
                   index.get(here.get(page, ("", None))[1]))
            for page in pages}


def say_where(where, report):
    """Tell which pages moved and which have nowhere to go; return the latter."""
    astray = {page: label for page, (label, arrival) in where.items() if arrival is None}
    moved = {page: arrival for page, (_, arrival) in where.items()
             if arrival not in (None, page)}
    if moved:
        report(f"{len(moved)} page(s) ont changé de rang et suivent leur section.")
        for page, destination in sorted(moved.items())[:4]:
            report(f"  « {where[page][0]} » : page {page} → page {destination}")
    if astray:
        report(f"{len(astray)} page(s) sans place dans le nouveau carnet, laissée(s) "
               "de côté.")
        for page, label in sorted(astray.items())[:4]:
            report(f"  page {page} : « {label} »")
    return astray


NOWHERE = ("Les pages choisies ne désignent plus la même chose dans le nouveau "
           "carnet : régénérez-le avec les mêmes réglages de backlog et de projets, "
           "ou choisissez d’autres pages.")
# Each sample is two renders, about a second together. Five spread over what is
# carried let the median shrug off two pages that disagree.
ALIGNMENT_SAMPLES = 5


def sample_pairs(where):
    """A few (page, arrival) pairs, spread over everything that has a place.

    The offset is only worth measuring between two pages of the same kind: a
    September month against a November one differs by a whole grid column, and
    phase correlation dutifully reports that column as a shift. Pages matched
    by name are the same sheet in both editions, and they are the very pages
    the ink is about to land on.
    """
    pairs = sorted((page, arrival) for page, (_, arrival) in where.items() if arrival)
    if len(pairs) <= ALIGNMENT_SAMPLES:
        return pairs
    step = (len(pairs) - 1) / (ALIGNMENT_SAMPLES - 1)
    return [pairs[round(index * step)] for index in range(ALIGNMENT_SAMPLES)]


def plan(source, target, pages):
    """What carrying `pages` over would do, before anything is written.

    Returns (where, kept, offset): where each page lands, as `landing` says;
    the pages whose destination the tablet already wrote on; and the layout
    offset in panel pixels, so a preview shows the ink where it will fall.
    """
    where = landing(source, target, pages)
    occupied = occupied_pages(target)
    kept = {page for page, (_, arrival) in where.items() if arrival in occupied}
    offset = (0, 0)
    if any(arrival for _, arrival in where.values()):
        try:
            offset = alignment(source, target, target, where)
        except (ValueError, OSError, subprocess.CalledProcessError):
            pass  # A preview is a convenience; the transfer itself will say why.
    return where, kept, offset


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
    wanted_pages = [page for page in written_pages(source)
                    if pages is None or page in set(pages)]
    where = landing(source, target, wanted_pages)
    astray = say_where(where, report)
    dx, dy = (alignment(source, target, output, where, report)
              if len(astray) < len(where) else (0, 0))
    with zipfile.ZipFile(source) as ink, zipfile.ZipFile(target) as base:
        written, declared = note_archive.resources(ink), note_archive.resources(base)
        present, taken = set(ink.namelist()), set(base.namelist())
        added, grafted = [], set()
        # Only pages that hold ink and have somewhere to land: a layer opened
        # and left blank is not worth carrying, and says nothing when it does.
        for page in wanted_pages:
            arrival = where[page][1]
            if arrival is None:
                continue
            slots = declared.get(arrival, {})
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
            raise ValueError(
                f"{source.name} : aucune page à reporter. "
                + (NOWHERE if astray else "Aucune page écrite dans la sélection."))
    report(f"{len(grafted)} page(s) greffée(s) : "
           + ", ".join(str(page) for page in sorted(grafted)))
    total = note_archive.append(target, output, added)
    report(f"Carnet de la tablette conservé octet pour octet ; {len(added)} fichiers "
           f"ajoutés, {total} entrées au total.")
    report(f"→ {output} ({output.stat().st_size / 1e6:.1f} Mo)")
    return sorted(grafted)


def templates(source, target, scratch):
    """Both templates on disk, as a pair of paths to clean up afterwards."""
    holders = []
    for index, path in enumerate((source, target)):
        holder = Path(scratch).with_suffix(f".gabarit-{index}.pdf")
        holder.write_bytes(template_bytes(path))
        holders.append(holder)
    return holders


def alignment(source, target, scratch, where, report=lambda line: None):
    """How far the new edition moved its writing column, in panel pixels.

    `where` is what `landing` answered: the measurement is taken between pages
    it matched, never between two pages that merely share a number.
    """
    holders = templates(source, target, scratch)
    try:
        report("Calage sur le carnet d’origine :")
        dx, dy, spread = measure(holders[0], Path(source).suffix.lower() == ".pdf",
                                 holders[1], sample_pairs(where), report)
    finally:
        for holder in holders:
            holder.unlink(missing_ok=True)
    report(f"Décalage retenu : {dx / PANEL_DPI * 25.4:+.2f} × "
           f"{dy / PANEL_DPI * 25.4:+.2f} mm"
           + (f" (dispersion {spread:.0f} px)" if spread else " (unanime)"))
    if spread > SPREAD_TOLERANCE:
        report("  Les pages ne s’accordent pas sur le décalage : vérifiez le "
               "résultat, ou imposez-le à la main.")
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


def measure(template, clean, target, pairs, report):
    """The offset between the two editions, agreed on by several matched pages.

    `pairs` are (page of the written notebook, page of the new one).
    """
    found = []
    for page, arrival in pairs:
        try:
            dx, dy = shift(render(template, page, SAMPLE_DPI, clean=clean),
                           render(target, arrival, SAMPLE_DPI))
        except (subprocess.CalledProcessError, ValueError) as error:
            report(f"  page {page} → {arrival} : calage impossible ({error})")
            continue
        found.append((dx, dy))
        report(f"  page {page} → {arrival} : {dx:+d}, {dy:+d} px")
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


def transfer(source, target, output, offset_mm=None, report=print, pages=None):
    """Report the handwriting of `source` onto `target`, saving to `output`."""
    source, target, output = Path(source), Path(target), Path(output)
    layers, _ = read_source(source, report)
    chosen = None if pages is None else set(pages)
    written = {page: layer for page, layer in layers.items()
               if coverage(layer) > 0 and (chosen is None or page in chosen)}
    blank = sorted(page for page, layer in layers.items() if coverage(layer) == 0)
    if not written:
        raise ValueError(f"{source.name} : aucune page écrite "
                         + ("dans ce carnet." if chosen is None else "dans la sélection."))
    report(f"{len(written)} page(s) écrite(s) : "
           + ", ".join(str(page) for page in sorted(written)))
    if blank:
        report("Ignorées, car vides : " + ", ".join(str(page) for page in blank))

    # The same matching as a `.note` destination: a page goes where its name
    # is, and a page whose name is gone stays behind instead of landing on a
    # stranger's sheet.
    where = landing(source, target, sorted(written))
    say_where(where, report)
    carried = {page: where[page][1] for page in sorted(written) if where[page][1]}
    if not carried:
        raise ValueError(f"{source.name} : aucune page à reporter. " + NOWHERE)

    if offset_mm is not None:
        dx, dy = offset_mm * MM * PANEL_DPI / 72, 0.0
        report(f"Décalage imposé : {offset_mm:+.2f} mm horizontal.")
    else:
        dx, dy = alignment(source, target, output, where, report)

    # An incremental update keeps the original bytes and appends only the pages
    # that changed: cloning a 2 400-page object graph exhausts the interpreter
    # stack, and would rewrite every link and bookmark for nothing.
    writer = PdfWriter(str(target), incremental=True)
    for page, arrival in carried.items():
        layer = written[page]
        target_page = writer.pages[arrival - 1]
        box = (float(target_page.mediabox.width), float(target_page.mediabox.height))
        target_page.merge_page(overlay(layer, box, dx, dy))
        report(f"  page {page:>5} → {arrival:>5} · {coverage(layer):5.2f} % d’encre reportée")
    with open(output, "wb") as handle:
        writer.write(handle)
    report(f"→ {output} ({output.stat().st_size / 1e6:.1f} Mo)")
    return sorted(carried)


def carry(source, target, output, offset_mm=None, report=print, pages=None):
    """Carry handwriting over, in the shape the destination asks for.

    A `.note` destination is a notebook the tablet just made: the ink is grafted
    into it and stays strokes. A PDF destination receives the ink as an image.
    """
    if zipfile.is_zipfile(Path(target)):
        return graft_note(source, target, output, report=report, pages=pages)
    return transfer(source, target, output, offset_mm, report=report, pages=pages)


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
        for page, label in rows:
            print(f"    {page:>6}  {label}")


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
