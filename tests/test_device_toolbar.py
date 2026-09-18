"""The built-in toolbar of a tablet floats above the page; its band stays free."""

import io
import unittest
from dataclasses import replace

from pypdf import PdfReader

from dated_planner_config import DatedPlannerConfig
from planner_config import PlannerConfig
from planner_formats import MM
from planner_layout import DEFAULT_TOOLBAR_MM, make_layout


def small(**changes):
    return replace(PlannerConfig(days=2, list_count=1, tasks_per_list=1,
                                 detail_pages=1, notes_pages=1, project_count=1),
                   **changes)


class GeometryTests(unittest.TestCase):
    def test_a_notebook_without_a_toolbar_keeps_the_historical_geometry(self):
        plain, layout = make_layout(PlannerConfig()), make_layout(PlannerConfig(toolbar="none"))
        self.assertEqual((layout.left, layout.right), (plain.left, plain.right))
        self.assertEqual(layout.toolbar_width, 0)
        self.assertEqual(layout.page_right, layout.width)
        self.assertEqual(PlannerConfig(toolbar_mm=25.0).layout.left, 24)

    def test_a_toolbar_on_the_left_moves_the_writing_column_off_it(self):
        layout = make_layout(PlannerConfig(toolbar="left", toolbar_mm=12))
        self.assertAlmostEqual(layout.left, 24 + 12 * MM)
        self.assertEqual(layout.right, make_layout(PlannerConfig()).right)
        self.assertEqual(layout.page_right, layout.width)  # The rail keeps its edge.

    def test_a_toolbar_on_the_right_pulls_the_navigation_rail_inwards(self):
        layout = make_layout(PlannerConfig(toolbar="right", toolbar_mm=12))
        self.assertEqual(layout.left, 24)
        self.assertAlmostEqual(layout.page_right, layout.width - 12 * MM)
        self.assertAlmostEqual(layout.right, layout.width - 12 * MM - 49)

    def test_the_sheet_itself_never_shrinks(self):
        """The toolbar floats over the page: cropping it would shrink the writing."""
        for side in ("none", "left", "right"):
            with self.subTest(side=side):
                layout = make_layout(PlannerConfig(toolbar=side, toolbar_mm=20))
                self.assertEqual(layout.pagesize, make_layout(PlannerConfig()).pagesize)

    def test_an_unusable_band_is_refused_instead_of_silently_overlapping(self):
        for values in ({"toolbar": "sideways"}, {"toolbar": "left", "toolbar_mm": 3},
                       {"toolbar": "left", "toolbar_mm": 31},
                       {"toolbar": "left", "toolbar_mm": True},
                       {"toolbar": "left", "toolbar_mm": "12"}):
            with self.subTest(**values), self.assertRaises(ValueError):
                PlannerConfig(**values)
        with self.assertRaises(ValueError):  # 100 mm wide, two 30 mm bands is absurd.
            PlannerConfig(device="custom", custom_width_mm=100.0, custom_height_mm=200.0,
                          toolbar="left", toolbar_mm=30.0)

    def test_each_variant_earns_its_own_file_name(self):
        self.assertEqual(PlannerConfig().pdf_filename, "aipaper-manrope-200j.pdf")
        self.assertEqual(PlannerConfig(toolbar_mm=20.0).pdf_filename,
                         "aipaper-manrope-200j.pdf")
        self.assertTrue(PlannerConfig(toolbar="left").pdf_filename.endswith("-barre-g.pdf"))
        self.assertTrue(PlannerConfig(toolbar="right").pdf_filename.endswith("-barre-d.pdf"))
        self.assertIn("-aere-barre-d",
                      PlannerConfig(toolbar="right", density="comfortable").pdf_filename)

    def test_an_export_saved_before_the_option_existed_still_opens(self):
        stored = {key: value for key, value in PlannerConfig().to_dict().items()
                  if key not in ("toolbar", "toolbar_mm")}
        restored = PlannerConfig.from_dict(stored)
        self.assertEqual(restored.toolbar, "none")
        self.assertEqual(restored.toolbar_mm, DEFAULT_TOOLBAR_MM)


class RenderingTests(unittest.TestCase):
    def assertClear(self, reader, band, side):
        """Nothing tappable may hide under the toolbar, on any page."""
        for number, page in enumerate(reader.pages, start=1):
            width = float(page.mediabox.width)
            for ref in page.get("/Annots", []):
                x0, _, x1, _ = map(float, ref.get_object()["/Rect"])
                with self.subTest(page=number):
                    if side == "left":
                        self.assertGreaterEqual(round(x0, 3), band)
                    else:
                        self.assertLessEqual(round(x1, 3), round(width - band, 3))

    def test_no_link_lands_under_the_toolbar_on_either_side(self):
        from planner_pdf import generate_pdf
        for side in ("left", "right"):
            with self.subTest(side=side):
                output = io.BytesIO()
                generate_pdf(small(toolbar=side, toolbar_mm=14), output)
                self.assertClear(PdfReader(output), 14 * MM, side)

    def test_a_dated_notebook_reserves_the_same_band(self):
        from dated_planner_pdf import generate_dated_pdf
        config = DatedPlannerConfig(base=small(toolbar="right", toolbar_mm=14),
                                    start_date="2026-09-16", months=1,
                                    weekly_overview=True, weekly_review=True,
                                    monthly_priorities=True)
        output = io.BytesIO()
        generate_dated_pdf(config, output)
        self.assertClear(PdfReader(output), 14 * MM, "right")


if __name__ == "__main__":
    unittest.main()
