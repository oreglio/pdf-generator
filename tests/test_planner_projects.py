import io
import unittest
from dataclasses import replace
from datetime import date

from pypdf import PdfReader

from dated_planner_config import MAX_DAYS, DatedPlannerConfig
from dated_planner_pdf import generate_dated_pdf
from planner_config import PlannerConfig
from planner_manifest import build_manifest
from planner_pdf import generate_pdf


def destinations(reader, page):
    ids = {p.indirect_reference.idnum: i for i, p in enumerate(reader.pages)}
    return {str(a.get_object()['/Contents']): ids[a.get_object()['/Dest'][0].idnum]
            for a in page.get('/Annots', [])}


class ExactDatesTests(unittest.TestCase):
    def test_without_an_explicit_end_the_period_still_counts_months(self):
        config = DatedPlannerConfig(start_date='2026-09-16')
        self.assertIsNone(config.end_date_override)
        self.assertEqual(config.end_date, date(2026, 12, 15))
        self.assertEqual(DatedPlannerConfig.from_dict({'start_date': '2026-09-16'}).end_date,
                         date(2026, 12, 15))

    def test_an_explicit_end_is_inclusive_and_ignores_the_number_of_months(self):
        config = DatedPlannerConfig(start_date='2026-09-16', months=12,
                                    end_date_override='2026-10-05')
        self.assertEqual(config.end_date, date(2026, 10, 5))
        self.assertEqual(len(config.dates), 20)
        self.assertEqual(config.dates[-1], date(2026, 10, 5))
        self.assertIn('2026-10-05', config.pdf_filename)

    def test_a_single_day_a_month_end_and_a_leap_day(self):
        for start, end, length in (('2026-09-16', '2026-09-16', 1),
                                   ('2026-01-31', '2026-02-28', 29),
                                   ('2024-02-01', '2024-02-29', 29),
                                   ('2026-12-28', '2027-01-03', 7)):
            with self.subTest(start=start, end=end):
                config = DatedPlannerConfig(start_date=start, end_date_override=end)
                self.assertEqual(len(config.dates), length)
                self.assertEqual(config.dates[0], date.fromisoformat(start))
                self.assertEqual(config.dates[-1], date.fromisoformat(end))

    def test_impossible_periods_are_refused_with_a_usable_message(self):
        cases = (
            ({'end_date_override': '2026-09-15'}, 'précéder'),
            ({'end_date_override': '2027-09-17'}, str(MAX_DAYS)),
            ({'end_date_override': '2026-02-30'}, 'date de fin'),
            ({'end_date_override': 20260916}, 'date de fin'),
            ({'start_date': '2026-09-19', 'end_date_override': '2026-09-20',
              'include_weekends': False}, 'aucune journée'),
        )
        for changes, expected in cases:
            start = changes.pop('start_date', '2026-09-16')
            with self.subTest(changes=changes), self.assertRaises(ValueError) as refusal:
                DatedPlannerConfig(start_date=start, **changes)
            self.assertIn(expected, str(refusal.exception))
        self.assertEqual(len(DatedPlannerConfig(start_date='2026-09-16',
                                                end_date_override='2027-09-16').dates), MAX_DAYS)

    def test_the_navigation_variant_follows_the_effective_period(self):
        for end, long in (('2026-12-15', False), ('2027-01-16', True),
                          ('2026-09-30', False), ('2027-09-15', True)):
            with self.subTest(end=end):
                config = DatedPlannerConfig(start_date='2026-09-16', end_date_override=end)
                self.assertEqual(config.long_navigation, long)
        self.assertFalse(DatedPlannerConfig(start_date='2026-09-16', months=3).long_navigation)
        self.assertTrue(DatedPlannerConfig(start_date='2026-01-01', months=4).long_navigation)

    def test_an_exact_period_generates_and_stays_navigable(self):
        config = DatedPlannerConfig(
            base=PlannerConfig(list_count=1, tasks_per_list=2, detail_pages=1, notes_pages=0),
            start_date='2026-09-16', end_date_override='2026-10-05')
        output = io.BytesIO()
        self.assertEqual(generate_dated_pdf(config, output), config.total_pages)
        reader = PdfReader(output)
        ids = {page.indirect_reference.idnum for page in reader.pages}
        for page in reader.pages:
            for ref in page.get('/Annots', []):
                self.assertIn(ref.get_object()['/Dest'][0].idnum, ids)
        self.assertEqual(DatedPlannerConfig.from_dict(config.to_dict()), config)

    def test_an_old_configuration_without_the_field_still_loads(self):
        legacy = {'start_date': '2026-09-16', 'months': 3, 'week_pages': 1,
                  'weekly_tasks': 40, 'include_weekends': True}
        config = DatedPlannerConfig.from_dict(legacy)
        self.assertIsNone(config.end_date_override)
        self.assertEqual(config.end_date, date(2026, 12, 15))


