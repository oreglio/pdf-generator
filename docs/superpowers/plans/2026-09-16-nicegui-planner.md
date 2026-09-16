# NiceGUI POC

Goal: provide local browser, desktop window and VPS web interfaces while preserving existing PDF generation and Streamlit.

Architecture: isolated NiceGUI entry point; per-client configuration and artifacts; existing Python PDF engines; background generation; optional desktop dependency; dedicated Docker image.

Tech stack: NiceGUI, ReportLab, pdf2image/Poppler, pywebview (desktop only).

Spec: expose every dated and undated configuration field, JSON import/export, sample previews/downloads, complete generation/downloads and undated three-day testing. Keep FR/EN, typography, custom list names and internal links identical. Scope confirmed by user: only the two Viwoods planners; historical Streamlit remains separate. Published PDF examples stay unchanged. Follow-up: optional weekday-only Meeting/Notes generation in the dated engine, enabled through both UIs, JSON and CLI; default PDF bytes stay identical.

- [x] Implement isolated PDF service and parity tests.
- [x] Build responsive NiceGUI configuration/preview workspace.
- [x] Keep the NiceGUI scope limited to dated and undated Viwoods planners.
- [x] Add local/desktop/web launch and VPS packaging/documentation.
- [x] Verify existing tests, PDF identity, browser workflows and deployment configuration.

Validation: byte comparison against direct engine calls, malformed import handling, client isolation, real generation/download and preview interaction. Report separately anything that cannot be exercised (such as remote VPS deployment).

Results: Regression suite covers engines, UI state and native PDF saving. Browser-generated dated default matches the published 1,102-page PDF byte for byte. Imported English/Atkinson configuration generates the same PDF as its engine call; invalid imports preserve existing output. JSON import/export work. Responsive layout checked at 390px with no horizontal overflow; no external web resources loaded. Docker builds and renders both modes with Poppler as a nonroot user. macOS window and native Save dialog observed; final native Save acceptance remains unverified. No VPS deployment performed.
