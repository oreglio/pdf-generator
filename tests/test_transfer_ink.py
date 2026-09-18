"""Carrying handwriting from a written notebook onto a freshly generated one."""

import io
import json
import shutil
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path

import numpy as np
from PIL import Image
from pypdf import PdfReader, PdfWriter

import note_archive
import transfer_ink
from planner_config import PlannerConfig
from planner_pdf import generate_pdf


SMALL = PlannerConfig(days=2, list_count=1, tasks_per_list=1, detail_pages=1,
                      notes_pages=1, project_count=1, project_notes_pages=1)
HAS_GHOSTSCRIPT = shutil.which("gs") is not None


def ink_layer(mark=True):
    """A panel-sized ink layer: black strokes on a transparent background."""
    layer = Image.new("RGBA", (1920, 2560), (0, 0, 0, 0))
    if mark:
        for row in range(900, 1000):
            for column in range(300, 900, 3):
                layer.putpixel((column, row), (0, 0, 0, 255))
    return layer


def png(layer):
    buffer = io.BytesIO()
    layer.save(buffer, format="PNG")
    return buffer.getvalue()


NOTE_NAME = "carnet_origine.pdf"
NOTE_ID = "090F70D3BF647C850F6C0EB4A01774B2"


def archive(path, template, layers, name=NOTE_NAME, note_id=NOTE_ID, count=None):
    """A `.note` shaped like the tablet's own export.

    Every page declares a layer and a stroke file, written on or not; only a
    written one ships the file. That is what the tablet does, and what makes
    grafting possible.
    """
    count = max(40, max(layers, default=0) + 1) if count is None else count
    pages = [{"id": f"{name}-page-{index}", "order": index, "pid": note_id}
             for index in range(count)]
    resources = []
    with zipfile.ZipFile(path, "w") as bundle:
        for index in range(count):
            page = index + 1
            for kind, prefix in ((1, "mainBmp"), (7, "path")):
                member = f"{prefix}_{name}-{page:05d}.{'png' if kind == 1 else 'json'}"
                resources.append({"fileName": member, "pid": f"{name}-page-{index}",
                                  "noteId": note_id, "resourceType": kind,
                                  "resourceState": 3 if kind == 1 else 1})
                if page in layers:
                    bundle.writestr(member, png(layers[page]) if kind == 1
                                    else json.dumps([[100, 200, 1], [110, 210, 2]]).encode())
        bundle.writestr(f"{name}_NoteFileInfo.json",
                        json.dumps({"fileName": name, "id": note_id,
                                    "pid": "NOTE_USER_DIR_ID_7178"}))
        bundle.writestr(f"{name}_PageListFileInfo.json", json.dumps(pages))
        bundle.writestr(f"{name}_PageResource.json", json.dumps(resources))
        bundle.writestr(f"{name}_NoteTemplateResource.json",
                        json.dumps({"ownerId": note_id, "templateType": "PDF"}))
        bundle.writestr("note_template.pdf", template)
    return path


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        self.template = io.BytesIO()
        generate_pdf(SMALL, self.template)
        self.template = self.template.getvalue()

    def test_only_the_pages_that_ship_a_layer_are_read(self):
        path = archive(self.folder / "carnet.note", self.template,
                       {3: ink_layer(), 5: ink_layer()})
        layers, template = transfer_ink.read_archive(path)
        self.assertEqual(sorted(layers), [3, 5])
        self.assertEqual(layers[3].mode, "RGBA")
        self.assertEqual(layers[3].size, (1920, 2560))
        self.assertEqual(template, self.template)

    def test_an_archive_without_the_expected_parts_is_refused(self):
        path = self.folder / "vide.note"
        with zipfile.ZipFile(path, "w") as bundle:
            bundle.writestr("readme.txt", "rien")
        with self.assertRaises(ValueError):
            transfer_ink.read_archive(path)


class AlignmentTests(unittest.TestCase):
    def page(self):
        page = np.zeros((600, 400))
        page[100:500, 40:250] = 180.0          # the writing column
        page[80:520, 330:390] = 255.0          # the navigation rail
        return page

    def test_a_known_translation_is_recovered_in_both_directions(self):
        before = self.page()
        after = np.roll(before, 26, axis=1)
        self.assertEqual(transfer_ink.shift(before, after), (26, 0))
        self.assertEqual(transfer_ink.shift(after, before), (-26, 0))
        self.assertEqual(transfer_ink.shift(before, before), (0, 0))

    def test_the_rail_is_left_out_so_it_cannot_outvote_the_writing(self):
        """A band on the left moves the writing; the rail stays where it was."""
        before = self.page()
        after = before.copy()
        after[:, :330] = np.roll(before[:, :330], 26, axis=1)
        self.assertEqual(transfer_ink.shift(before, after), (26, 0))
        self.assertLess(transfer_ink.writing_area(before).shape[1], before.shape[1])

    def test_two_different_page_sizes_are_refused(self):
        with self.assertRaises(ValueError):
            transfer_ink.shift(self.page(), np.zeros((600, 401)))


