import importlib.util
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(
            importlib.util.find_spec("planner_pdf"),
            "The connected Viwoods planner generator has not been implemented",
        )
        from planner_config import PlannerConfig
        from planner_pdf import generate_pdf
        self.Config = PlannerConfig
        self.generate = generate_pdf
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def book(self, **kwargs):
        kwargs.setdefault("notes_pages", 1)
        config = self.Config(list_count=2, tasks_per_list=4, days=3, **kwargs)
        path = Path(self.temp.name) / "book.pdf"
        self.generate(config, path)
        return PdfReader(path)

    @staticmethod
    def links(reader, page):
        pages = {p.indirect_reference.idnum: i for i, p in enumerate(reader.pages)}
        result = {}
        for ref in page.get("/Annots", []):
            annotation = ref.get_object()
            dest = annotation.get("/Dest")
            if dest:
                result[str(annotation.get("/Contents", ""))] = pages[dest[0].idnum]
        return result

    def test_device_size_page_count_and_meetings_sections(self):
        reader = self.book()
        self.assertEqual(len(reader.pages), 26)
        for page in reader.pages:
            self.assertAlmostEqual(float(page.mediabox.width), 460.8)
            self.assertAlmostEqual(float(page.mediabox.height), 614.4)
        text = reader.pages[2].extract_text()
        for section in ("Objectives", "Agenda", "Notes"):
            self.assertIn(section, text)

    def test_daily_dashboards_share_tasks_and_context_has_fixed_backlink(self):
        reader = self.book()
        for day_page in (2, 4, 6):
            links = self.links(reader, reader.pages[day_page])
            self.assertEqual(links["Liste 01"], 8)
            self.assertEqual(links["Liste 02"], 17)
        list_links = self.links(reader, reader.pages[17])
        self.assertEqual(list_links["Tache 02-04"], 24)
        self.assertEqual(self.links(reader, reader.pages[24])["Liste 02"], 17)
        self.assertEqual(self.links(reader, reader.pages[24])["Suite"], 25)
        self.assertEqual(self.links(reader, reader.pages[25])["Precedent"], 24)

    def test_every_link_resolves_and_click_target_stays_on_page(self):
        reader = self.book()
        pages = {p.indirect_reference.idnum for p in reader.pages}
        links = 0
        for page in reader.pages:
            self.assertEqual(self.links(reader, page)["Mes listes"], 0)
            for ref in page.get("/Annots", []):
                annotation = ref.get_object()
                self.assertEqual(annotation["/Subtype"], "/Link")
                self.assertIn(annotation["/Dest"][0].idnum, pages)
                x0, y0, x1, y1 = map(float, annotation["/Rect"])
                self.assertTrue(0 <= x0 < x1 <= 460.8)
                self.assertTrue(0 <= y0 < y1 <= 614.4)
                links += 1
        self.assertGreater(links, 100)

    def test_fonts_are_embedded_for_all_variants(self):
        for variant in ("manrope", "manrope-contrast", "atkinson"):
            reader = self.book(typography=variant)
            embedded = set()
            for page in reader.pages:
                for ref in page["/Resources"].get("/Font", {}).values():
                    font = ref.get_object()
                    descriptor = font.get("/FontDescriptor")
                    if descriptor:
                        self.assertIn("/FontFile2", descriptor.get_object())
                        embedded.add(str(font["/BaseFont"]))
            self.assertGreaterEqual(len(embedded), 2)

    def test_day_41_uses_second_index_and_all_days_remain_reachable(self):
        config = self.Config(list_count=1, tasks_per_list=2, days=41, notes_pages=1)
        path = Path(self.temp.name) / "boundary.pdf"
        self.generate(config, path)
        reader = PdfReader(path)
        self.assertEqual(len(reader.pages), 90)
        home_links = self.links(reader, reader.pages[0])
        self.assertEqual(home_links["Journees 001–040"], 1)
        self.assertEqual(home_links["Journees 041–041"], 2)
        self.assertEqual(home_links["Premiere journee"], 3)
        self.assertEqual(self.links(reader, reader.pages[1])["Meeting 040"], 81)
        self.assertEqual(self.links(reader, reader.pages[2])["Meeting 041"], 83)
        self.assertEqual(self.links(reader, reader.pages[83])["Journees"], 2)

    def test_two_notes_pages_link_to_each_other_and_their_meeting(self):
        self.assertEqual(self.Config().notes_pages, 2)
        reader = self.book(notes_pages=2)
        self.assertEqual(len(reader.pages), 29)
        for meeting in (2, 5, 8):
            first, second = meeting + 1, meeting + 2
            self.assertEqual(self.links(reader, reader.pages[meeting])["Suite"], first)
            self.assertEqual(self.links(reader, reader.pages[first])["Suite"], second)
            self.assertEqual(self.links(reader, reader.pages[second])["Notes 1"], first)
            day = (meeting - 2) // 3 + 1
            self.assertEqual(self.links(reader, reader.pages[second])[f"Meeting {day:03d}"], meeting)
            self.assertEqual(self.links(reader, reader.pages[second])["Suite"], second + 1 if day < 3 else 1)

    def test_notes_navigation_has_explicit_labels_and_no_duplicate_meeting_backlink(self):
        for language in ("fr", "en"):
            for count in (1, 2, 3):
                with self.subTest(language=language, notes_pages=count):
                    reader = self.book(language=language, notes_pages=count)
                    for day in range(1, 4):
                        meeting = 2 + (day - 1) * (1 + count)
                        for number in range(1, count + 1):
                            page = reader.pages[meeting + number]
                            links = self.links(reader, page)
                            text = page.extract_text()
                            self.assertEqual(links[f"Meeting {day:03d}"], meeting)
                            self.assertEqual(list(links.values()).count(meeting), 1)
                            if number > 1:
                                self.assertIn(f"< Notes {number - 1}", text)
                                self.assertEqual(links[f"Notes {number - 1}"], meeting + number - 1)
                            else:
                                self.assertNotIn("<", text)
                            if number < count:
                                self.assertIn(f"Notes {number + 1} >", text)
                                self.assertEqual(links["Suite" if language == "fr" else "Next"], meeting + number + 1)
                            elif day < 3:
                                self.assertIn("Jour suivant >" if language == "fr" else "Next day >", text)
                                self.assertEqual(links["Suite" if language == "fr" else "Next"], meeting + count + 1)
                            else:
                                self.assertIn("Index >", text)

    def test_invalid_inputs_fail_before_writing(self):
        for changes in ({"days": 0}, {"list_count": 11}, {"tasks_per_list": 41},
                        {"typography": "unknown"}, {"detail_pages": 0},
                        {"days": True}, {"notes_pages": -1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.Config(**changes)

    def test_visual_samples_do_not_contain_dead_links(self):
        import planner_pdf
        self.assertTrue(hasattr(planner_pdf, "generate_samples"), "A small visual preview is required")
        path = Path(self.temp.name) / "samples.pdf"
        planner_pdf.generate_samples(self.Config(), path)
        reader = PdfReader(path)
        self.assertEqual(len(reader.pages), 3)
        for page in reader.pages:
            self.assertFalse(page.get("/Annots"))

    def test_comparison_reuses_templates_without_duplicate_pdf_objects(self):
        from planner_pdf import generate_comparison
        path = Path(self.temp.name) / "comparison.pdf"
        generate_comparison(self.Config(), path)
        reader = PdfReader(path)
        self.assertEqual(len(reader.pages), 10)
        for index in (1, 4, 7):
            self.assertIn("Objectives", reader.pages[index].extract_text())
        for page in reader.pages:
            self.assertFalse(page.get("/Annots"))

    def test_configuration_roundtrip_and_unknown_settings(self):
        config = self.Config(list_count=2, list_names=["Travail", "Personnel"], typography="atkinson")
        self.assertEqual(self.Config.from_dict(config.to_dict()), config)
        self.assertEqual(config.list_name(2), "Personnel")
        for value in ([], {"unknown": 1}, {"list_names": ["x" * 25]}):
            with self.assertRaises(ValueError):
                self.Config.from_dict(value)

    def test_english_edition_preserves_layout_and_navigation(self):
        self.assertIn("language", self.Config.__dataclass_fields__)
        french = self.book()
        english = self.book(language="en")
        expected = {0: ("UNDATED NOTEBOOK", "My days", "My lists", "4 tasks / list"),
                    1: ("DAY INDEX", "Days"), 2: ("DAY 001", "Date / period", "Day"),
                    3: ("Date / subject",), 8: ("TODO / LIST 01", "List 01"),
                    9: ("LIST 01 — NOTES 01/02", "Subject")}
        for index, labels in expected.items():
            for label in labels:
                self.assertIn(label, english.pages[index].extract_text())
        self.assertIn("Mes journées", french.pages[0].extract_text())
        self.assertEqual(len(french.pages), len(english.pages))
        for fr, en in zip(french.pages, english.pages):
            self.assertEqual(fr.mediabox, en.mediabox)
            self.assertEqual(list(self.links(french, fr).values()), list(self.links(english, en).values()))
            self.assertEqual([a.get_object()["/Rect"] for a in fr["/Annots"]],
                             [a.get_object()["/Rect"] for a in en["/Annots"]])
        self.assertEqual(self.links(english, english.pages[9])["Back to list 01"], 8)
        self.assertIn("Undated meetings", english.metadata.subject)

    def test_language_roundtrip_custom_names_and_separate_filenames(self):
        self.assertIn("language", self.Config.__dataclass_fields__)
        config = self.Config(language="en", list_names=("Travail",))
        self.assertEqual(self.Config.from_dict(config.to_dict()), config)
        self.assertEqual(config.list_name(1), "Travail")
        self.assertEqual(config.list_name(2), "List 02")
        self.assertEqual(self.Config().pdf_filename, "aipaper-manrope-200j.pdf")
        self.assertEqual(config.pdf_filename, "aipaper-manrope-en-200d.pdf")
        for language in ("de", None, [], True):
            with self.assertRaises(ValueError):
                self.Config(language=language)


if __name__ == "__main__":
    unittest.main()
