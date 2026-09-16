import asyncio
import json
import os
import unittest
from contextlib import nullcontext
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from nicegui_app import PlannerWorkspace
from nicegui_service import PDFArtifact
from planner_config import PlannerConfig


def populate_fields(workspace):
    config = workspace.config
    base = config.base if workspace.mode == 'dated' else config
    values = base.to_dict()
    values['list_names'] = '\n'.join(base.list_names)
    if workspace.mode == 'dated':
        values.update({key: value for key, value in config.to_dict().items() if key != 'base'})
        values.pop('days')
    workspace.fields = {key: SimpleNamespace(value=value) for key, value in values.items()}


def workspace(mode='undated'):
    state = PlannerWorkspace()
    state.client = nullcontext()
    state.mode = mode
    state.configs['undated'] = PlannerConfig(days=4, list_count=1, tasks_per_list=1)
    for name in ('metrics', 'preview_area', 'download_area'):
        setattr(state, name, SimpleNamespace(refresh=lambda: None))
    async def refresh_body():
        await asyncio.sleep(0)
        populate_fields(state)

    state.body = SimpleNamespace(refresh=refresh_body)
    state.mode_control = SimpleNamespace(set_value=lambda value: None)
    populate_fields(state)
    return state


class WorkspaceTests(unittest.IsolatedAsyncioTestCase):
    def test_weekend_choice_is_applied_to_dated_generation(self):
        state = workspace('dated')
        state.fields['include_weekends'].value = False
        state.apply_draft()
        self.assertFalse(state.config.include_weekends)
        self.assertTrue(all(day.weekday() < 5 for day in state.config.dates))

    def test_client_drafts_images_and_documents_are_independent(self):
        first, second = workspace(), workspace()
        first.fields['title'].value = 'Private draft'
        first.apply_draft()
        first.images[0] = 'private image'
        first.output = PDFArtifact(b'private bytes', 'private.pdf', 1)
        first.mark_dirty()
        self.assertEqual(first.config.title, 'Private draft')
        self.assertEqual(second.config.title, 'Meetings & actions')
        self.assertFalse(second.dirty)
        self.assertIsNone(second.output)
        self.assertEqual(second.images, {})

    def test_changed_draft_invalidates_previous_pdf_and_previews(self):
        state = workspace()
        state.sample = PDFArtifact(b'old preview', 'sample.pdf', 3)
        state.output = PDFArtifact(b'old book', 'book.pdf', 10)
        state.images[0] = 'old image'
        state.fields['language'].value = 'en'
        state.mark_dirty()
        self.assertIsNone(state.output)
        self.assertTrue(state.dirty)
        state.apply_draft()
        self.assertEqual(state.config.language, 'en')
        self.assertIsNone(state.sample)
        self.assertEqual(state.images, {})
        self.assertFalse(state.dirty)

    def test_invalid_draft_preserves_last_valid_configuration(self):
        state = workspace()
        original = state.config
        state.fields['days'].value = 0
        state.mark_dirty()
        with self.assertRaises(ValueError):
            state.apply_draft()
        self.assertEqual(state.config, original)
        self.assertTrue(state.dirty)

    def test_ui_numbers_reject_boolean_and_nonfinite_values_as_validation_errors(self):
        for mode, field in (('undated', 'days'), ('dated', 'months')):
            for value in (True, float('inf'), float('nan'), 1.5, None):
                state = workspace(mode)
                state.fields[field].value = value
                with self.subTest(mode=mode, value=value), self.assertRaises(ValueError):
                    state.read_config()

    async def test_failed_generation_unlocks_controls_and_preserves_draft(self):
        state = workspace()
        state.fields['title'].value = 'Keep my settings'

        async def fail(*args, **kwargs):
            raise ValueError('Cannot generate this configuration')

        with patch('nicegui_app.cpu_job', fail):
            await state.generate()
        self.assertFalse(state.busy)
        self.assertEqual(state.activity, '')
        self.assertEqual(state.config.title, 'Keep my settings')
        self.assertIsNone(state.output)
        self.assertIn('Cannot generate', state.error)

    async def test_mode_switch_queued_during_generation_cannot_relabel_old_result(self):
        state = workspace()
        started, finish = asyncio.Event(), asyncio.Event()
        artifact = PDFArtifact(b'undated PDF', 'undated.pdf', 12)

        async def delayed_job(*args, **kwargs):
            started.set()
            await finish.wait()
            return artifact

        with patch('nicegui_app.cpu_job', delayed_job), patch('nicegui_app.ui.notify'):
            pending = asyncio.create_task(state.generate())
            await started.wait()
            try:
                await state.switch_mode(SimpleNamespace(value='dated'))
                self.assertEqual(state.mode, 'undated')
            finally:
                finish.set()
                await pending
        self.assertEqual(state.output, artifact)
        self.assertFalse(state.busy)

    async def test_import_locks_workspace_before_awaiting_uploaded_file(self):
        state = workspace()
        started, finish = asyncio.Event(), asyncio.Event()
        imported = replace(state.config, title='Imported configuration')

        async def delayed_read():
            started.set()
            await finish.wait()
            return json.dumps(imported.to_dict()).encode()

        async def preview():
            self.assertFalse(state.busy)
            self.assertEqual(state.read_config(), imported)

        state.refresh_preview = preview
        with patch('nicegui_app.ui.notify'):
            pending = asyncio.create_task(state.import_config(
                SimpleNamespace(file=SimpleNamespace(read=delayed_read))))
            await started.wait()
            try:
                self.assertTrue(state.busy)
            finally:
                finish.set()
                await pending
        self.assertFalse(state.busy)
        self.assertEqual(state.config, imported)
        self.assertEqual(state.fields['title'].value, 'Imported configuration')

    async def test_invalid_import_unlocks_and_keeps_existing_config_and_pdf(self):
        state = workspace()
        original = state.config
        artifact = PDFArtifact(b'valid PDF', 'book.pdf', 12)
        state.output = artifact
        rendered_busy = []
        state.download_area = SimpleNamespace(refresh=lambda: rendered_busy.append(state.busy))

        async def read():
            return b'{"days": false}'

        await state.import_config(SimpleNamespace(file=SimpleNamespace(read=read)))
        self.assertFalse(state.busy)
        self.assertEqual(state.config, original)
        self.assertEqual(state.output, artifact)
        self.assertIn('Configuration invalide', state.error)
        self.assertTrue(rendered_busy)
        self.assertFalse(rendered_busy[-1], 'The error display must not retain a loading indicator')

    async def test_import_switches_mode_and_clears_prior_artifacts(self):
        state = workspace()
        undated = state.config
        imported = replace(state.configs['dated'], start_date='2026-12-28', week_pages=3)
        state.sample = PDFArtifact(b'old sample', 'sample.pdf', 3)
        state.output = PDFArtifact(b'old book', 'book.pdf', 12)
        state.images[0] = 'old image'
        state.kind = 2

        async def read():
            return json.dumps(imported.to_dict()).encode()

        async def preview():
            self.assertEqual(state.mode, 'dated')
            self.assertFalse(state.busy)
            self.assertEqual(state.read_config(), imported)

        state.refresh_preview = preview
        with patch('nicegui_app.ui.notify'):
            await state.import_config(SimpleNamespace(file=SimpleNamespace(read=read)))
        self.assertEqual(state.config, imported)
        self.assertEqual(state.configs['undated'], undated)
        self.assertEqual(state.fields['week_pages'].value, 3)
        self.assertEqual(state.kind, 0)
        self.assertIsNone(state.output)
        self.assertIsNone(state.sample)
        self.assertEqual(state.images, {})

    def test_export_downloads_current_draft_without_clearing_preview(self):
        state = workspace()
        state.sample = PDFArtifact(b'preview', 'sample.pdf', 3)
        state.images[0] = 'current image'
        state.fields['title'].value = 'Current draft'
        state.mark_dirty()
        downloads = []
        with patch('nicegui_app.ui.download', lambda data, name, mime: downloads.append((data, name, mime))):
            state.export_config()
        self.assertEqual(len(downloads), 1)
        data, name, mime = downloads[0]
        self.assertEqual(json.loads(data)['title'], 'Current draft')
        self.assertEqual(name, 'aipaper-config.json')
        self.assertEqual(mime, 'application/json')
        self.assertIsNotNone(state.sample)
        self.assertEqual(state.images[0], 'current image')
        self.assertTrue(state.dirty)

    async def test_late_generation_result_does_not_restore_download_after_edit(self):
        state = workspace()
        started, finish = asyncio.Event(), asyncio.Event()

        async def delayed_job(*args, **kwargs):
            started.set()
            await finish.wait()
            return PDFArtifact(b'outdated PDF', 'old.pdf', 12)

        with patch('nicegui_app.cpu_job', delayed_job), patch('nicegui_app.ui.notify'):
            pending = asyncio.create_task(state.generate())
            await started.wait()
            state.fields['title'].value = 'A newer edit'
            state.mark_dirty()
            finish.set()
            await pending
        self.assertTrue(state.dirty)
        self.assertIsNone(state.output)

    async def test_short_option_invalidates_only_full_download(self):
        state = workspace()
        state.sample = PDFArtifact(b'sample', 'preview.pdf', 3)
        state.output = PDFArtifact(b'full book', 'book.pdf', 18)
        state.images[0] = 'current preview'
        state.short_changed(SimpleNamespace(value=True))
        self.assertTrue(state.short)
        self.assertIsNone(state.output)
        self.assertIsNotNone(state.sample)
        self.assertEqual(state.images[0], 'current preview')


class NiceGUIRefreshIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_widgets_finish_import_refresh_before_preview_reads_fields(self):
        from nicegui import core, ui
        from nicegui.client import Client
        from nicegui_service import generate_artifact, render_preview

        for initial_mode, imported_mode in (('undated', 'undated'), ('dated', 'undated'),
                                            ('undated', 'dated')):
            with self.subTest(initial_mode=initial_mode, imported_mode=imported_mode):
                with patch.object(core, 'loop', asyncio.get_running_loop()):
                    client = Client(ui.page('/test-import-refresh'))
                    try:
                        with client:
                            state = PlannerWorkspace()
                            state.client = client
                            state.mode = initial_mode
                            state.mode_control = ui.toggle(
                                {'dated': 'Dated', 'undated': 'Undated'}, value=initial_mode,
                                on_change=state.switch_mode,
                            )
                            state.body()
                            old_title_widget = state.fields['title']
                            upload = next(element for element in client.elements.values()
                                          if isinstance(element, ui.upload))
                            base = PlannerConfig(days=2, list_count=1, tasks_per_list=1,
                                                 language='en', title='Imported settings')
                            imported = (base if imported_mode == 'undated' else
                                        replace(state.configs['dated'], base=base,
                                                start_date='2026-12-28', months=1, week_pages=3))

                            async def read():
                                await asyncio.sleep(0)
                                return json.dumps(imported.to_dict()).encode()

                            async def job(function, *args, **kwargs):
                                if function is render_preview:
                                    return b'preview image'
                                return await asyncio.to_thread(function, *args, **kwargs)

                            with patch('nicegui_app.cpu_job', job):
                                with upload.parent_slot:
                                    await state.import_config(
                                        SimpleNamespace(file=SimpleNamespace(read=read)))
                            self.assertEqual(state.error, '')
                            self.assertEqual(state.mode, imported_mode)
                            self.assertEqual(state.config, imported)
                            self.assertEqual(state.read_config(), imported)
                            self.assertIsNot(state.fields['title'], old_title_widget)
                            self.assertEqual(state.fields['title'].value, 'Imported settings')
                            expected = await asyncio.to_thread(
                                generate_artifact, imported_mode, imported.to_dict(), samples=True)
                            self.assertEqual(state.sample, expected)
                            self.assertFalse(state.busy)
                            await asyncio.sleep(0)
                    finally:
                        client.delete()


class CPUJobTests(unittest.IsolatedAsyncioTestCase):
    async def test_worker_uses_separate_process_and_propagates_errors(self):
        from nicegui_jobs import cpu_job, shutdown_jobs
        self.addCleanup(shutdown_jobs)
        pid = await cpu_job(os.getpid)
        self.assertNotEqual(pid, os.getpid())
        self.assertEqual(await cpu_job(round, 1.234, ndigits=2), 1.23)
        with self.assertRaises(ValueError):
            await cpu_job(int, 'not an integer')


if __name__ == '__main__':
    unittest.main()
