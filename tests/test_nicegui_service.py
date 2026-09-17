import importlib.util
import io
import json
import pickle
import shutil
import unittest
from dataclasses import replace
from itertools import product

from pypdf import PdfReader

from dated_planner_config import DatedPlannerConfig
from dated_planner_pdf import generate_dated_pdf, generate_dated_samples
from planner_config import PlannerConfig
from planner_pdf import generate_pdf, generate_samples


class NiceGUIServiceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('nicegui_service'),
                             'The independent NiceGUI generation service is missing')
        import nicegui_service
        self.service = nicegui_service
        self.base = PlannerConfig(list_count=2, tasks_per_list=2, detail_pages=2,
                                  days=4, notes_pages=1, list_names=('Work', 'Home'))
        self.dated = DatedPlannerConfig(base=self.base, start_date='2026-12-28',
                                        months=1, week_pages=2, weekly_tasks=4)

    def test_json_roundtrip_preserves_all_configuration_fields(self):
        rich = replace(self.base, device='boox-note-max', density='comfortable',
                       meeting_note_style='grid', task_note_style='blank',
                       meeting_layout='notes_actions', project_count=2,
                       project_names=('Folio',), project_notes_pages=2)
        custom = replace(self.base, device='custom', custom_width_mm=150.0,
                         custom_height_mm=210.0)
        dated = replace(self.dated, base=rich, months=12, monthly_priorities=True,
                        weekly_overview=True, weekly_review=True)
        exact = replace(self.dated, end_date_override='2027-01-15')
        for mode, config in (('undated', self.base), ('dated', self.dated),
                             ('undated', rich), ('undated', custom),
                             ('dated', dated), ('dated', exact)):
            with self.subTest(mode=mode, config=config):
                payload = json.loads(json.dumps(config.to_dict()))
                self.assertEqual(self.service.parse_config(mode, payload), config)
                self.assertEqual(payload, json.loads(json.dumps(config.to_dict())))
        # Every field of both configurations must survive the round trip.
        self.assertEqual(set(rich.to_dict()), set(PlannerConfig.__dataclass_fields__))
        self.assertEqual(set(dated.to_dict()), set(DatedPlannerConfig.__dataclass_fields__))

    def test_full_pdf_bytes_and_navigation_match_each_existing_engine(self):
        for language, typography in product(('fr', 'en'),
                                            ('manrope', 'manrope-contrast', 'atkinson')):
            base = replace(self.base, language=language, typography=typography)
            dated = replace(self.dated, base=base)
            for mode, config, engine in (('undated', base, generate_pdf),
                                         ('dated', dated, generate_dated_pdf)):
                with self.subTest(mode=mode, language=language, typography=typography):
                    direct = io.BytesIO()
                    engine(config, direct)
                    artifact = self.service.generate_artifact(mode, config.to_dict())
                    self.assertEqual(artifact.pdf_bytes, direct.getvalue())
                    self.assertEqual(artifact.filename, config.pdf_filename)
                    self.assertEqual(pickle.loads(pickle.dumps(artifact)), artifact)
                    reader = PdfReader(io.BytesIO(artifact.pdf_bytes))
                    self.assertEqual(artifact.pages, len(reader.pages))
                    page_ids = {page.indirect_reference.idnum for page in reader.pages}
                    links = [ref.get_object() for page in reader.pages
                             for ref in page.get('/Annots', [])]
                    self.assertGreater(len(links), 20)
                    self.assertTrue(all(link['/Dest'][0].idnum in page_ids for link in links))

    def test_samples_match_engines_without_links_and_use_preview_filenames(self):
        for language in ('fr', 'en'):
            base = replace(self.base, language=language)
            dated = replace(self.dated, base=base)
            undated_name = 'aipaper-apercu.pdf' if language == 'fr' else 'aipaper-preview-en.pdf'
            for mode, config, engine, count, filename in (
                ('undated', base, generate_samples, 4, undated_name),
                ('dated', dated, generate_dated_samples, 6,
                 f'aipaper-dated-preview-{language}.pdf'),
            ):
                with self.subTest(mode=mode, language=language):
                    output = io.BytesIO()
                    engine(config, output)
                    artifact = self.service.generate_artifact(mode, config.to_dict(), samples=True)
                    self.assertEqual(artifact.pdf_bytes, output.getvalue())
                    self.assertEqual(artifact.filename, filename)
                    self.assertEqual(artifact.pages, count)
                    pages = PdfReader(io.BytesIO(artifact.pdf_bytes)).pages
                    self.assertEqual(len(pages), count)
                    self.assertTrue(all(not page.get('/Annots') for page in pages))

    def test_short_book_limits_days_without_changing_backlog_or_input(self):
        payload = self.base.to_dict()
        artifact = self.service.generate_artifact('undated', payload, short=True)
        output = io.BytesIO()
        generate_pdf(replace(self.base, days=3), output)
        self.assertEqual(artifact.pdf_bytes, output.getvalue())
        self.assertEqual(artifact.pages, 18)
        self.assertEqual(artifact.filename, 'aipaper-manrope-3j.pdf')
        self.assertEqual(payload['days'], 4)
        two_days = replace(self.base, days=2)
        artifact = self.service.generate_artifact('undated', two_days.to_dict(), short=True)
        self.assertEqual(artifact.pages, 16)

    def test_malformed_configuration_is_rejected_without_coercion(self):
        for mode, payload in (
            ('other', {}), (None, {}), ([], {}), ('undated', []),
            ('undated', {'days': True}), ('undated', {'days': '3'}),
            ('undated', {'days': 3.0}), ('undated', {'typo': 1}),
            ('undated', {1: 'value'}), ('undated', {'title': 'bad\nname'}),
            ('undated', {'list_names': 'Work'}),
            ('dated', {'base': None}), ('dated', {'base': {1: 'value'}}),
            ('dated', {'months': 0}), ('dated', {'week_pages': True}),
            ('dated', {'start_date': '2026-02-30'}),
        ):
            with self.subTest(mode=mode, payload=payload), self.assertRaises(ValueError):
                self.service.parse_config(mode, payload)

    def test_generation_flags_reject_ambiguous_requests(self):
        for mode, flags in (
            ('undated', {'samples': 'false'}), ('undated', {'short': 1}),
            ('undated', {'samples': True, 'short': True}), ('dated', {'short': True}),
        ):
            with self.subTest(mode=mode, flags=flags), self.assertRaises(ValueError):
                self.service.generate_artifact(mode, {}, **flags)

    @unittest.skipUnless(shutil.which('pdftoppm') and shutil.which('pdfinfo'),
                         'Poppler is required for rendering previews')
    def test_preview_renders_requested_page_as_bounded_png(self):
        from PIL import Image
        artifact = self.service.generate_artifact('undated', self.base.to_dict(), samples=True)
        png = self.service.render_preview(artifact.pdf_bytes, page=2)
        self.assertTrue(png.startswith(b'\x89PNG\r\n\x1a\n'))
        with Image.open(io.BytesIO(png)) as preview:
            self.assertLessEqual(max(preview.size), 1200)
            self.assertGreater(min(preview.size), 100)
        self.assertNotEqual(png, self.service.render_preview(artifact.pdf_bytes, page=1))
        for page in (0, -1, True, 1.5, '1', 5):
            with self.subTest(page=page), self.assertRaises(ValueError):
                self.service.render_preview(artifact.pdf_bytes, page=page)

    def test_preview_rejects_invalid_pdf_input(self):
        for payload in (None, '', b'', b'not a PDF'):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.service.render_preview(payload)


if __name__ == '__main__':
    unittest.main()
