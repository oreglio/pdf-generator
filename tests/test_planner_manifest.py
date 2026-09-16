import io
import unittest
from dataclasses import replace

from pypdf import PdfReader

from dated_planner_config import DatedPlannerConfig
from dated_planner_pdf import generate_dated_pdf
from planner_config import PlannerConfig
from planner_manifest import (build_manifest, first_of, list_key, sheet_key,
                              sheet_of, sheets)
from planner_pdf import generate_pdf


SMALL = "viwoods-aipaper-mini"


class SheetArithmeticTests(unittest.TestCase):
    def test_day_indexes_keep_uniform_blocks(self):
        self.assertEqual(sheets(41, 40, balance=False), ((1, 40), (41, 41)))
        self.assertEqual(sheets(45, 28, balance=False), ((1, 28), (29, 45)))

    def test_sheets_cover_every_item_once_without_gaps(self):
        for total in (1, 7, 26, 27, 40, 52):
            for per_page in (1, 5, 26, 40, 100):
                with self.subTest(total=total, per_page=per_page):
                    spread = sheets(total, per_page)
                    covered = [item for first, last in spread
                               for item in range(first, last + 1)]
                    self.assertEqual(covered, list(range(1, total + 1)))
                    for number, (first, last) in enumerate(spread, 1):
                        self.assertEqual(sheet_of(first, total, per_page), number)
                        self.assertEqual(sheet_of(last, total, per_page), number)
                    lengths = {last - first + 1 for first, last in spread}
                    self.assertLessEqual(max(lengths) - min(lengths), 1)

    def test_first_sheet_keeps_the_historical_destination(self):
        self.assertEqual(sheet_key("list-1", 1), "list-1")
        self.assertEqual(sheet_key("list-1", 2), "list-1-page-2")
        self.assertEqual(list_key(1, 40, 40, 40), "list-1")
        self.assertEqual(list_key(1, 21, 40, 26), "list-1-page-2")
        self.assertEqual(list_key(1, 20, 40, 26), "list-1")
        self.assertEqual(list_key(3, 1, 40, 26), "list-3")


class ManifestStructureTests(unittest.TestCase):
    def notebooks(self):
        base = PlannerConfig(days=45, list_count=2, tasks_per_list=40,
                             detail_pages=1, notes_pages=1)
        yield "aipaper", base
        yield "mini", replace(base, device=SMALL)
        yield "aéré", replace(base, density="comfortable")
        yield "dated", DatedPlannerConfig(base=replace(base, list_count=1),
                                          start_date="2026-09-16", months=1,
                                          week_pages=2, weekly_tasks=40)
        yield "dated mini", DatedPlannerConfig(
            base=replace(base, device=SMALL, list_count=1),
            start_date="2026-09-16", months=1, week_pages=2, weekly_tasks=40)

    def test_manifest_is_the_page_count_with_unique_keys(self):
        for name, config in self.notebooks():
            with self.subTest(notebook=name):
                manifest = build_manifest(config)
                self.assertEqual(len(manifest), config.total_pages)
                keys = [spec.key for spec in manifest]
                self.assertEqual(len(keys), len(set(keys)))
                self.assertEqual(keys[0], "home")
                self.assertFalse(any(spec.kind == "task-list" and not spec.holds_items
                                     for spec in manifest))

    def test_no_task_line_is_lost_or_duplicated_when_a_list_is_split(self):
        for name, config in self.notebooks():
            base = getattr(config, "base", config)
            with self.subTest(notebook=name):
                manifest = build_manifest(config)
                for number in range(1, base.list_count + 1):
                    covered = [item
                               for spec in manifest
                               if spec.kind == "task-list" and spec.reference == str(number)
                               for item in range(spec.first_item, spec.last_item + 1)]
                    self.assertEqual(covered, list(range(1, base.tasks_per_list + 1)))

    def test_small_screen_and_comfort_add_sheets_rather_than_dropping_tasks(self):
        reference = PlannerConfig(days=1, list_count=1, tasks_per_list=40, detail_pages=1)
        self.assertEqual(reference.list_sheets, 1)
        self.assertEqual(replace(reference, device=SMALL).list_sheets, 2)
        self.assertEqual(replace(reference, density="comfortable").list_sheets, 2)
        for changes in ({"device": SMALL}, {"density": "comfortable"}):
            config = replace(reference, **changes)
            with self.subTest(changes=changes):
                self.assertGreater(config.total_pages, reference.total_pages)
                self.assertEqual(config.tasks_per_list, 40)

    def test_weekly_list_split_keeps_its_week_and_its_task_count(self):
        config = DatedPlannerConfig(
            base=PlannerConfig(device=SMALL, list_count=1, tasks_per_list=2,
                               detail_pages=1, notes_pages=0),
            start_date="2026-09-16", months=1, week_pages=2, weekly_tasks=40)
        self.assertEqual(config.week_sheets, 2)
        manifest = build_manifest(config)
        for monday in config.weeks:
            weekly = [spec for spec in manifest
                      if spec.kind == "weekly" and spec.reference == monday.isoformat()]
            self.assertEqual(len(weekly), 4)
            self.assertEqual([spec.key for spec in weekly], [
                f"week-{monday}-1", f"week-{monday}-1-page-2",
                f"week-{monday}-2", f"week-{monday}-2-page-2"])
            for part in (1, 2):
                covered = [item for spec in weekly if spec.part == part
                           for item in range(spec.first_item, spec.last_item + 1)]
                self.assertEqual(covered, list(range(1, 41)))
            self.assertTrue(all(spec.sheets == 2 for spec in weekly))


