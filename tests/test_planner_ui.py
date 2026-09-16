import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


ENTRYPOINT = Path(__file__).resolve().parents[1] / "pdf_generator_ui.py"


class PlannerUITests(unittest.TestCase):
    def test_pdf_language_switch_generates_english_and_preserves_french_default(self):
        import io
        from pypdf import PdfReader

        app = AppTest.from_file(str(ENTRYPOINT)).run(timeout=20)
        self.assertTrue(any(s.key == "planner_field_language" for s in app.selectbox))
        self.assertEqual(app.selectbox(key="planner_field_language").value, "fr")
        app.selectbox(key="planner_field_language").set_value("en")
        app.number_input(key="planner_field_days").set_value(1)
        app.number_input(key="planner_field_lists").set_value(1)
        app.number_input(key="planner_field_tasks").set_value(1)
        self.apply(app)
        preview = PdfReader(io.BytesIO(app.session_state["planner_preview"]["pdf"]))
        self.assertIn("Date / period", preview.pages[0].extract_text())
        app.button(key="planner_generate").click().run(timeout=20)
        self.assertFalse(app.exception)
        result = app.session_state["planner_download"]
        self.assertEqual(result["name"], "aipaper-manrope-en-1d.pdf")
        self.assertIn("My lists", PdfReader(io.BytesIO(result["data"])).pages[0].extract_text())
        app.selectbox(key="planner_field_language").set_value("fr")
        self.apply(app)
        self.assertNotIn("planner_download", app.session_state)
        preview = PdfReader(io.BytesIO(app.session_state["planner_preview"]["pdf"]))
        self.assertIn("Date / période", preview.pages[0].extract_text())

    def apply(self, app):
        button = next(button for button in app.button if button.label == "Appliquer et actualiser l’aperçu")
        button.click().run(timeout=20)
        self.assertFalse(app.exception)

    def test_config_changes_generate_matching_pdf_and_invalidate_old_download(self):
        app = AppTest.from_file(str(ENTRYPOINT)).run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(app.radio(key="workspace_mode").value, "Viwoods AiPaper")
        app.number_input(key="planner_field_days").set_value(3)
        app.number_input(key="planner_field_lists").set_value(2)
        app.number_input(key="planner_field_tasks").set_value(4)
        app.selectbox(key="planner_field_typography").set_value("atkinson")
        self.apply(app)
        self.assertEqual(app.session_state["planner_config"]["typography"], "atkinson")
        self.assertEqual(next(m.value for m in app.metric if m.label == "Pages"), "29")
        app.button(key="planner_generate").click().run(timeout=20)
        self.assertFalse(app.exception)
        from pypdf import PdfReader
        import io
        result = app.session_state["planner_download"]
        self.assertEqual(len(PdfReader(io.BytesIO(result["data"])).pages), 29)
        app.number_input(key="planner_field_days").set_value(2)
        self.apply(app)
        self.assertNotIn("planner_download", app.session_state)

    def test_invalid_form_preserves_last_valid_configuration(self):
        app = AppTest.from_file(str(ENTRYPOINT)).run(timeout=20)
        app.text_input(key="planner_field_title").set_value("")
        self.apply(app)
        self.assertTrue(app.error)
        self.assertEqual(app.session_state["planner_config"]["title"], "Meetings & actions")

    def test_historical_mode_still_opens(self):
        app = AppTest.from_file(str(ENTRYPOINT)).run(timeout=20)
        app.radio(key="workspace_mode").set_value("Générateur historique").run(timeout=20)
        self.assertFalse(app.exception)
        self.assertEqual(app.title[0].value, "📄 A4 PDF Todo Generator")

    def test_missing_poppler_keeps_preview_download_available(self):
        from pdf2image.exceptions import PDFInfoNotInstalledError
        with patch("pdf2image.convert_from_bytes", side_effect=PDFInfoNotInstalledError("Poppler absent")):
            app = AppTest.from_file(str(ENTRYPOINT)).run(timeout=20)
        self.assertFalse(app.exception)
        self.assertTrue(any("Poppler" in message.value for message in app.info))
        downloads = app.get("download_button")
        self.assertTrue(any(button.label == "Télécharger ces 3 pages d’aperçu" for button in downloads))


if __name__ == "__main__":
    unittest.main()