@unittest.skipUnless(HAS_GHOSTSCRIPT, "Ghostscript est requis pour le calage")
class TransferTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        self.template = self.build(SMALL, "gabarit.pdf")

    def build(self, config, name):
        path = self.folder / name
        with open(path, "wb") as handle:
            generate_pdf(config, handle)
        return path

    def inked_pages(self, pdf):
        """Pages carrying an image, which is the only thing this tool adds."""
        found = []
        for index, page in enumerate(PdfReader(str(pdf)).pages, start=1):
            resources = page.get("/Resources")
            objects = resources.get_object().get("/XObject") if resources else None
            if objects and any(entry.get_object().get("/Subtype") == "/Image"
                               for entry in objects.get_object().values()):
                found.append(index)
        return found

    def note(self, layers):
        return archive(self.folder / "carnet.note", self.template.read_bytes(), layers)

    def test_the_ink_lands_on_the_pages_it_came_from(self):
        source = self.note({3: ink_layer(), 6: ink_layer()})
        output = self.folder / "repris.pdf"
        pages = transfer_ink.transfer(source, self.template, output, report=lambda line: None)
        self.assertEqual(pages, [3, 6])
        self.assertEqual(self.inked_pages(output), [3, 6])
        self.assertEqual(len(PdfReader(str(output)).pages),
                         len(PdfReader(str(self.template)).pages))

    def test_a_reserved_band_is_measured_and_the_ink_follows_it(self):
        target = self.build(PlannerConfig(**dict(SMALL.to_dict(),
                                                 toolbar="left", toolbar_mm=11.0)),
                            "decale.pdf")
        lines = []
        transfer_ink.transfer(self.note({3: ink_layer()}), target,
                              self.folder / "cale.pdf", report=lines.append)
        measured = next(line for line in lines if line.startswith("Décalage retenu"))
        self.assertIn("+11.0", measured)
        self.assertIn("unanime", measured)

    def test_an_imposed_offset_skips_the_measurement(self):
        lines = []
        transfer_ink.transfer(self.note({3: ink_layer()}), self.template,
                              self.folder / "impose.pdf", offset_mm=8.0,
                              report=lines.append)
        self.assertTrue(any("Décalage imposé" in line for line in lines))
        self.assertFalse(any("Calage" in line for line in lines))

    def test_a_page_opened_but_never_written_is_not_transferred(self):
        lines = []
        pages = transfer_ink.transfer(self.note({3: ink_layer(), 4: ink_layer(mark=False)}),
                                      self.template, self.folder / "vierge.pdf",
                                      report=lines.append)
        self.assertEqual(pages, [3])
        self.assertTrue(any("Ignorées, car vides : 4" in line for line in lines))

    def test_a_notebook_too_short_to_hold_the_ink_is_refused(self):
        short = self.build(replace(SMALL, days=1), "court.pdf")
        with self.assertRaises(ValueError) as refusal:
            transfer_ink.transfer(self.note({3: ink_layer(), 400: ink_layer()}),
                                  short, self.folder / "jamais.pdf",
                                  report=lambda line: None)
        self.assertIn("400", str(refusal.exception))
        self.assertFalse((self.folder / "jamais.pdf").exists())

    def test_a_notebook_nobody_wrote_in_is_refused(self):
        with self.assertRaises(ValueError):
            transfer_ink.transfer(self.note({3: ink_layer(mark=False)}), self.template,
                                  self.folder / "jamais.pdf", report=lambda line: None)