class ProjectTests(unittest.TestCase):
    def book(self, **changes):
        config = replace(PlannerConfig(days=2, list_count=1, tasks_per_list=1,
                                       detail_pages=1, notes_pages=0), **changes)
        output = io.BytesIO()
        self.assertEqual(generate_pdf(config, output), config.total_pages)
        return config, PdfReader(output), {spec.key: index for index, spec
                                           in enumerate(build_manifest(config))}

    def test_no_project_means_no_page_and_no_link(self):
        self.assertEqual(PlannerConfig().project_count, 0)
        config, reader, keys = self.book()
        self.assertFalse(any(key.startswith('project') for key in keys))
        for page in reader.pages:
            self.assertFalse(any('rojet' in title or 'roject' in title
                                 for title in destinations(reader, page)))

    def test_an_index_then_one_sheet_and_its_notes_per_project(self):
        plain, _, _ = self.book()
        config, reader, keys = self.book(project_count=3, project_notes_pages=2)
        self.assertEqual(config.total_pages - plain.total_pages, 1 + 3 * 3)
        self.assertEqual([key for key in keys if key.startswith('project')],
                         ['projects', 'project-1', 'project-1-notes-1', 'project-1-notes-2',
                          'project-2', 'project-2-notes-1', 'project-2-notes-2',
                          'project-3', 'project-3-notes-1', 'project-3-notes-2'])
        without_notes, _, keys = self.book(project_count=2, project_notes_pages=0)
        self.assertEqual([key for key in keys if key.startswith('project')],
                         ['projects', 'project-1', 'project-2'])

    def test_every_sheet_returns_to_the_index_and_to_the_backlog(self):
        config, reader, keys = self.book(project_count=2, project_notes_pages=1)
        for number in (1, 2):
            sheet = destinations(reader, reader.pages[keys[f'project-{number}']])
            notes = destinations(reader, reader.pages[keys[f'project-{number}-notes-1']])
            with self.subTest(project=number):
                self.assertEqual(sheet['Projets'], keys['projects'])
                self.assertEqual(sheet['Retour aux projets'], keys['projects'])
                self.assertEqual(sheet['Liste 01'], keys['list-1'])
                self.assertEqual(sheet['Mes listes'], keys['home'])
                self.assertEqual(notes[f'Projet {number:02d}'], keys[f'project-{number}'])
                self.assertEqual(notes['Liste 01'], keys['list-1'])
        home = destinations(reader, reader.pages[0])
        self.assertEqual(home['Projets'], keys['projects'])
        index = destinations(reader, reader.pages[keys['projects']])
        self.assertEqual(index['Projet 01'], keys['project-1'])
        self.assertEqual(index['Projet 02'], keys['project-2'])

    def test_named_projects_and_their_fixed_backlog_reference(self):
        config, reader, keys = self.book(project_count=2, project_names=('Folio',))
        self.assertEqual(config.project_name(1), 'Folio')
        self.assertEqual(config.project_name(2), 'Projet 02')
        sheet = reader.pages[keys['project-1']].extract_text()
        for section in ('Objectif', 'Prochaines actions', 'Décisions', 'Notes', 'BKLG', 'Folio'):
            self.assertIn(section, sheet)

    def test_the_english_edition_and_the_dated_notebook_carry_projects_too(self):
        config, reader, keys = self.book(project_count=1, language='en', project_notes_pages=1)
        sheet = reader.pages[keys['project-1']].extract_text()
        for section in ('Goal', 'Next actions', 'Decisions', 'PROJECT 01'):
            self.assertIn(section, sheet)
        self.assertIn('Back to projects', destinations(reader, reader.pages[keys['project-1']]))
        dated = DatedPlannerConfig(base=replace(config, language='fr'),
                                   start_date='2026-09-16', months=1)
        output = io.BytesIO()
        self.assertEqual(generate_dated_pdf(dated, output), dated.total_pages)
        reader = PdfReader(output)
        keys = {spec.key: index for index, spec in enumerate(build_manifest(dated))}
        self.assertEqual(destinations(reader, reader.pages[0])['Projets'], keys['projects'])
        ids = {page.indirect_reference.idnum for page in reader.pages}
        for page in reader.pages:
            for ref in page.get('/Annots', []):
                self.assertIn(ref.get_object()['/Dest'][0].idnum, ids)

    def test_every_page_opens_each_project_in_one_tap(self):
        config, reader, keys = self.book(project_count=3, project_notes_pages=1)
        for index, page in enumerate(reader.pages):
            links = destinations(reader, page)
            with self.subTest(page=index):
                self.assertEqual(links['Projets'], keys['projects'])
                for number in (1, 2, 3):
                    self.assertEqual(links[f'Projet {number:02d}'], keys[f'project-{number}'])

    def test_a_meeting_offers_a_fixed_place_to_write_its_project(self):
        _, without, _ = self.book()
        _, with_projects, keys = self.book(project_count=2)
        self.assertNotIn('PROJET', without.pages[2].extract_text())
        self.assertIn('PROJET', with_projects.pages[keys['day-1']].extract_text())
        self.assertIn('Objectives', with_projects.pages[keys['day-1']].extract_text())

    def test_a_crowded_rail_keeps_the_index_when_tabs_no_longer_fit(self):
        from dated_planner_config import DatedPlannerConfig
        from dated_planner_pdf import generate_dated_pdf
        base = replace(PlannerConfig(list_count=10, tasks_per_list=2, detail_pages=1,
                                     notes_pages=0, project_count=12),
                       device='custom', custom_width_mm=100, custom_height_mm=150)
        config = DatedPlannerConfig(base=base, start_date='2026-09-16', months=12)
        output = io.BytesIO()
        self.assertEqual(generate_dated_pdf(config, output), config.total_pages)
        reader = PdfReader(output)
        keys = {spec.key: index for index, spec in enumerate(build_manifest(config))}
        links = destinations(reader, reader.pages[keys['day-1']])
        self.assertEqual(links['Projets'], keys['projects'])
        for page in reader.pages:
            for ref in page.get('/Annots', []):
                x0, y0, x1, y1 = map(float, ref.get_object()['/Rect'])
                self.assertLess(y0, y1, 'rectangle inversé dans la barre latérale')
                self.assertGreaterEqual(y0, 0)

    def test_ten_note_pages_per_project_are_all_one_tap_away(self):
        config, reader, keys = self.book(project_count=2, project_notes_pages=10)
        self.assertEqual(config.project_notes_pages, 10)
        pages = [keys['project-1']] + [keys[f'project-1-notes-{part}'] for part in range(1, 11)]
        for index in pages:
            links = destinations(reader, reader.pages[index])
            with self.subTest(page=index):
                for part in range(1, 11):
                    self.assertEqual(links[f'Projet 01 / Notes {part:02d}'],
                                     keys[f'project-1-notes-{part}'])
                self.assertNotIn('Projet 02 / Notes 01', links)
        self.assertIn('NOTES', reader.pages[keys['project-1']].extract_text())

    def test_no_note_page_means_no_note_bar(self):
        config, reader, keys = self.book(project_count=1, project_notes_pages=0)
        links = destinations(reader, reader.pages[keys['project-1']])
        self.assertFalse(any('Notes' in title for title in links))

    def test_invalid_project_settings_are_refused(self):
        for changes in ({'project_count': -1}, {'project_count': 13}, {'project_count': True},
                        {'project_notes_pages': 11}, {'project_notes_pages': -1},
                        {'project_names': ('a', 'b')}, {'project_names': ('x' * 25,)},
                        {'project_names': 'Folio'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(PlannerConfig(project_count=1), **changes)
        self.assertEqual(PlannerConfig.from_dict(PlannerConfig(project_count=2).to_dict()),
                         PlannerConfig(project_count=2))


if __name__ == '__main__':
    unittest.main()
