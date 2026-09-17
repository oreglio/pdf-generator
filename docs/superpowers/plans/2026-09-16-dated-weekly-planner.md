# Dated weekly planner implementation plan

**Goal:** Add an independent French/English dated planner with clickable calendars,
weekly action lists and a permanent backlog, preserving undated PDFs byte for byte.

**Approved design:** User approved the Meeting → weekly tasks → permanent backlog
workflow and calendar. Weekly actions have no detail pages. Backlog notes remain
permanent; handwritten references do not become links. Every backlog page exposes
the weeks of the document for a deliberate one-tap return.

**Architecture:** Separate configuration, page renderer, assembler/CLI and Streamlit
UI. Reuse drawing primitives and backlog layouts from PlannerPages by subclassing;
do not edit the undated configuration, renderer, assembler, CLI or UI. Add one mode
to the application entrypoint. No new runtime dependency.

**Tech stack:** Python dataclasses/datetime/calendar, ReportLab, Streamlit, pypdf tests.

## Constraints

- Start from main on feat/dated-weekly-planner; keep current Manrope/AiPaper format.
- Date interval: start included through the day before start + N calendar months;
  clamp the exclusive end to the last valid day when necessary. N is 1–3.
- Include all weekdays; partial weeks/months have no links outside the interval.
- ISO weeks start Monday; week destinations contain the Monday date, not just Wxx.
- Keep ISO year visible in week headers across New Year.
- Default: 3 months, 1 weekly task page, 40 actions/page, 2 Meeting notes pages.
- Allow 1–3 weekly pages and 1–40 actions/page; retain existing backlog settings.
- Separate dated filenames, JSON, preview/download state and CLI reports.
- Published undated example SHA-256 hashes must remain unchanged.

## Tasks and interfaces

- [x] Add `dated_planner_config.py` and `tests/test_dated_config.py`.
  Frozen DatedPlannerConfig fields: base: PlannerConfig, start_date: ISO string,
  months: int, week_pages: int, weekly_tasks: int. Properties: start/end_date
  (date, inclusive end), dates (tuple), weeks (tuple of Monday dates),
  calendar_months (tuple of month-start dates), render_config (base with actual
  day count), total_pages, pdf_filename. Methods: day_number(date), week_for_day
  (1-based int), week_key(Monday), to_dict/from_dict. Test leap years, month ends,
  ISO years, serialization, invalid types/ranges and 1/3-month page counts.
- [x] Add `dated_planner_pages.py` and `dated_planner_pdf.py`.
  DatedPlannerPages inherits primitives/backlog from PlannerPages. Own home,
  calendar(month index), weekly(Monday, part), meeting(day), meeting_notes(day,
  part), rail and footer. `generate_dated_pdf(config,target)` returns page count;
  `generate_dated_samples(config,target)` emits five visual-only pages: calendar,
  weekly tasks, Meeting, backlog list, backlog context. Test destinations and
  hit rectangles for all page types and partial-week/year boundaries before
  implementing. Preserve shared forms and vector drawing.
- [x] Add `dated_planner_ui.py`, `generate_dated_planner.py` and UI tests.
  Render function `render_dated_planner_ui()` with independent dated_* session
  state, JSON import/export, date/months/weekly settings and existing backlog
  controls. CLI accepts --start-date, --months, --week-pages, --weekly-tasks,
  --language, --font, --config and --output-dir; default output/pdf/dated.
  Add `Viwoods daté` mode in pdf_generator_ui.py without changing default.
- [x] Verify all navigation graphs, new-year dates and both languages; render
  calendar, week, Meeting, notes and backlog for visual inspection. Regenerate
  both undated full PDFs and compare their bytes with examples/. Run full suite.
- [x] Generate separate dated French/English examples starting 2026-09-16 for
  3 months, document the workflow and commands, commit/push on the feature branch
  using oreglio as author/committer without modifying global Git configuration.

## Verification results

34 unittest tests pass. Both full dated editions have 1,102 pages and 33,807
valid, bounded links. Rendered calendars, weekly tasks, Meetings, Meeting notes,
backlog and context pages were visually inspected in French and English.
The Streamlit dated workspace was inspected in the local browser. Both published
undated PDFs regenerate byte for byte; their code and examples are unchanged.