@unittest.skipUnless(HAS_GHOSTSCRIPT, "Ghostscript est requis pour le calage")
class GraftTests(unittest.TestCase):
    """Adding handwriting to a notebook the tablet itself exported."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        self.template = self.build(SMALL, "gabarit.pdf")
        self.pages = len(PdfReader(str(self.template)).pages)

    def build(self, config, name):
        path = self.folder / name
        with open(path, "wb") as handle:
            generate_pdf(config, handle)
        return path

    def written(self, layers, name="carnet_ecrit.pdf"):
        return archive(self.folder / f"{name}.note", self.template.read_bytes(),
                       layers, name=name, count=self.pages)

    def skeleton(self, template=None, name="carnet_neuf.pdf", count=None):  # noqa: D401
        """What the tablet exports after importing a new edition: no ink."""
        return archive(self.folder / f"{name}.note",
                       (template or self.template).read_bytes(), {}, name=name,
                       note_id="F00DFACE" * 4, count=count or self.pages)

    def test_the_tablet_notebook_is_kept_byte_for_byte_and_the_ink_added(self):
        base = self.skeleton()
        before = base.read_bytes()
        output = self.folder / "greffe.note"
        pages = transfer_ink.graft_note(self.written({3: ink_layer(), 6: ink_layer()}),
                                        base, output, report=lambda line: None)
        self.assertEqual(pages, [3, 6])
        # Not "same contents": the original bytes are still the original bytes.
        self.assertEqual(output.read_bytes()[:len(before) - 4000], before[:len(before) - 4000])
        with zipfile.ZipFile(base) as was, zipfile.ZipFile(output) as now:
            self.assertTrue(set(was.namelist()) < set(now.namelist()))
            for name in was.namelist():
                self.assertEqual(was.read(name), now.read(name))

    def test_the_ink_lands_in_the_slots_the_tablet_declared(self):
        base = self.skeleton()
        output = self.folder / "greffe.note"
        transfer_ink.graft_note(self.written({3: ink_layer()}), base, output,
                                report=lambda line: None)
        with zipfile.ZipFile(base) as was, zipfile.ZipFile(output) as now:
            declared = note_archive.resources(was)[3]
            for kind in (note_archive.LAYER, note_archive.STROKES):
                self.assertNotIn(declared[kind], was.namelist())
                self.assertIn(declared[kind], now.namelist())

    def test_only_the_chosen_pages_are_carried_over(self):
        """A new period rarely wants the whole of the old notebook."""
        source = self.written({3: ink_layer(), 6: ink_layer(), 9: ink_layer()})
        output = self.folder / "choisi.note"
        pages = transfer_ink.graft_note(source, self.skeleton(), output,
                                        report=lambda line: None, pages=[3, 9])
        self.assertEqual(pages, [3, 9])

    def test_a_page_the_tablet_already_wrote_is_never_overwritten(self):
        base = self.skeleton()
        with zipfile.ZipFile(base) as was:
            theirs = note_archive.resources(was)[3][note_archive.LAYER]
        note_archive.append(base, base, [(theirs, png(ink_layer()))])
        output = self.folder / "greffe.note"
        pages = transfer_ink.graft_note(self.written({3: ink_layer(), 6: ink_layer()}),
                                        base, output, report=lambda line: None)
        self.assertEqual(pages, [6])

    def test_a_flattened_pdf_has_no_strokes_left_to_graft(self):
        with self.assertRaises(ValueError):
            transfer_ink.graft_note(self.template, self.skeleton(),
                                    self.folder / "jamais.note", report=lambda line: None)

    def test_a_reserved_band_is_measured_and_the_ink_follows_it(self):
        moved = self.build(PlannerConfig(**dict(SMALL.to_dict(), toolbar="left",
                                                toolbar_mm=11.0)), "decale.pdf")
        lines = []
        transfer_ink.graft_note(self.written({3: ink_layer()}), self.skeleton(moved),
                                self.folder / "cale.note", report=lines.append)
        measured = next(line for line in lines if line.startswith("Décalage retenu"))
        self.assertIn("+11.0", measured)

    def test_a_section_keeps_its_writing_wherever_the_new_edition_puts_it(self):
        """A longer period pushes everything down; the ink follows its section."""
        longer = self.build(replace(SMALL, days=SMALL.days + 4), "plus-long.pdf")
        source = self.written({3: ink_layer()})
        base = self.skeleton(longer, count=len(PdfReader(str(longer)).pages))
        lines = []
        pages = transfer_ink.graft_note(source, base, self.folder / "suivi.note",
                                        report=lines.append)
        self.assertEqual(pages, [3])
        where = transfer_ink.landing(source, base, [3])
        self.assertIsNotNone(where[3][1])

    def test_a_page_whose_section_is_gone_is_left_behind(self):
        """A dated page from September does not belong in a shorter notebook."""
        shorter = self.build(replace(SMALL, days=1, project_count=0), "court.pdf")
        source = self.written({self.pages - 1: ink_layer()})
        base = self.skeleton(shorter, count=len(PdfReader(str(shorter)).pages))
        with self.assertRaises(ValueError):
            transfer_ink.graft_note(source, base, self.folder / "jamais.note",
                                    report=lambda line: None)

    def test_a_notebook_with_nothing_to_give_is_refused(self):
        with self.assertRaises(ValueError):
            transfer_ink.graft_note(self.written({}), self.skeleton(),
                                    self.folder / "jamais.note", report=lambda line: None)


@unittest.skipUnless(HAS_GHOSTSCRIPT, "Ghostscript est requis pour le calage")
class InventoryTests(unittest.TestCase):
    """What the written notebook holds, named the way a person reads it."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        path = self.folder / "gabarit.pdf"
        with open(path, "wb") as handle:
            generate_pdf(SMALL, handle)
        self.pages = len(PdfReader(str(path)).pages)
        self.source = archive(self.folder / "ecrit.note", path.read_bytes(),
                              {3: ink_layer(), 4: ink_layer(mark=False),
                               6: ink_layer()}, count=self.pages)

    def test_a_page_opened_but_never_written_is_not_listed(self):
        self.assertEqual(sorted(transfer_ink.written_pages(self.source)), [3, 6])

    def test_a_blank_layer_is_recognised_whatever_it_weighs(self):
        """One encoder writes a blank layer at 267 bytes, another at 19 kB."""
        weights = transfer_ink.written_pages(self.source)
        self.assertEqual(sorted(weights), [3, 6])
        self.assertTrue(all(weight > 0 for weight in weights.values()))

    def test_every_page_is_named_and_filed_under_a_section(self):
        sections = transfer_ink.inventory(self.source)
        listed = [page for _, rows in sections for page, _ in rows]
        self.assertEqual(listed, [3, 6])
        for section, rows in sections:
            self.assertTrue(section)
            for _, label in rows:
                self.assertTrue(label)

    def test_a_thumbnail_shows_the_writing_not_the_empty_sheet(self):
        previews = transfer_ink.page_previews(self.source, [3, 4, 6])
        self.assertEqual(sorted(previews), [3, 6])   # 4 is blank, nothing to show
        for uri, share in previews.values():
            self.assertTrue(uri.startswith("data:image/png;base64,"))
            self.assertGreater(share, 0)

    def test_a_thumbnail_keeps_the_sheet_proportions_when_it_has_one(self):
        """The page under the writing says what it was written on."""
        import base64, io
        from PIL import Image
        alone = transfer_ink.page_previews(self.source, [3])[3][0]
        onsheet = transfer_ink.page_previews(self.source, [3], target=self.source,
                                             offset=(60, 0))[3][0]
        self.assertNotEqual(alone, onsheet)
        read = lambda uri: Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1])))
        page = read(onsheet)
        self.assertAlmostEqual(page.width / page.height, 1920 / 2560, places=2)

    def test_a_selection_is_read_the_way_people_write_it(self):
        self.assertEqual(transfer_ink.parse_pages("3"), {3})
        self.assertEqual(transfer_ink.parse_pages("3-5, 9"), {3, 4, 5, 9})
        self.assertIsNone(transfer_ink.parse_pages(""))
        self.assertIsNone(transfer_ink.parse_pages(None))
        for text in ("5-3", "0-2", "trois", "1-2-3"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                transfer_ink.parse_pages(text)


class WorkspaceTests(unittest.TestCase):
    """The Folio page, in the parts that do not need a browser."""

    def setUp(self):
        from nicegui_app import TransferWorkspace
        self.workspace = TransferWorkspace()
        self.addCleanup(self.workspace.close)

    def test_a_file_of_the_wrong_kind_never_reaches_the_disk(self):
        space = self.workspace
        self.assertIsNone(space.destination('target', space.TARGET, 'notes.txt'))
        self.assertIsNone(space.destination('source', space.SOURCE, 'notes.txt'))
        self.assertIsNotNone(space.destination('target', space.TARGET, 'carnet.note'))
        for name in ('carnet.note', 'carnet.PDF'):
            self.assertIsNotNone(space.destination('source', space.SOURCE, name))

    def test_an_uploaded_path_cannot_escape_its_own_folder(self):
        space = self.workspace
        landed = space.destination('source', space.SOURCE, '../../etc/passwd.pdf')
        self.assertEqual(landed.parent, space.folder)
        self.assertEqual(landed.name, 'source-passwd.pdf')

    def test_the_upload_event_still_carries_the_file_this_page_reads(self):
        """NiceGUI moved this payload once; a silent change kills the page."""
        from nicegui.elements.upload_files import FileUpload
        from nicegui.events import UploadEventArguments
        self.assertIn('file', UploadEventArguments.__dataclass_fields__)
        self.assertIn('name', FileUpload.__dataclass_fields__)
        self.assertTrue(callable(FileUpload.save))


if __name__ == "__main__":
    unittest.main()
