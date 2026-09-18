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
from pypdf import PdfReader

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


def archive(path, template, layers):
    """A `.note` shaped like the tablet's own export."""
    count = max(40, max(layers, default=0) + 1)
    pages = [{"id": f"page-{index}", "order": index} for index in range(count)]
    resources = []
    with zipfile.ZipFile(path, "w") as bundle:
        for page, layer in layers.items():
            name = f"mainBmp_{page:04d}.png"
            resources.append({"fileName": name, "pid": f"page-{page - 1}"})
            bundle.writestr(name, png(layer))
        # A page that was opened but never written declares a layer it never ships.
        resources.append({"fileName": "mainBmp_absent.png", "pid": "page-30"})
        bundle.writestr("note_PageListFileInfo.json", json.dumps(pages))
        bundle.writestr("note_PageResource.json", json.dumps(resources))
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


if __name__ == "__main__":
    unittest.main()
