import json
import unittest
from datetime import date, datetime, timedelta

from dated_planner_config import DatedPlannerConfig
from planner_config import PlannerConfig


class DatedConfigTests(unittest.TestCase):
    def test_weekdays_keep_calendar_and_weeks_but_remove_only_daily_pages(self):
        from dataclasses import replace
        original = DatedPlannerConfig(start_date="2026-09-16")
        config = replace(original, include_weekends=False)
        self.assertEqual(len(config.dates), 65)
        self.assertEqual(config.calendar_months, original.calendar_months)
        self.assertEqual(config.weeks, original.weeks)
        self.assertEqual(original.total_pages - config.total_pages, 26 * 3)
        self.assertEqual(config.day_number(date(2026, 9, 21)), 4)
        self.assertEqual(config.week_for_day(4), date(2026, 9, 21))
        with self.assertRaises(ValueError):
            config.day_number(date(2026, 9, 19))
        self.assertEqual(DatedPlannerConfig.from_dict(config.to_dict()), config)
        self.assertTrue(DatedPlannerConfig.from_dict({}).include_weekends)
        for value in (0, 1, "false", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                replace(config, include_weekends=value)
        weekend_start = replace(config, start_date="2026-09-19", months=1)
        self.assertEqual(weekend_start.dates[0], date(2026, 9, 21))
        self.assertEqual(weekend_start.dates[-1], date(2026, 10, 16))
        self.assertNotEqual(config.pdf_filename, original.pdf_filename)

    def test_calendar_month_interval_includes_start_and_excludes_anniversary(self):
        config = DatedPlannerConfig(start_date="2026-09-16", months=3)
        self.assertEqual(config.start, date(2026, 9, 16))
        self.assertEqual(config.end_date, date(2026, 12, 15))
        self.assertEqual(len(config.dates), 91)
        self.assertEqual(config.dates[0], config.start)
        self.assertEqual(config.dates[-1], config.end_date)
        self.assertEqual(config.calendar_months, (
            date(2026, 9, 1), date(2026, 10, 1),
            date(2026, 11, 1), date(2026, 12, 1),
        ))
        self.assertEqual(len(config.weeks), 14)
        self.assertEqual(config.weeks[0], date(2026, 9, 14))
        self.assertEqual(config.weeks[-1], date(2026, 12, 14))

    def test_month_end_clamp_and_leap_year(self):
        for start, end, length in (
            ("2024-01-31", date(2024, 2, 28), 29),
            ("2025-01-31", date(2025, 2, 27), 28),
            ("2024-02-01", date(2024, 2, 29), 29),
            ("2024-02-29", date(2024, 3, 28), 29),
            ("2026-12-16", date(2027, 1, 15), 31),
        ):
            with self.subTest(start=start):
                config = DatedPlannerConfig(start_date=start, months=1)
                self.assertEqual(config.end_date, end)
                self.assertEqual(len(config.dates), length)
                self.assertEqual(config.total_pages,
                                 1 + len(config.calendar_months) + len(config.weeks)
                                 + length * 3 + 810)

    def test_day_and_week_lookup_across_iso_year(self):
        config = DatedPlannerConfig(start_date="2026-12-30", months=1)
        self.assertEqual(config.day_number(date(2027, 1, 1)), 3)
        self.assertEqual(config.week_for_day(3), date(2026, 12, 28))
        self.assertEqual(config.week_for_day(6), date(2027, 1, 4))
        self.assertEqual(config.week_key(config.weeks[0]), "week-2026-12-28")
        self.assertEqual(config.week_key(config.weeks[1]), "week-2027-01-04")
        self.assertEqual(config.weeks[0].isocalendar()[:2], (2026, 53))
        self.assertEqual(config.weeks[1].isocalendar()[:2], (2027, 1))
        for value in (config.start - timedelta(days=1), config.end_date + timedelta(days=1),
                      "2026-12-30", datetime(2026, 12, 30)):
            with self.subTest(date=value), self.assertRaises(ValueError):
                config.day_number(value)
        for value in (0, len(config.dates) + 1, True, 1.5, "1"):
            with self.subTest(day=value), self.assertRaises(ValueError):
                config.week_for_day(value)
        with self.assertRaises(ValueError):
            config.week_key(date(2026, 12, 30))

    def test_composition_preserves_undated_config_and_counts_all_sections(self):
        base = PlannerConfig(list_count=2, tasks_per_list=4, detail_pages=3,
                             notes_pages=1, days=200, language="en")
        config = DatedPlannerConfig(base=base, start_date="2026-09-16",
                                    months=3, week_pages=2, weekly_tasks=12)
        self.assertEqual(base.days, 200)
        self.assertEqual(config.render_config.days, 91)
        self.assertEqual(config.render_config.list_count, 2)
        self.assertEqual(config.total_pages, 1 + 4 + 28 + 182 + 2 + 24)
        self.assertEqual(config.pdf_filename,
                         "dated-aipaper-manrope-en-2026-09-16-2026-12-15.pdf")
        self.assertNotEqual(config.pdf_filename, base.pdf_filename)

    def test_json_round_trip_and_defaults(self):
        config = DatedPlannerConfig(base=PlannerConfig(list_names=("Projets",)),
                                    start_date="2026-09-16", week_pages=3)
        values = json.loads(json.dumps(config.to_dict()))
        self.assertEqual(DatedPlannerConfig.from_dict(values), config)
        self.assertEqual(values["base"]["list_names"], ["Projets"])
        defaults = DatedPlannerConfig.from_dict({})
        self.assertEqual(defaults.start, date.today())
        self.assertEqual(defaults.months, 3)
        self.assertEqual(defaults.week_pages, 1)
        self.assertEqual(defaults.weekly_tasks, 40)

    def test_invalid_configuration_is_rejected(self):
        invalid = (
            {"base": {}}, {"base": None}, {"start_date": date(2026, 9, 16)},
            {"start_date": "20260916"}, {"start_date": "2026-02-30"},
            {"start_date": "9999-12-01"}, {"start_date": None},
            {"months": 0}, {"months": 4}, {"months": True}, {"months": 1.0},
            {"week_pages": 0}, {"week_pages": 4}, {"week_pages": False},
            {"weekly_tasks": 0}, {"weekly_tasks": 41}, {"weekly_tasks": "40"},
        )
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                DatedPlannerConfig(**values)
        for values in ([], {"unknown": 1}, {"base": {"days": 0}}, {"base": None}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                DatedPlannerConfig.from_dict(values)


if __name__ == "__main__":
    unittest.main()
