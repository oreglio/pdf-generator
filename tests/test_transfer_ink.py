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


def archive(path, template, layers, name=NOTE_NAME, note_id=NOTE_ID):
    """A `.note` shaped like the tablet's own export."""
    count = max(40, max(layers, default=0) + 1)
    pages = [{"id": f"page-{index}", "order": index, "pid": note_id}
             for index in range(count)]
    resources = []
    with zipfile.ZipFile(path, "w") as bundle:
        for page, layer in layers.items():
            member = f"mainBmp_{page:04d}.png"
            resources.append({"fileName": member, "pid": f"page-{page - 1}",
                              "noteId": note_id, "resourceType": 1})
            bundle.writestr(member, png(layer))
        # A page that was opened but never written declares a layer it never ships.
        resources.append({"fileName": "mainBmp_absent.png", "pid": "page-30",
                          "noteId": note_id, "resourceType": 1})
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
class RebuildTests(unittest.TestCase):
    """Re-issuing the tablet's own notebook, so the strokes stay strokes."""

    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        self.template = self.folder / "gabarit.pdf"
        with open(self.template, "wb") as handle:
            generate_pdf(SMALL, handle)
        self.pages = len(PdfReader(str(self.template)).pages)

    def note(self, template=None, count=None):
        path = self.folder / "carnet.note"
        source = (template or self.template).read_bytes()
        archive(path, source, {3: ink_layer()})
        # The page list must describe the template it was written on.
        count = self.pages if count is None else count
        with zipfile.ZipFile(path) as bundle:
            members = {name: bundle.read(name) for name in bundle.namelist()}
        members[f"{NOTE_NAME}_PageListFileInfo.json"] = json.dumps(
            [{"id": f"page-{index}", "order": index, "pid": NOTE_ID}
             for index in range(count)]).encode()
        with zipfile.ZipFile(path, "w") as bundle:
            for name, data in members.items():
                bundle.writestr(name, data)
        return path

    def edition(self, name):
        """The same layout, a different file: what a regeneration produces."""
        path = self.folder / name
        writer = PdfWriter(str(self.template), incremental=True)
        writer.add_metadata({"/Subject": name})
        with open(path, "wb") as handle:
            writer.write(handle)
        return path

    def test_the_template_is_replaced_and_the_handwriting_is_copied_as_is(self):
        source, target = self.note(), self.edition("nouvelle.pdf")
        output = self.folder / "reedite.note"
        pages = transfer_ink.rebuild_note(source, target, output, report=lambda line: None)
        self.assertEqual(pages, self.pages)
        with zipfile.ZipFile(source) as before, zipfile.ZipFile(output) as after:
            self.assertEqual(after.read("note_template.pdf"), target.read_bytes())
            drawings = [name for name in before.namelist() if name.endswith(".png")]
            self.assertTrue(drawings)
            for name in drawings:  # The ink itself is never touched.
                self.assertEqual(before.read(name), after.read(name))

    def test_the_notebook_keeps_its_identity_unless_a_name_is_asked_for(self):
        """An unknown notebook is what the importer refuses when anything is off."""
        output = self.folder / "tel quel.note"
        transfer_ink.rebuild_note(self.note(), self.edition("nouvelle.pdf"), output,
                                  report=lambda line: None)
        with zipfile.ZipFile(output) as after:
            info = json.loads(after.read(f"{NOTE_NAME}_NoteFileInfo.json"))
            self.assertEqual(info["fileName"], NOTE_NAME)
            self.assertEqual(info["id"], NOTE_ID)

    def test_a_name_asked_for_is_carried_through_every_field(self):
        output = self.folder / "Carnet 2026.note"
        transfer_ink.rebuild_note(self.note(), self.edition("nouvelle.pdf"), output,
                                  report=lambda line: None, name="Carnet 2026")
        with zipfile.ZipFile(output) as after:
            info = json.loads(after.read("Carnet 2026_NoteFileInfo.json"))
            self.assertEqual(info["fileName"], "Carnet 2026")
            self.assertNotEqual(info["id"], NOTE_ID)
            self.assertEqual(info["pid"], "NOTE_USER_DIR_ID_7178")  # same folder
            pages = json.loads(after.read("Carnet 2026_PageListFileInfo.json"))
            self.assertTrue(all(page["pid"] == info["id"] for page in pages))
            resources = json.loads(after.read("Carnet 2026_PageResource.json"))
            self.assertTrue(all(item["noteId"] == info["id"] for item in resources))
            template = json.loads(after.read("Carnet 2026_NoteTemplateResource.json"))
            self.assertEqual(template["ownerId"], info["id"])
            for name in after.namelist():
                if name.endswith(".json"):
                    self.assertNotIn(NOTE_ID.encode(), after.read(name))
                    self.assertNotIn(NOTE_NAME.encode(), after.read(name))

    def test_the_refusal_of_the_tablet_is_stated_before_anything_is_written(self):
        lines = []
        transfer_ink.rebuild_note(self.note(), self.edition("nouvelle.pdf"),
                                  self.folder / "pour memoire.note", report=lines.append)
        self.assertEqual(lines[0], transfer_ink.REBUILD_WARNING)

    def test_an_archive_that_names_no_notebook_is_refused(self):
        path = self.folder / "muet.note"
        with zipfile.ZipFile(path, "w") as bundle:
            bundle.writestr("note_PageListFileInfo.json", json.dumps(
                [{"id": f"page-{i}", "order": i} for i in range(self.pages)]))
            bundle.writestr("note_template.pdf", self.template.read_bytes())
        with self.assertRaises(ValueError):
            transfer_ink.rebuild_note(path, self.edition("nouvelle.pdf"),
                                      self.folder / "jamais.note", report=lambda line: None)

    def test_a_flattened_pdf_has_no_strokes_left_to_hand_back(self):
        with self.assertRaises(ValueError) as refusal:
            transfer_ink.rebuild_note(self.template, self.edition("autre.pdf"),
                                      self.folder / "jamais.note", report=lambda line: None)
        self.assertIn(".note", str(refusal.exception))

    def test_an_edition_of_another_length_is_refused(self):
        with self.assertRaises(ValueError) as refusal:
            transfer_ink.rebuild_note(self.note(count=self.pages + 5),
                                      self.edition("nouvelle.pdf"),
                                      self.folder / "jamais.note", report=lambda line: None)
        self.assertIn(str(self.pages), str(refusal.exception))
        self.assertFalse((self.folder / "jamais.note").exists())

    def test_an_edition_that_moved_the_writing_column_is_refused(self):
        """Strokes keep their coordinates: a shifted layout would land beside them."""
        shifted = self.folder / "decale.pdf"
        with open(shifted, "wb") as handle:
            generate_pdf(PlannerConfig(**dict(SMALL.to_dict(), toolbar="left",
                                              toolbar_mm=11.0)), handle)
        with self.assertRaises(ValueError) as refusal:
            transfer_ink.rebuild_note(self.note(), shifted,
                                      self.folder / "jamais.note", report=lambda line: None)
        self.assertIn("+11.0", str(refusal.exception))
        self.assertFalse((self.folder / "jamais.note").exists())


class WorkspaceTests(unittest.TestCase):
    """The Folio page, in the parts that do not need a browser."""

    def setUp(self):
        from nicegui_app import TransferWorkspace
        self.workspace = TransferWorkspace()
        self.addCleanup(self.workspace.close)

    def test_a_file_of_the_wrong_kind_never_reaches_the_disk(self):
        space = self.workspace
        self.assertIsNone(space.destination('target', space.TARGET, 'carnet.note'))
        self.assertIsNone(space.destination('source', space.SOURCE, 'notes.txt'))
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
