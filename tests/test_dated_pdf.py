import io
import unittest
from datetime import date

from pypdf import PdfReader


class DatedPDFTests(unittest.TestCase):
    def book(self, **kwargs):
        from dated_planner_config import DatedPlannerConfig
        from dated_planner_pdf import generate_dated_pdf
        from planner_config import PlannerConfig
        base = PlannerConfig(list_count=2, tasks_per_list=2, language=kwargs.pop("language", "fr"))
        config = DatedPlannerConfig(base=base, start_date="2026-12-28", months=1, **kwargs)
        output = io.BytesIO()
        self.assertEqual(generate_dated_pdf(config, output), config.total_pages)
        return config, PdfReader(output)

    @staticmethod
    def destinations(reader, page):
        ids = {p.indirect_reference.idnum: i for i, p in enumerate(reader.pages)}
        return {str(a.get_object()["/Contents"]): ids[a.get_object()["/Dest"][0].idnum]
                for a in page.get("/Annots", [])}

    def test_calendar_week_meeting_backlog_roundtrip_across_iso_year(self):
        config, reader = self.book(week_pages=2)
        home = self.destinations(reader, reader.pages[0])
        december = home["calendar-2026-12"]
        january = home["calendar-2027-01"]
        dec_links = self.destinations(reader, reader.pages[december])
        jan_links = self.destinations(reader, reader.pages[january])
        self.assertNotIn("2026-12-27", dec_links)
        self.assertNotIn("2027-01-28", jan_links)
        jan1 = jan_links["2027-01-01"]
        week53 = home["week-2026-12-28"]
        self.assertEqual(self.destinations(reader, reader.pages[jan1])["week-2026-12-28"], week53)
        self.assertIn("W53", reader.pages[week53].extract_text())
        self.assertIn("2026", reader.pages[week53].extract_text())
        week_links = self.destinations(reader, reader.pages[week53])
        self.assertEqual(week_links["2027-01-01"], jan1)
        backlog = week_links["Liste 01"]
        context = self.destinations(reader, reader.pages[backlog])["Tache 01-01"]
        self.assertEqual(self.destinations(reader, reader.pages[context])["week-2026-12-28"], week53)
        self.assertIn("BACKLOG", reader.pages[backlog].extract_text())
        self.assertIn("Notes 2 >", reader.pages[context].extract_text())
        # The second weekly page has the same day destinations and no detail pages.
        self.assertEqual(week_links["Next"], week53 + 1)
        second = self.destinations(reader, reader.pages[week53 + 1])
        self.assertEqual(second["Previous"], week53)
        self.assertEqual(second["2027-01-01"], jan1)
        self.assertNotIn("Tache 01-01", week_links)

    def test_all_links_fit_resolve_and_weeks_are_reachable_from_every_page(self):
        config, reader = self.book()
        ids = {p.indirect_reference.idnum for p in reader.pages}
        for page in reader.pages:
            links = self.destinations(reader, page)
            for week in config.weeks:
                self.assertIn(config.week_key(week), links)
            for ref in page.get("/Annots", []):
                a = ref.get_object()
                self.assertEqual(a["/Subtype"], "/Link")
                self.assertIn(a["/Dest"][0].idnum, ids)
                x0, y0, x1, y1 = map(float, a["/Rect"])
                self.assertTrue(0 <= x0 < x1 <= 460.8)
                self.assertTrue(0 <= y0 < y1 <= 614.4)
        self.assertEqual(len(reader.pages), config.total_pages)

    def test_english_dates_and_visual_samples(self):
        from dated_planner_pdf import generate_dated_samples
        config, reader = self.book(language="en")
        home = self.destinations(reader, reader.pages[0])
        self.assertIn("December 2026", reader.pages[home["calendar-2026-12"]].extract_text())
        self.assertIn("Weekly tasks", reader.pages[home["week-2026-12-28"]].extract_text())
        output = io.BytesIO()
        generate_dated_samples(config, output)
        preview = PdfReader(output)
        self.assertEqual(len(preview.pages), 5)
        self.assertTrue(all(not p.get("/Annots") for p in preview.pages))

    def test_undated_published_examples_are_byte_identical(self):
        from pathlib import Path
        from planner_config import PlannerConfig
        from planner_pdf import generate_pdf
        for language in ("fr", "en"):
            config = PlannerConfig(language=language)
            output = io.BytesIO()
            generate_pdf(config, output)
            expected = Path(__file__).resolve().parents[1] / "examples" / config.pdf_filename
            self.assertEqual(output.getvalue(), expected.read_bytes())
