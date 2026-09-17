import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader
from streamlit.testing.v1 import AppTest


ENTRYPOINT = Path(__file__).resolve().parents[1] / 'pdf_generator_ui.py'


class DatedPlannerUITests(unittest.TestCase):
    def open_dated(self):
        app = AppTest.from_file(str(ENTRYPOINT)).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.radio(key='workspace_mode').value, 'Viwoods AiPaper')
        self.assertIn('Viwoods daté', app.radio(key='workspace_mode').options)
        app.radio(key='workspace_mode').set_value('Viwoods daté').run(timeout=30)
        self.assertFalse(app.exception)
        return app

    def apply(self, app):
        next(b for b in app.button if b.label == 'Appliquer et actualiser l’aperçu').click().run(timeout=30)
        self.assertFalse(app.exception)

    def test_dated_generation_keeps_undated_configuration_independent(self):
        app = self.open_dated()
        undated = dict(app.session_state['planner_config'])
        app.date_input(key='dated_field_start').set_value(date(2026, 9, 16))
        app.selectbox(key='dated_field_months').set_value(1)
        app.selectbox(key='dated_field_language').set_value('en')
        app.number_input(key='dated_field_lists').set_value(1)
        app.number_input(key='dated_field_tasks').set_value(2)
        app.checkbox(key='dated_field_include_weekends').uncheck()
        self.apply(app)
        self.assertFalse(app.session_state['dated_config']['include_weekends'])
        self.assertEqual(app.session_state['dated_config']['start_date'], '2026-09-16')
        self.assertEqual(app.session_state['dated_config']['months'], 1)
        self.assertEqual(app.session_state['dated_config']['base']['language'], 'en')
        preview = PdfReader(io.BytesIO(app.session_state['dated_preview']['pdf']))
        self.assertEqual(len(preview.pages), 6)
        app.button(key='dated_generate').click().run(timeout=30)
        self.assertFalse(app.exception)
        output = app.session_state['dated_download']
        pdf = PdfReader(io.BytesIO(output['data']))
        self.assertIn('2026-09-16', output['name'])
        self.assertIn('dated', output['name'])
        self.assertEqual(len(pdf.pages), int(next(m.value for m in app.metric if m.label == 'Pages').replace(' ', '')))
        self.assertEqual(app.session_state['planner_config'], undated)
        app.selectbox(key='dated_field_months').set_value(2)
        self.apply(app)
        self.assertNotIn('dated_download', app.session_state)
        app.radio(key='workspace_mode').set_value('Viwoods AiPaper').run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key='planner_field_language').value, 'fr')

    def test_invalid_settings_preserve_last_valid_dated_config(self):
        app = self.open_dated()
        original = dict(app.session_state['dated_config'])
        app.text_input(key='dated_field_title').set_value('')
        self.apply(app)
        self.assertTrue(app.error)
        self.assertEqual(app.session_state['dated_config'], original)

    def test_missing_poppler_keeps_pdf_preview_available(self):
        from pdf2image.exceptions import PDFInfoNotInstalledError
        with patch('pdf2image.convert_from_bytes', side_effect=PDFInfoNotInstalledError('Poppler absent')):
            app = self.open_dated()
        self.assertFalse(app.exception)
        self.assertTrue(any('Poppler' in message.value for message in app.info))
        self.assertTrue(any(b.label == 'Télécharger les 6 pages d’aperçu' for b in app.get('download_button')))


class DatedPlannerCLITests(unittest.TestCase):
    def test_json_and_flags_generate_separate_pdf_and_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'config.json'
            config.write_text(json.dumps({
                'start_date': '2026-09-16', 'months': 3,
                'base': {'list_count': 1, 'tasks_per_list': 2, 'detail_pages': 1, 'notes_pages': 0},
            }))
            output = root / 'pdf'
            command = [sys.executable, str(ENTRYPOINT.parent / 'generate_dated_planner.py'),
                       '--config', str(config), '--months', '1', '--language', 'en',
                       '--week-pages', '2', '--weekly-tasks', '12', '--no-include-weekends', '--output-dir', str(output)]
            run = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertEqual(result['config']['months'], 1)
            self.assertEqual(result['config']['week_pages'], 2)
            self.assertEqual(result['config']['weekly_tasks'], 12)
            self.assertFalse(result['config']['include_weekends'])
            self.assertEqual(result['config']['base']['language'], 'en')
            pdf = Path(result['file'])
            self.assertEqual(pdf.parent, output)
            self.assertIn('dated', pdf.name)
            self.assertEqual(len(PdfReader(pdf).pages), result['pages'])
            self.assertEqual(json.loads(pdf.with_suffix('.report.json').read_text()), result)

    def test_device_and_comfort_flags_change_the_surface_and_the_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            command = [sys.executable, str(ENTRYPOINT.parent / 'generate_dated_planner.py'),
                       '--start-date', '2026-09-16', '--months', '1',
                       '--device', 'boox-note-max', '--density', 'comfortable',
                       '--output-dir', directory]
            run = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            result = json.loads(run.stdout)
            self.assertEqual(result['config']['base']['device'], 'boox-note-max')
            self.assertEqual(result['config']['base']['density'], 'comfortable')
            self.assertIn('boox-note-max-aere', result['file'])
            page = PdfReader(result['file']).pages[0]
            self.assertAlmostEqual(float(page.mediabox.width), 2400 * 72 / 300, places=3)

    def test_unknown_device_does_not_generate_a_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            run = subprocess.run([sys.executable, str(ENTRYPOINT.parent / 'generate_dated_planner.py'),
                                  '--device', 'custom', '--output-dir', directory],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(list(Path(directory).glob('*.pdf')), [])

    def test_invalid_date_does_not_generate_a_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            run = subprocess.run([sys.executable, str(ENTRYPOINT.parent / 'generate_dated_planner.py'),
                                  '--start-date', '2026-02-30', '--output-dir', directory],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertIn('error:', run.stderr)
            self.assertEqual(list(Path(directory).glob('*.pdf')), [])


if __name__ == '__main__':
    unittest.main()
