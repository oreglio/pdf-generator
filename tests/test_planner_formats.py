import io
import unittest
from dataclasses import replace

from pypdf import PdfReader

from planner_config import PlannerConfig
from planner_formats import (CATALOGUE, DEFAULT_DEVICE, DEVICES, MM,
                             DeviceFormat, devices_of, resolve_format)
from planner_layout import make_layout


class _Unknown:
    device = "boox-note-air3"
    custom_width_mm = None
    custom_height_mm = None


class FormatCatalogueTests(unittest.TestCase):
    def test_reference_profile_keeps_the_exact_historical_surface(self):
        layout = make_layout(PlannerConfig())
        self.assertEqual(layout.width, 1920 * 72 / 300)
        self.assertEqual(layout.height, 2560 * 72 / 300)
        self.assertEqual(layout.left, 24)
        self.assertEqual(layout.right, layout.width - 49)
        self.assertEqual(layout.content_width, layout.right - layout.left)
        self.assertEqual(layout.device.key, DEFAULT_DEVICE)
        self.assertEqual(PlannerConfig().pdf_filename, "aipaper-manrope-200j.pdf")

    def test_catalogue_is_portrait_documented_and_uniquely_keyed(self):
        self.assertEqual(len(DEVICES), len(CATALOGUE))
        for device in CATALOGUE:
            with self.subTest(device=device.key):
                self.assertIsInstance(device, DeviceFormat)
                self.assertGreater(device.width_pt, 0)
                self.assertLessEqual(device.width_pt, device.height_pt)
                self.assertTrue(device.source_url.startswith("https://"))
                self.assertTrue(device.label)
                self.assertLess(80, device.width_mm)
                self.assertLess(device.height_mm, 400)
        self.assertEqual({device.brand for device in CATALOGUE},
                         {"viwoods", "boox", "ipad"})
        self.assertEqual(len(devices_of("boox")), 3)

    def test_published_dimensions_match_the_official_specification_sheets(self):
        expected = {
            "viwoods-aipaper": (1920, 2560, 300),
            "viwoods-aipaper-mini": (1440, 1920, 292),
            "boox-go-103": (1860, 2480, 300),
            "boox-note-air4c": (1860, 2480, 300),
            "boox-note-max": (2400, 3200, 300),
            "ipad-pro-11-m4": (1668, 2420, 264),
            "ipad-pro-13-m4": (2064, 2752, 264),
        }
        self.assertEqual(set(expected), set(DEVICES))
        for key, (pixels_x, pixels_y, ppi) in expected.items():
            with self.subTest(device=key):
                device = DEVICES[key]
                self.assertAlmostEqual(device.width_pt, pixels_x * 72 / ppi, places=9)
                self.assertAlmostEqual(device.height_pt, pixels_y * 72 / ppi, places=9)

    def test_custom_format_accepts_only_documented_portrait_millimetres(self):
        config = replace(PlannerConfig(), device="custom",
                         custom_width_mm=150, custom_height_mm=210)
        layout = make_layout(config)
        self.assertAlmostEqual(layout.width, 150 * MM)
        self.assertAlmostEqual(layout.height, 210 * MM)
        self.assertEqual(layout.device.label, "150 × 210 mm")
        for changes in (
            {"device": "custom"},
            {"device": "custom", "custom_width_mm": 150},
            {"device": "custom", "custom_width_mm": 99, "custom_height_mm": 210},
            {"device": "custom", "custom_width_mm": 150, "custom_height_mm": 401},
            {"device": "custom", "custom_width_mm": 210, "custom_height_mm": 150},
            {"device": "custom", "custom_width_mm": True, "custom_height_mm": 210},
            {"device": "custom", "custom_width_mm": float("nan"), "custom_height_mm": 210},
            {"custom_width_mm": 150, "custom_height_mm": 210},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(PlannerConfig(), **changes)

    def test_unknown_device_or_comfort_is_refused_without_silent_fallback(self):
        for changes in ({"device": "boox-note-air3"}, {"device": ""}, {"device": None},
                        {"device": 1}, {"density": "aere"}, {"density": None}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(PlannerConfig(), **changes)
        with self.assertRaises(ValueError) as refusal:
            resolve_format(_Unknown())
        self.assertIn("Appareil inconnu", str(refusal.exception))
        self.assertIn("viwoods-aipaper", str(refusal.exception))

    def test_comfort_only_changes_row_spacing_not_the_surface(self):
        standard = make_layout(PlannerConfig())
        comfortable = make_layout(replace(PlannerConfig(), density="comfortable"))
        self.assertEqual((standard.width, standard.height),
                         (comfortable.width, comfortable.height))
        self.assertGreater(comfortable.row_height, standard.row_height)
        self.assertGreater(comfortable.task_row_height, standard.task_row_height)
        self.assertGreater(comfortable.weekly_row_height, standard.weekly_row_height)


class FormatRenderingTests(unittest.TestCase):
    def assertInside(self, page, box):
        width, height = box
        for ref in page.get("/Annots", []):
            x0, y0, x1, y1 = map(float, ref.get_object()["/Rect"])
            self.assertTrue(0 <= x0 < x1 <= width, f"{x0}–{x1} déborde de {width}")
            self.assertTrue(0 <= y0 < y1 <= height, f"{y0}–{y1} déborde de {height}")

    def small(self, **changes):
        return replace(PlannerConfig(days=2, list_count=1, tasks_per_list=1,
                                     detail_pages=1, notes_pages=1), **changes)

    def test_every_device_renders_at_its_own_size_without_distortion(self):
        from planner_pdf import generate_pdf
        for key, device in DEVICES.items():
            with self.subTest(device=key):
                output = io.BytesIO()
                generate_pdf(self.small(device=key), output)
                reader = PdfReader(output)
                ratio = device.width_pt / device.height_pt
                for page in reader.pages:
                    box = (float(page.mediabox.width), float(page.mediabox.height))
                    self.assertAlmostEqual(box[0], device.width_pt, places=3)
                    self.assertAlmostEqual(box[1], device.height_pt, places=3)
                    self.assertAlmostEqual(box[0] / box[1], ratio, places=5)
                    self.assertInside(page, box)

    def test_dated_notebook_follows_the_same_device_geometry(self):
        from dated_planner_config import DatedPlannerConfig
        from dated_planner_pdf import generate_dated_pdf
        for key in ("viwoods-aipaper-mini", "boox-note-max", "ipad-pro-11-m4"):
            with self.subTest(device=key):
                device = DEVICES[key]
                config = DatedPlannerConfig(base=self.small(device=key),
                                            start_date="2026-09-16", months=1)
                output = io.BytesIO()
                generate_dated_pdf(config, output)
                reader = PdfReader(output)
                self.assertEqual(len(reader.pages), config.total_pages)
                for page in reader.pages:
                    box = (float(page.mediabox.width), float(page.mediabox.height))
                    self.assertAlmostEqual(box[0], device.width_pt, places=3)
                    self.assertAlmostEqual(box[1], device.height_pt, places=3)
                    self.assertInside(page, box)

    def test_two_devices_never_share_mutated_geometry(self):
        from planner_pages import PlannerPages
        from reportlab.pdfgen import canvas
        mini = PlannerPages(canvas.Canvas(io.BytesIO()), self.small(device="viwoods-aipaper-mini"))
        maximum = PlannerPages(canvas.Canvas(io.BytesIO()), self.small(device="boox-note-max"))
        reference = PlannerPages(canvas.Canvas(io.BytesIO()), self.small())
        self.assertLess(mini.w, reference.w)
        self.assertGreater(maximum.w, reference.w)
        self.assertEqual(reference.w, 1920 * 72 / 300)
        self.assertEqual(mini.left, maximum.left)
        self.assertNotEqual(mini.width, maximum.width)


if __name__ == "__main__":
    unittest.main()
