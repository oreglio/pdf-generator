import io
import unittest
from dataclasses import replace
from datetime import date, timedelta

from pypdf import PdfReader

from dated_planner_config import DatedPlannerConfig
from dated_planner_pdf import generate_dated_pdf
from planner_config import MEETING_LAYOUTS, PlannerConfig
from planner_manifest import build_manifest
from planner_pdf import generate_pdf


BASE = PlannerConfig(list_count=1, tasks_per_list=2, detail_pages=1, notes_pages=0)


def destinations(reader, page):
    ids = {p.indirect_reference.idnum: i for i, p in enumerate(reader.pages)}
    return {str(a.get_object()['/Contents']): ids[a.get_object()['/Dest'][0].idnum]
            for a in page.get('/Annots', [])}


class WeeklyOptionTests(unittest.TestCase):
    def book(self, **changes):
        config = DatedPlannerConfig(base=BASE, start_date='2026-09-16', months=1, **changes)
        output = io.BytesIO()
        self.assertEqual(generate_dated_pdf(config, output), config.total_pages)
        return config, PdfReader(output), {spec.key: index for index, spec
                                           in enumerate(build_manifest(config))}

    def test_classic_pages_stay_the_default(self):
        self.assertFalse(DatedPlannerConfig().weekly_overview)
        self.assertFalse(DatedPlannerConfig().weekly_review)
        self.assertEqual(PlannerConfig().meeting_layout, 'classic')
        config, reader, keys = self.book()
        self.assertFalse(any(key.startswith(('week-overview', 'week-review')) for key in keys))

    def test_each_option_adds_exactly_one_page_per_week(self):
        plain, _, _ = self.book()
        for option in ('weekly_overview', 'weekly_review'):
            with self.subTest(option=option):
                config, _, keys = self.book(**{option: True})
                self.assertEqual(config.total_pages - plain.total_pages, len(config.weeks))
                prefix = 'week-overview-' if option == 'weekly_overview' else 'week-review-'
                self.assertEqual(sorted(key for key in keys if key.startswith(prefix)),
                                 sorted(f'{prefix}{monday.isoformat()}' for monday in config.weeks))
        both, _, _ = self.book(weekly_overview=True, weekly_review=True)
        self.assertEqual(both.total_pages - plain.total_pages, 2 * len(both.weeks))

    def test_the_overview_sits_before_the_tasks_and_the_review_after(self):
        config, _, keys = self.book(weekly_overview=True, weekly_review=True, week_pages=2)
        for monday in config.weeks:
            with self.subTest(week=monday):
                self.assertLess(keys[f'week-overview-{monday}'], keys[f'week-{monday}-1'])
                self.assertLess(keys[f'week-{monday}-2'], keys[f'week-review-{monday}'])

    def test_the_overview_opens_its_days_and_never_a_missing_meeting(self):
        config, reader, keys = self.book(weekly_overview=True, include_weekends=False)
        monday = config.weeks[1]
        page = reader.pages[keys[f'week-overview-{monday}']]
        links = destinations(reader, page)
        text = page.extract_text()
        for offset in range(7):
            value = monday + timedelta(days=offset)
            with self.subTest(day=value):
                self.assertIn(f'{value.day:02d}', text)  # Every day stays visible.
                if config.includes_day(value):
                    self.assertEqual(links[value.isoformat()], keys[f'day-{config.day_number(value)}'])
                else:
                    self.assertNotIn(value.isoformat(), links)
        self.assertEqual(links['Next'], keys[f'week-{monday}-1'])
        self.assertEqual(links[config.week_key(monday)], keys[f'week-{monday}-1'])

    def test_a_week_outside_the_period_keeps_its_days_visible_but_inactive(self):
        config, reader, keys = self.book(weekly_overview=True)
        first = config.weeks[0]
        links = destinations(reader, reader.pages[keys[f'week-overview-{first}']])
        self.assertNotIn(date(2026, 9, 14).isoformat(), links)
        self.assertIn(date(2026, 9, 16).isoformat(), links)

    def test_the_review_returns_to_its_tasks_and_opens_the_next_week(self):
        config, reader, keys = self.book(weekly_review=True)
        for index, monday in enumerate(config.weeks):
            links = destinations(reader, reader.pages[keys[f'week-review-{monday}']])
            with self.subTest(week=monday):
                self.assertEqual(links[config.week_key(monday)], keys[f'week-{monday}-1'])
                if index + 1 < len(config.weeks):
                    self.assertEqual(links['Next'], keys[f'week-{config.weeks[index + 1]}-1'])
                else:
                    self.assertNotIn('Next', links)
        text = reader.pages[keys[f'week-review-{config.weeks[0]}']].extract_text()
        for section in ('Terminé', 'À reporter', 'À retenir'):
            self.assertIn(section, text)

    def test_the_task_page_reaches_its_companions_when_they_exist(self):
        config, reader, keys = self.book(weekly_overview=True, weekly_review=True)
        monday = config.weeks[0]
        links = destinations(reader, reader.pages[keys[f'week-{monday}-1']])
        self.assertEqual(links[f'week-overview-{monday}'], keys[f'week-overview-{monday}'])
        self.assertEqual(links[f'week-review-{monday}'], keys[f'week-review-{monday}'])
        _, plain_reader, plain_keys = self.book()
        plain_links = destinations(plain_reader, plain_reader.pages[plain_keys[f'week-{monday}-1']])
        self.assertFalse(any(key.startswith('week-overview') for key in plain_links))

    def test_english_labels_and_a_small_screen_keep_every_link_on_the_page(self):
        config = DatedPlannerConfig(
            base=replace(BASE, language='en', device='viwoods-aipaper-mini'),
            start_date='2026-09-16', months=1, weekly_overview=True, weekly_review=True)
        output = io.BytesIO()
        self.assertEqual(generate_dated_pdf(config, output), config.total_pages)
        reader = PdfReader(output)
        keys = {spec.key: index for index, spec in enumerate(build_manifest(config))}
        overview = reader.pages[keys[f'week-overview-{config.weeks[0]}']].extract_text()
        review = reader.pages[keys[f'week-review-{config.weeks[0]}']].extract_text()
        self.assertIn('AT A GLANCE', overview)
        self.assertIn('Week at a glance', overview)
        self.assertIn('REVIEW', review)
        for section in ('Done', 'To carry over', 'To remember'):
            self.assertIn(section, review)
        width, height = config.base.layout.width, config.base.layout.height
        ids = {page.indirect_reference.idnum for page in reader.pages}
        for page in reader.pages:
            for ref in page.get('/Annots', []):
                annotation = ref.get_object()
                self.assertIn(annotation['/Dest'][0].idnum, ids)
                x0, y0, x1, y1 = map(float, annotation['/Rect'])
                self.assertTrue(0 <= x0 < x1 <= width + 0.01)
                self.assertTrue(0 <= y0 < y1 <= height + 0.01)

    def test_an_empty_week_never_receives_pages_or_tabs(self):
        config = DatedPlannerConfig(base=BASE, start_date='2026-09-19', months=1,
                                    include_weekends=False, week_pages=3,
                                    weekly_overview=True, weekly_review=True)
        output = io.BytesIO()
        self.assertEqual(generate_dated_pdf(config, output), config.total_pages)
        reader = PdfReader(output)
        keys = {spec.key: index for index, spec in enumerate(build_manifest(config))}
        self.assertNotIn('week-2026-09-14-1', keys)
        self.assertNotIn('week-overview-2026-09-14', keys)
        self.assertNotIn('week-review-2026-09-14', keys)
        for page in reader.pages:
            self.assertFalse(any('2026-09-14' in title
                                 for title in destinations(reader, page)))
        ids = {page.indirect_reference.idnum for page in reader.pages}
        for page in reader.pages:
            for ref in page.get('/Annots', []):
                self.assertIn(ref.get_object()['/Dest'][0].idnum, ids)

    def test_invalid_option_values_are_refused(self):
        for changes in ({'weekly_overview': 1}, {'weekly_review': None},
                        {'weekly_overview': 'true'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                DatedPlannerConfig(start_date='2026-09-16', **changes)


class MeetingLayoutTests(unittest.TestCase):
    def test_the_simplified_meeting_keeps_the_same_destinations(self):
        classic = replace(BASE, days=3, notes_pages=1)
        simple = replace(classic, meeting_layout='notes_actions')
        pages = []
        for config in (classic, simple):
            output = io.BytesIO()
            generate_pdf(config, output)
            pages.append(PdfReader(output))
        self.assertEqual(len(pages[0].pages), len(pages[1].pages))
        for first, second in zip(pages[0].pages, pages[1].pages):
            self.assertEqual([a.get_object()['/Rect'] for a in first.get('/Annots', [])],
                             [a.get_object()['/Rect'] for a in second.get('/Annots', [])])
            self.assertEqual(list(destinations(pages[0], first).items()),
                             list(destinations(pages[1], second).items()))
        meeting = pages[1].pages[2].extract_text()
        self.assertIn('Décisions', meeting)
        self.assertIn('Actions', meeting)
        self.assertNotIn('Agenda', meeting)
        self.assertIn('Notes', meeting)
        self.assertIn('Agenda', pages[0].pages[2].extract_text())

    def test_the_dated_meeting_follows_the_same_choice(self):
        config = DatedPlannerConfig(base=replace(BASE, meeting_layout='notes_actions'),
                                    start_date='2026-09-16', months=1)
        output = io.BytesIO()
        self.assertEqual(generate_dated_pdf(config, output), config.total_pages)
        reader = PdfReader(output)
        keys = {spec.key: index for index, spec in enumerate(build_manifest(config))}
        meeting = reader.pages[keys['day-1']]
        self.assertIn('Décisions', meeting.extract_text())
        self.assertIn(config.week_key(config.weeks[0]), destinations(reader, meeting))

    def test_both_gives_one_meeting_two_pages_then_its_notes(self):
        classic = replace(BASE, days=3, notes_pages=2)
        both = replace(classic, meeting_layout='both')
        self.assertEqual(both.total_pages - classic.total_pages, 3)
        output = io.BytesIO()
        self.assertEqual(generate_pdf(both, output), both.total_pages)
        reader = PdfReader(output)
        keys = {spec.key: index for index, spec in enumerate(build_manifest(both))}
        for day in (1, 2, 3):
            with self.subTest(day=day):
                self.assertEqual(keys[f'day-{day}-actions'], keys[f'day-{day}'] + 1)
                self.assertEqual(keys[f'day-{day}-notes-1'], keys[f'day-{day}-actions'] + 1)
                first = destinations(reader, reader.pages[keys[f'day-{day}']])
                second = destinations(reader, reader.pages[keys[f'day-{day}-actions']])
                self.assertEqual(first['Suite'], keys[f'day-{day}-actions'])
                self.assertEqual(second['Suite'], keys[f'day-{day}-notes-1'])
                self.assertEqual(second[f'Meeting {day:03d}'], keys[f'day-{day}'])
        self.assertIn('Objectives', reader.pages[keys['day-1']].extract_text())
        actions = reader.pages[keys['day-1-actions']].extract_text()
        self.assertIn('Décisions & actions', actions)
        self.assertIn('Actions', actions)
        self.assertNotIn('Objectives', actions)
        self.assertIn('Décisions >', reader.pages[keys['day-1']].extract_text())

    def test_both_chains_the_dated_meeting_to_its_decisions_page(self):
        config = DatedPlannerConfig(base=replace(BASE, meeting_layout='both', notes_pages=0),
                                    start_date='2026-09-16', months=1)
        output = io.BytesIO()
        self.assertEqual(generate_dated_pdf(config, output), config.total_pages)
        reader = PdfReader(output)
        keys = {spec.key: index for index, spec in enumerate(build_manifest(config))}
        first = destinations(reader, reader.pages[keys['day-1']])
        second = destinations(reader, reader.pages[keys['day-1-actions']])
        self.assertEqual(first['Next'], keys['day-1-actions'])
        self.assertEqual(second['Meeting 2026-09-16'], keys['day-1'])
        self.assertEqual(second[config.week_key(config.weeks[0])], keys[f'week-{config.weeks[0]}-1'])
        self.assertEqual(second['Next day'], keys['day-2'])
        self.assertIn('Décisions & actions', reader.pages[keys['day-1-actions']].extract_text())
        english = DatedPlannerConfig(base=replace(BASE, meeting_layout='both', notes_pages=0,
                                                  language='en'),
                                     start_date='2026-09-16', months=1)
        output = io.BytesIO()
        generate_dated_pdf(english, output)
        keys = {spec.key: index for index, spec in enumerate(build_manifest(english))}
        self.assertIn('Decisions & actions',
                      PdfReader(output).pages[keys['day-1-actions']].extract_text())

    def test_both_keeps_the_notes_one_tap_away_from_the_meeting(self):
        both = replace(BASE, days=2, notes_pages=2, meeting_layout='both')
        output = io.BytesIO()
        generate_pdf(both, output)
        reader = PdfReader(output)
        keys = {spec.key: index for index, spec in enumerate(build_manifest(both))}
        first = destinations(reader, reader.pages[keys['day-1']])
        self.assertEqual(first['Notes 001'], keys['day-1-notes-1'])
        self.assertIn('Notes ›', reader.pages[keys['day-1']].extract_text())
        # Without the second page the footer already goes there: no extra tab.
        classic = replace(both, meeting_layout='classic')
        output = io.BytesIO()
        generate_pdf(classic, output)
        plain = PdfReader(output)
        self.assertNotIn('Notes 001', destinations(plain, plain.pages[2]))
        # And none at all when the notebook has no Notes page.
        without = replace(both, notes_pages=0)
        output = io.BytesIO()
        generate_pdf(without, output)
        bare = PdfReader(output)
        keys = {spec.key: index for index, spec in enumerate(build_manifest(without))}
        self.assertNotIn('Notes 001', destinations(bare, bare.pages[keys['day-1']]))

    def test_unknown_layouts_are_refused(self):
        self.assertEqual(set(MEETING_LAYOUTS), {'classic', 'notes_actions', 'both'})
        for value in ('simple', None, 1, ''):
            with self.subTest(value=value), self.assertRaises(ValueError):
                replace(PlannerConfig(), meeting_layout=value)


if __name__ == '__main__':
    unittest.main()
