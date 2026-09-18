import io
import unittest
from dataclasses import replace

from pypdf import PdfReader

from dated_planner_config import DatedPlannerConfig
from dated_planner_pdf import generate_dated_pdf
from planner_config import PlannerConfig
from planner_manifest import build_manifest
from planner_note_styles import NOTE_STYLES, draw_note_background
from planner_pdf import generate_pdf


class Recorder:
    """Collects the drawing calls a background emits, in order."""

    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args))
        return record


class BackgroundTests(unittest.TestCase):
    def test_each_style_stays_inside_its_bounds(self):
        bounds = (24, 67, 400, 500)
        for style in NOTE_STYLES:
            with self.subTest(style=style):
                recorder = Recorder()
                draw_note_background(recorder, bounds, style, 14)
                for name, args in recorder.calls:
                    if name == 'line':
                        x0, y0, x1, y1 = args
                        self.assertTrue(24 <= x0 <= 400 and 24 <= x1 <= 400)
                        self.assertTrue(67 <= y0 <= 500 and 67 <= y1 <= 500)
                    elif name == 'circle':
                        x, y, _ = args[:3]
                        self.assertTrue(24 <= x <= 400 and 67 <= y <= 500)

    def test_blank_and_degenerate_bounds_draw_nothing(self):
        for style, bounds, spacing in (('blank', (24, 67, 400, 500), 14),
                                       ('lined', (24, 67, 400, 500), 0),
                                       ('grid', (400, 67, 24, 500), 14),
                                       ('dots', (24, 500, 400, 67), 14)):
            with self.subTest(style=style):
                recorder = Recorder()
                draw_note_background(recorder, bounds, style, spacing)
                self.assertEqual(recorder.calls, [])

    def test_grid_draws_both_directions_and_an_unknown_style_is_refused(self):
        recorder = Recorder()
        draw_note_background(recorder, (24, 67, 100, 200), 'grid', 20)
        horizontal = [args for name, args in recorder.calls if name == 'line' and args[1] == args[3]]
        vertical = [args for name, args in recorder.calls if name == 'line' and args[0] == args[2]]
        self.assertTrue(horizontal and vertical)
        with self.assertRaises(ValueError):
            draw_note_background(recorder, (24, 67, 100, 200), 'squared', 20)


