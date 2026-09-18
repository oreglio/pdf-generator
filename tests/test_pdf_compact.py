"""Repacking a finished PDF so a slow reader has less to parse."""

import io
import shutil
import unittest

from pypdf import PdfReader

import pdf_compact
from planner_config import PlannerConfig
from planner_pdf import generate_pdf


HAS_QPDF = shutil.which("qpdf") is not None
SMALL = PlannerConfig(days=6, list_count=2, tasks_per_list=3, detail_pages=1,
                      notes_pages=1, project_count=2, project_notes_pages=1)


def notebook():
    output = io.BytesIO()
    generate_pdf(SMALL, output)
    return output.getvalue()


class MissingToolTests(unittest.TestCase):
    def test_without_qpdf_the_notebook_is_handed_back_untouched(self):
        """A missing convenience never costs anyone their carnet."""
        original, lines = notebook(), []
        pdf_compact.available = lambda: False
        self.addCleanup(setattr, pdf_compact, "available",
                        pdf_compact.__dict__["available"])
        try:
            self.assertEqual(pdf_compact.compact(original, report=lines.append), original)
        finally:
            import importlib
            importlib.reload(pdf_compact)
        self.assertTrue(any("qpdf" in line for line in lines))


@unittest.skipUnless(HAS_QPDF, "qpdf est requis pour le compactage")
class CompactionTests(unittest.TestCase):
    def setUp(self):
        self.original = notebook()
        self.packed = pdf_compact.compact(self.original, report=lambda line: None)

    def test_the_file_shrinks(self):
        self.assertLess(len(self.packed), len(self.original))
        self.assertTrue(self.packed.startswith(b"%PDF"))

    def test_not_one_page_is_redrawn(self):
        """The document is stored differently, never rewritten."""
        before, after = (PdfReader(io.BytesIO(data))
                         for data in (self.original, self.packed))
        self.assertEqual(len(after.pages), len(before.pages))
        for index, (was, now) in enumerate(zip(before.pages, after.pages)):
            with self.subTest(page=index + 1):
                self.assertEqual(now.get_contents().get_data(),
                                 was.get_contents().get_data())
                self.assertEqual(list(now.mediabox), list(was.mediabox))

    def test_every_link_and_bookmark_survives(self):
        before, after = (PdfReader(io.BytesIO(data))
                         for data in (self.original, self.packed))

        def count(items):
            return sum(count(item) if isinstance(item, list) else 1 for item in items)

        self.assertEqual(sum(len(page.get("/Annots") or []) for page in after.pages),
                         sum(len(page.get("/Annots") or []) for page in before.pages))
        self.assertEqual(count(after.outline), count(before.outline))

    def test_a_document_that_cannot_be_read_is_returned_as_it_came(self):
        for data in (b"%PDF-1.4 tronqu\xc3\xa9", b"pas un pdf"):
            with self.subTest(data=data[:12]):
                self.assertEqual(pdf_compact.compact(data, report=lambda line: None), data)


if __name__ == "__main__":
    unittest.main()
