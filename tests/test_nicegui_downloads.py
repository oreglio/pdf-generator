import inspect
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from nicegui import Client, app, ui

from nicegui_app import PlannerWorkspace
from nicegui_service import PDFArtifact


class PdfDownloadTests(unittest.IsolatedAsyncioTestCase):
    async def click_download(self, preview, window):
        artifact = PDFArtifact(b'%PDF-test-content', 'carnet.pdf', 5)
        client = Client(ui.page('/download-test'))
        state = PlannerWorkspace()
        state.client = client
        with patch.object(app.native, 'main_window', window), \
                patch('nicegui_app.ui.download') as browser_download, \
                patch('nicegui_app.ui.notify') as notify, \
                patch('nicegui_app.logging.exception'), \
                patch.dict('sys.modules', {'webview': SimpleNamespace(FileDialog=SimpleNamespace(SAVE=30))}):
            with client:
                if preview:
                    state.sample = artifact
                    state.preview_area()
                else:
                    state.output = artifact
                    state.download_area()
                button = next(element for element in client.elements.values()
                              if isinstance(element, ui.button) and element.text.startswith('Télécharger'))
                handler = next(iter(button._event_listeners.values())).handler
                callback = inspect.getclosurevars(handler).nonlocals.get('callback', handler)
                result = callback()
                if inspect.isawaitable(result):
                    await result
                self.assertFalse(state.busy)
                self.assertFalse(button.is_deleted)
                return browser_download, notify

    async def test_native_preview_and_full_pdf_save_without_browser_navigation(self):
        for preview in (True, False):
            with self.subTest(preview=preview), tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / 'mon carnet.pdf'
                window = SimpleNamespace(create_file_dialog=AsyncMock(return_value=(str(target),)))
                download, _ = await self.click_download(preview, window)
                window.create_file_dialog.assert_awaited_once()
                download.assert_not_called()
                self.assertEqual(target.read_bytes(), b'%PDF-test-content')

    async def test_cancel_native_dialog_keeps_application_and_does_not_download(self):
        window = SimpleNamespace(create_file_dialog=AsyncMock(return_value=None))
        download, _ = await self.click_download(True, window)
        window.create_file_dialog.assert_awaited_once()
        download.assert_not_called()

    async def test_native_write_error_is_reported_without_navigation(self):
        with tempfile.TemporaryDirectory() as directory:
            window = SimpleNamespace(create_file_dialog=AsyncMock(return_value=(directory,)))
            download, notify = await self.click_download(True, window)
            download.assert_not_called()
            self.assertTrue(any(call.kwargs.get('type') == 'negative' for call in notify.call_args_list))

    async def test_web_download_stays_standard(self):
        download, _ = await self.click_download(True, None)
        download.assert_called_once_with(b'%PDF-test-content', 'carnet.pdf', 'application/pdf')