class NotebookStyleTests(unittest.TestCase):
    def book(self, **changes):
        config = replace(PlannerConfig(days=2, list_count=1, tasks_per_list=1,
                                       detail_pages=1, notes_pages=1), **changes)
        output = io.BytesIO()
        self.assertEqual(generate_pdf(config, output), config.total_pages)
        return config, PdfReader(output)

    def test_defaults_keep_the_historical_backgrounds(self):
        self.assertEqual(PlannerConfig().meeting_note_style, 'lined')
        self.assertEqual(PlannerConfig().task_note_style, 'dots')

    def test_every_combination_renders_with_the_same_pages_and_links(self):
        reference, expected = self.book()
        for meeting in NOTE_STYLES:
            for task in NOTE_STYLES:
                with self.subTest(meeting=meeting, task=task):
                    config, reader = self.book(meeting_note_style=meeting, task_note_style=task)
                    self.assertEqual(len(reader.pages), len(expected.pages))
                    for page, model in zip(reader.pages, expected.pages):
                        self.assertEqual([a.get_object()['/Rect'] for a in page.get('/Annots', [])],
                                         [a.get_object()['/Rect'] for a in model.get('/Annots', [])])

    def test_a_blank_background_removes_the_rules_without_touching_the_titles(self):
        _, ruled = self.book()
        _, blank = self.book(meeting_note_style='blank')
        notes_page = 3
        self.assertIn('NOTES 01', blank.pages[notes_page].extract_text())
        self.assertLess(len(blank.pages[notes_page].get_contents().get_data()),
                        len(ruled.pages[notes_page].get_contents().get_data()))

    def test_unknown_styles_are_refused_by_the_configuration(self):
        for changes in ({'meeting_note_style': 'squared'}, {'task_note_style': None},
                        {'task_note_style': 'Ligné'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(PlannerConfig(), **changes)


class MonthlyPrioritiesTests(unittest.TestCase):
    @staticmethod
    def destinations(reader, page):
        ids = {p.indirect_reference.idnum: i for i, p in enumerate(reader.pages)}
        return {str(a.get_object()['/Contents']): ids[a.get_object()['/Dest'][0].idnum]
                for a in page.get('/Annots', [])}

    def book(self, language='fr', **changes):
        base = PlannerConfig(list_count=1, tasks_per_list=1, detail_pages=1,
                             notes_pages=0, language=language)
        config = DatedPlannerConfig(base=base, start_date='2026-09-16', months=2,
                                    monthly_priorities=True, **changes)
        output = io.BytesIO()
        self.assertEqual(generate_dated_pdf(config, output), config.total_pages)
        return config, PdfReader(output)

    def test_one_page_per_displayed_month_placed_after_its_calendar(self):
        config, reader = self.book()
        manifest = build_manifest(config)
        kinds = [spec.kind for spec in manifest[:2 * len(config.calendar_months) + 1]]
        self.assertEqual(kinds, ['home'] + ['calendar', 'month-plan'] * len(config.calendar_months))
        plain = DatedPlannerConfig(base=config.base, start_date='2026-09-16', months=2)
        self.assertEqual(config.total_pages - plain.total_pages, len(config.calendar_months))
        self.assertFalse(DatedPlannerConfig().monthly_priorities)
        self.assertEqual([spec.key for spec in manifest if spec.kind == 'month-plan'],
                         [f'month-plan-{month:%Y-%m}' for month in config.calendar_months])

    def test_a_priority_page_returns_to_its_calendar_and_opens_its_weeks(self):
        config, reader = self.book()
        keys = {spec.key: index for index, spec in enumerate(build_manifest(config))}
        page = reader.pages[keys['month-plan-2026-09']]
        links = self.destinations(reader, page)
        self.assertEqual(links['Calendar'], keys['calendar-2026-09'])
        weeks = config.month_weeks(config.calendar_months[0])
        self.assertTrue(weeks)
        for monday in weeks:
            self.assertIn(config.week_key(monday), links)
        self.assertEqual(links['Next'], keys['month-plan-2026-10'])
        last = f'month-plan-{config.calendar_months[-1]:%Y-%m}'
        self.assertNotIn('Next', self.destinations(reader, reader.pages[keys[last]]))

    def test_a_partial_month_shows_the_period_it_really_covers(self):
        config, reader = self.book()
        keys = {spec.key: index for index, spec in enumerate(build_manifest(config))}
        first = reader.pages[keys['month-plan-2026-09']].extract_text()
        self.assertIn('16.09 — 30.09.2026', first)
        self.assertIn('PRIORITÉS DU MOIS', first)
        self.assertIn('Septembre 2026', first)
        last = reader.pages[keys['month-plan-2026-11']].extract_text()
        self.assertIn('01.11 — 15.11.2026', last)

    def test_english_month_priorities_and_small_screens(self):
        config, reader = self.book(language='en')
        keys = {spec.key: index for index, spec in enumerate(build_manifest(config))}
        text = reader.pages[keys['month-plan-2026-09']].extract_text()
        self.assertIn('MONTH PRIORITIES', text)
        self.assertIn('September 2026', text)
        self.assertIn('My three priorities', text)
        small = DatedPlannerConfig(
            base=replace(config.base, device='custom', custom_width_mm=125.0,
                         custom_height_mm=167.0),
            start_date='2026-09-16', months=2, monthly_priorities=True)
        output = io.BytesIO()
        self.assertEqual(generate_dated_pdf(small, output), small.total_pages)
        reader = PdfReader(output)
        width = small.base.layout.width
        height = small.base.layout.height
        for page in reader.pages:
            for ref in page.get('/Annots', []):
                x0, y0, x1, y1 = map(float, ref.get_object()['/Rect'])
                self.assertTrue(0 <= x0 < x1 <= width + 0.01)
                self.assertTrue(0 <= y0 < y1 <= height + 0.01)


if __name__ == '__main__':
    unittest.main()


class BackgroundReuseTests(unittest.TestCase):
    """A writing area that comes back is placed again, not drawn again."""

    def notebook(self, **changes):
        from planner_config import PlannerConfig
        from planner_pdf import generate_pdf
        settings = dict(days=6, list_count=1, tasks_per_list=2, detail_pages=2,
                        notes_pages=3, project_count=2, project_notes_pages=3)
        config = PlannerConfig(**dict(settings, **changes))
        output = io.BytesIO()
        generate_pdf(config, output)
        return output.getvalue()

    def page_weights(self, data):
        from pypdf import PdfReader
        weights = []
        for page in PdfReader(io.BytesIO(data)).pages:
            contents = page.get("/Contents")
            contents = contents if isinstance(contents, list) else contents.get_object()
            weights.append(len(contents.get_data()) if not isinstance(contents, list)
                           else sum(len(part.get_object().get_data()) for part in contents))
        return weights

    def test_a_dotted_page_weighs_no_more_than_a_plain_one(self):
        """Left inline, a dotted area costs thousands of circles per page."""
        self.assertLess(max(self.page_weights(self.notebook(meeting_note_style="dots"))),
                        max(self.page_weights(self.notebook(meeting_note_style="blank")))
                        + 4000)

    def test_the_drawing_is_paid_once_however_many_pages_repeat_it(self):
        """What matters is the cost of one more Notes page, not the first."""
        few = len(self.notebook(meeting_note_style="dots", notes_pages=1))
        many = len(self.notebook(meeting_note_style="dots", notes_pages=3))
        added = (many - few) / (2 * 6)  # two more Notes pages on each of six days
        plain = self.notebook(meeting_note_style="blank")
        self.assertLess(added, max(self.page_weights(plain)) + 2000)

    def test_the_historical_lined_pages_are_still_drawn_in_place(self):
        """`lined` is the drawing the published notebooks are compared against."""
        from planner_config import PlannerConfig
        from planner_pages import PlannerPages
        from reportlab.pdfgen import canvas
        pages = PlannerPages(canvas.Canvas(io.BytesIO()), PlannerConfig(days=2))
        forms = []
        pages.c.doForm = lambda name: forms.append(name)
        pages.rules(400, bottom=200, style="lined")
        self.assertEqual(forms, [])
        pages.rules(400, bottom=200, style="grid")
        self.assertEqual(len(forms), 1)
        pages.rules(400, bottom=200, style="grid")  # the same area, placed again
        self.assertEqual(forms, [forms[0], forms[0]])
        pages.rules(390, bottom=200, style="grid")  # another area, its own form
        self.assertNotEqual(forms[-1], forms[0])
