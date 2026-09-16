# Viwoods daily planner implementation plan

**Goal:** Restore Meetings as an undated daily dashboard connected to a permanent task bank; deliver usable PDFs for the AiPaper and typography comparisons.

**Architecture:** Keep ReportLab and the historical generator. Add a self-contained planner with validated configuration, reusable drawing templates and ordinary internal PDF destinations. Expose it in the existing Streamlit entry point as a separate mode. No production deployment or changes to saved user configurations. Commit and push were explicitly authorized after the design iterations.

**Approved design:** Conversation of 16 September 2026: 10 lists, 40 tasks per list, 2 context pages per task, 200 undated Meetings, 2 continuation pages each. Objectives (5 priorities, updated after device trial), Agenda and Notes. Persistent numbered list tabs. Stable task references. All fonts embedded. No calendar, PDF JavaScript, or implied synchronization of handwritten notes.

**Device:** Viwoods AiPaper, 1920 × 2560 pixels at 300 PPI, portrait: 460.8 × 614.4 PDF points (162.56 × 216.7467 mm). Source: https://viwoods.com/products/viwoods-aipaper/.

## Constraints

- Preserve the old generator and all saved configurations; snapshot the UI before editing.
- Use local static TTF fonts with licenses: Manrope Regular/SemiBold, Manrope Medium/Bold, Atkinson Next Regular/SemiBold plus Mono for identifiers.
- A header reference written by hand does not become a dynamic PDF link.
- Shared task pages return to their task list and the day index, not a fictitious current day.
- Default book: 1 home + 5 day index pages + 600 dashboard/notes pages + 810 task list/context pages = 1416 pages.
- Task page backgrounds use shared Form XObjects, not raster images.

## Tasks

- [x] Add failing output-level tests in `tests/test_planner.py`: real PDF generation, dimensions, shared links, navigation destinations, link bounds, embedded fonts, invalid configuration.
- [x] Add `planner_config.py` for validated limits, device dimensions and typography choices; `planner_pdf.py` for page ordering and output; `planner_pages.py` for vector layouts and stable navigation.
- [x] Copy only required TTF files and licenses into `assets/fonts/` without altering the originals in Documents.
- [x] Add `planner_ui.py` and a mode selector in `pdf_generator_ui.py`. Include complete/short books, typography selection, counts, preview and JSON configuration import/export. Old mode remains available.
- [x] Add `generate_planner.py` CLI for repeatable PDF builds and `requirements-dev.txt` for PDF inspection tests.
- [x] Generate three full font variants and one short comparison PDF. Render home, day index, dashboard, continuation, list and task pages; inspect all template types visually.
- [x] Validate every link in the complete books, count pages, check file size, measure elapsed time and peak RSS. Run Streamlit smoke tests and an independent code review.
- [x] Document commands and navigation in `PLANNER.md`; deliver local file links. Commit and push the code when requested; no production deployment.

## Verification

Run `venv/bin/python -m unittest discover -s tests -v`. Reduced fixture: 2 lists × 4 tasks × 2 context pages, 3 days × 2 pages, 1 index and 1 home = 26 pages. Check that every dashboard links to the same list targets; task 02-04 opens its own context and returns to list 02. Validate the 40/41 day-index boundary with a 41-day fixture. Run the full PDF audit independently of the generator's page-count calculation.

Use `pdftoppm` at 150 DPI for layout inspection, and one dashboard at 300 DPI (1920 × 2560) for device-resolution inspection. Test the UI through Streamlit AppTest, including font changes, config validation, download invalidation, missing Poppler and historical mode; configuration serialization is covered by generator tests. Existing Python source other than the UI entry point remains byte-identical to its backup/archive baseline.

## Initial verification (before subsequent layout iterations)

13 automated tests passed. All 18,644 links in each full font variant checked; Manrope rechecked after the five-objective revision. All six page templates visually inspected, Meetings also rendered at device resolution. Independent review identified a missing-Poppler fallback issue, now fixed and regression-tested. Local browser inspection completed. Default book generation measured at about 2–2.5 seconds; isolated CLI run used 88,342,528 bytes maximum RSS (before the five-line layout adjustment). Manrope confirmed by the user on-device.

## Final device-trial layout

- Manrope retained; compact title and handwritten date/subject fields.
- Five Objectives, unruled Agenda, two continuation Notes pages.
- All pages have direct day-index shortcuts above the ten task-list tabs.
- Index ranges use two numbers separated by a small downward triangle.
- Day indexes read across rows; day numbers sit close to their underlines.
- Task lists have a handwritten source-day field instead of a checkbox.
- Header links return to the relevant list or the home overview.
- Daily footers contain separate previous/next-day controls that skip notes.
- Local UI previews/downloads are invalidated when the layout changes.

Before publication: fresh local dependency installation, full CLI generation,
three short font variants and the comparison, all automated tests and complete
PDF destination checks. The local-only archives and generated output are ignored
by Git. The GitHub main history is preserved; work is published on a feature branch.