class SplitRenderingTests(unittest.TestCase):
    @staticmethod
    def destinations(reader, page):
        ids = {p.indirect_reference.idnum: i for i, p in enumerate(reader.pages)}
        return {str(a.get_object()["/Contents"]): ids[a.get_object()["/Dest"][0].idnum]
                for a in page.get("/Annots", [])}

    def book(self, **changes):
        config = replace(PlannerConfig(days=3, list_count=1, tasks_per_list=40,
                                       detail_pages=1, notes_pages=0), **changes)
        output = io.BytesIO()
        self.assertEqual(generate_pdf(config, output), config.total_pages)
        return config, PdfReader(output)

    def test_split_list_numbers_stay_continuous_and_tabs_open_the_first_sheet(self):
        config, reader = self.book(device=SMALL)
        manifest = build_manifest(config)
        keys = {spec.key: index for index, spec in enumerate(manifest)}
        self.assertIn("list-1-page-2", keys)
        first, second = reader.pages[keys["list-1"]], reader.pages[keys["list-1-page-2"]]
        numbers = [f"{item:02d}" for item in range(1, 21)]
        self.assertTrue(all(value in first.extract_text() for value in numbers))
        self.assertIn("21", second.extract_text())
        self.assertIn("40", second.extract_text())
        self.assertIn("01 – 20", first.extract_text())
        self.assertIn("21 – 40", second.extract_text())
        self.assertIn("2/2 >", first.extract_text())
        self.assertIn("< 1/2", second.extract_text())
        self.assertEqual(self.destinations(reader, first)["Suite"], keys["list-1-page-2"])
        self.assertEqual(self.destinations(reader, second)["1/2"], keys["list-1"])
        for page in reader.pages:
            self.assertEqual(self.destinations(reader, page)["Liste 01"], keys["list-1"])

    def test_task_notes_return_to_the_sheet_holding_their_line(self):
        config, reader = self.book(device=SMALL)
        keys = {spec.key: index for index, spec in enumerate(build_manifest(config))}
        for item, expected in ((1, "list-1"), (20, "list-1"),
                               (21, "list-1-page-2"), (40, "list-1-page-2")):
            with self.subTest(item=item):
                page = reader.pages[keys[f"task-1-{item}-1"]]
                sheet = 1 if expected == "list-1" else 2
                links = self.destinations(reader, page)
                self.assertEqual(links["Retour liste 01"], keys[expected])
                self.assertEqual(links[f"Liste 01 {sheet}/2"], keys[expected])
                self.assertEqual(links["Liste 01"], keys["list-1"])

    def test_every_destination_resolves_and_fits_on_split_notebooks(self):
        for changes in ({"device": SMALL}, {"density": "comfortable"},
                        {"device": "boox-note-max"}, {"device": "ipad-pro-11-m4"}):
            with self.subTest(changes=changes):
                config, reader = self.book(**changes)
                ids = {page.indirect_reference.idnum for page in reader.pages}
                width, height = config.layout.width, config.layout.height
                for page in reader.pages:
                    for ref in page.get("/Annots", []):
                        annotation = ref.get_object()
                        self.assertIn(annotation["/Dest"][0].idnum, ids)
                        x0, y0, x1, y1 = map(float, annotation["/Rect"])
                        self.assertTrue(0 <= x0 < x1 <= width + 0.01)
                        self.assertTrue(0 <= y0 < y1 <= height + 0.01)

    def test_dated_split_weeks_stay_navigable_on_a_small_screen(self):
        config = DatedPlannerConfig(
            base=PlannerConfig(device=SMALL, list_count=1, tasks_per_list=2,
                               detail_pages=1, notes_pages=0),
            start_date="2026-09-16", months=1, week_pages=1, weekly_tasks=40)
        output = io.BytesIO()
        self.assertEqual(generate_dated_pdf(config, output), config.total_pages)
        reader = PdfReader(output)
        keys = {spec.key: index for index, spec in enumerate(build_manifest(config))}
        monday = config.weeks[0]
        first, second = keys[f"week-{monday}-1"], keys[f"week-{monday}-1-page-2"]
        self.assertEqual(self.destinations(reader, reader.pages[first])["Next"], second)
        self.assertEqual(self.destinations(reader, reader.pages[second])["Previous"], first)
        self.assertIn("2/2", reader.pages[second].extract_text())
        home = self.destinations(reader, reader.pages[0])
        self.assertEqual(home[config.week_key(monday)], first)
        ids = {page.indirect_reference.idnum for page in reader.pages}
        for page in reader.pages:
            for ref in page.get("/Annots", []):
                self.assertIn(ref.get_object()["/Dest"][0].idnum, ids)

    def test_previews_follow_the_manifest_instead_of_a_fixed_count(self):
        from dated_planner_pdf import generate_dated_samples
        from planner_pdf import generate_samples
        for changes in ({}, {"device": SMALL}, {"density": "comfortable"}):
            config = replace(PlannerConfig(days=2, list_count=1, tasks_per_list=40,
                                           detail_pages=1), **changes)
            with self.subTest(changes=changes):
                output = io.BytesIO()
                self.assertEqual(generate_samples(config, output), 3)
                self.assertEqual(len(PdfReader(output).pages), 3)
                dated = DatedPlannerConfig(base=config, start_date="2026-09-16", months=1)
                output = io.BytesIO()
                self.assertEqual(generate_dated_samples(dated, output), 5)
                self.assertEqual(len(PdfReader(output).pages), 5)
                self.assertEqual(first_of(build_manifest(config), "task-list").key, "list-1")


if __name__ == "__main__":
    unittest.main()
