import io
import unittest
from datetime import date

from pypdf import PdfReader


class DatedPDFTests(unittest.TestCase):
    def test_weekend_calendar_cells_remain_without_links_and_navigation_skips_them(self):
        config, reader = self.book(include_weekends=False)
        home = self.destinations(reader, reader.pages[0])
        january = reader.pages[home["calendar-2027-01"]]
        links = self.destinations(reader, january)
        self.assertNotIn("2027-01-02", links)
        self.assertNotIn("2027-01-03", links)
        self.assertIn("2", january.extract_text().split())
        self.assertIn("3", january.extract_text().split())
        friday, monday = links["2027-01-01"], links["2027-01-04"]
        self.assertEqual(self.destinations(reader, reader.pages[friday])["Next day"], monday)
        self.assertEqual(self.destinations(reader, reader.pages[monday])["Previous day"], friday)
        self.assertEqual(self.destinations(reader, reader.pages[friday + 2])["Next"], monday)
        weekly = self.destinations(reader, reader.pages[home["week-2026-12-28"]])
        self.assertNotIn("2027-01-02", weekly)
        self.assertEqual(weekly["2027-01-01"], friday)
        for page in reader.pages:
            self.destinations(reader, page)  # Every internal link must resolve.

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
        self.assertIn("S53", reader.pages[week53].extract_text())
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
        self.assertEqual(len(preview.pages), 6)
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

    def test_dated_published_examples_are_byte_identical(self):
        from pathlib import Path
        from dated_planner_config import DatedPlannerConfig
        from dated_planner_pdf import generate_dated_pdf
        from planner_config import PlannerConfig
        for language in ("fr", "en"):
            with self.subTest(language=language):
                config = DatedPlannerConfig(base=PlannerConfig(language=language),
                                            start_date="2026-09-16")
                output = io.BytesIO()
                generate_dated_pdf(config, output)
                expected = (Path(__file__).resolve().parents[1]
                            / "examples/dated" / config.pdf_filename)
                self.assertEqual(output.getvalue(), expected.read_bytes())

    def test_legacy_json_loads_without_device_density_or_module_fields(self):
        from dated_planner_config import DatedPlannerConfig
        from planner_config import PlannerConfig
        legacy_base = {"list_count": 10, "tasks_per_list": 40, "detail_pages": 2,
                       "days": 200, "notes_pages": 2, "typography": "manrope",
                       "title": "Meetings & actions", "list_names": [], "language": "fr"}
        base = PlannerConfig.from_dict(legacy_base)
        self.assertEqual(base, PlannerConfig())
        legacy = {"base": legacy_base, "start_date": "2026-09-16", "months": 3,
                  "week_pages": 1, "weekly_tasks": 40, "include_weekends": True}
        config = DatedPlannerConfig.from_dict(legacy)
        self.assertEqual(config, DatedPlannerConfig(start_date="2026-09-16"))
        self.assertEqual(config.pdf_filename,
                         "dated-aipaper-manrope-fr-2026-09-16-2026-12-15.pdf")

    def long_book(self, months=6, **kwargs):
        from dated_planner_config import DatedPlannerConfig
        from dated_planner_pdf import generate_dated_pdf
        from planner_config import PlannerConfig
        base = PlannerConfig(list_count=1, tasks_per_list=1, detail_pages=1,
                             notes_pages=1, language=kwargs.pop("language", "fr"))
        config = DatedPlannerConfig(base=base, start_date="2026-09-16",
                                    months=months, **kwargs)
        output = io.BytesIO()
        self.assertEqual(generate_dated_pdf(config, output), config.total_pages)
        return config, PdfReader(output)

    def test_long_notebook_replaces_the_week_rail_with_reachable_months(self):
        config, reader = self.long_book()
        self.assertTrue(config.long_navigation)
        keys = [f"calendar-{month:%Y-%m}" for month in config.calendar_months]
        for index, page in enumerate(reader.pages):
            links = self.destinations(reader, page)
            for key in keys:
                self.assertIn(key, links, f"page {index} ne rejoint pas {key}")
        home = self.destinations(reader, reader.pages[0])
        self.assertNotIn(config.week_key(config.weeks[5]), home)
        self.assertIn(config.week_key(config.weeks[0]), home)
        january = reader.pages[home["calendar-2027-01"]]
        calendar_links = self.destinations(reader, january)
        for monday in config.weeks:
            if monday.month == 1 and monday.year == 2027:
                self.assertIn(config.week_key(monday), calendar_links)

    def test_long_notebook_adds_explicit_week_steps_and_a_week_return(self):
        config, reader = self.long_book()
        home = self.destinations(reader, reader.pages[0])
        first_week = home[config.week_key(config.weeks[0])]
        middle = self.destinations(reader, reader.pages[first_week + 2])
        self.assertEqual(middle["Previous week"], first_week + 1)
        self.assertEqual(middle["Next week"], first_week + 3)
        self.assertIn("S39", reader.pages[first_week + 2].extract_text())
        self.assertIn("S41", reader.pages[first_week + 2].extract_text())
        self.assertNotIn("Previous week", self.destinations(reader, reader.pages[first_week]))
        last = len(config.weeks) - 1
        self.assertNotIn("Next week", self.destinations(reader, reader.pages[first_week + last]))
        january = self.destinations(reader, reader.pages[home["calendar-2027-01"]])
        day = january["2027-01-04"]
        week_page = self.destinations(reader, reader.pages[day])["week-2027-01-04"]
        notes = self.destinations(reader, reader.pages[day + 1])
        self.assertEqual(notes["week-2027-01-04"], week_page)
        self.assertIn("S01", reader.pages[day + 1].extract_text())

    def test_long_notebook_shows_the_year_where_labels_would_be_ambiguous(self):
        config, reader = self.long_book(months=12)
        self.assertEqual(len(config.calendar_months), 13)
        home_text = reader.pages[0].extract_text()
        self.assertIn("Septembre 2026", home_text)
        self.assertIn("Septembre 2027", home_text)
        rail_text = reader.pages[1].extract_text()
        self.assertIn("26", rail_text)
        self.assertIn("27", rail_text)
        ids = {page.indirect_reference.idnum for page in reader.pages}
        for page in reader.pages:
            for ref in page.get("/Annots", []):
                annotation = ref.get_object()
                self.assertIn(annotation["/Dest"][0].idnum, ids)
                x0, y0, x1, y1 = map(float, annotation["/Rect"])
                self.assertTrue(0 <= x0 < x1 <= 460.8)
                self.assertTrue(0 <= y0 < y1 <= 614.4)

    def test_long_notebook_english_edition_keeps_the_same_destinations(self):
        french_config, french = self.long_book()
        english_config, english = self.long_book(language="en")
        self.assertEqual(len(french.pages), len(english.pages))
        for fr, en in zip(french.pages, english.pages):
            self.assertEqual(list(self.destinations(french, fr).values()),
                             list(self.destinations(english, en).values()))
        self.assertIn("SEPT", french.pages[1].extract_text())
        self.assertIn("SEP", english.pages[1].extract_text())
        notes = english.pages[self.destinations(english, english.pages[0])
                              [english_config.week_key(english_config.weeks[0])]]
        self.assertIn("Weekly tasks", notes.extract_text())
