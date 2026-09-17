"""Ordered list of the pages a configuration produces.

The manifest is the single source of the page count and of every destination:
the interfaces and the PDF engines read the same list instead of recomputing
the structure of a notebook twice. It never reads `config.total_pages`, which
is itself derived from this module.
"""

from dataclasses import dataclass
from math import ceil
from typing import TYPE_CHECKING

from planner_layout import make_layout

if TYPE_CHECKING:  # Annotations only: importing the configurations would loop.
    from dated_planner_config import DatedPlannerConfig
    from planner_config import PlannerConfig


@dataclass(frozen=True)
class PageSpec:
    """One page: `part` is the part the reader asked for (Notes 2, weekly list
    2), `sheet` is the extra sheet pagination adds when a list does not fit."""

    key: str
    kind: str
    reference: str
    part: int = 1
    first_item: int = 0
    last_item: int = 0
    sheet: int = 1
    sheets: int = 1

    @property
    def holds_items(self):
        return self.last_item >= self.first_item > 0


def sheet_key(base: str, sheet: int) -> str:
    """The first sheet keeps the historical destination of its section."""
    return base if sheet == 1 else f"{base}-page-{sheet}"


def sheets(total: int, capacity: int, *, balance: bool = True) -> tuple[tuple[int, int], ...]:
    """Inclusive, one-based (first, last) item numbers of each sheet.

    Lists spread evenly — two half sheets read better than a full one followed
    by a stub. Day indexes keep uniform blocks, because their labels and the
    footer shortcut both rely on a constant number of days per page.
    """
    total, capacity = max(1, total), max(1, capacity)
    count = ceil(total / capacity)
    if balance:
        size, extra = divmod(total, count)
        sizes = [size + (1 if index < extra else 0) for index in range(count)]
    else:
        sizes = [min(capacity, total - index * capacity) for index in range(count)]
    spread, start = [], 0
    for size in sizes:
        spread.append((start + 1, start + size))
        start += size
    return tuple(spread)


def sheet_of(item: int, total: int, capacity: int) -> int:
    for number, (first, last) in enumerate(sheets(total, capacity), 1):
        if first <= item <= last:
            return number
    return 1


def list_key(number: int, item: int, total: int, capacity: int) -> str:
    """Destination of the sheet actually holding one backlog task line."""
    return sheet_key(f"list-{number}", sheet_of(item, total, capacity))


def _backlog(base: "PlannerConfig", layout) -> list[PageSpec]:
    per_page = layout.backlog_capacity
    spread = sheets(base.tasks_per_list, per_page)
    total = len(spread)
    pages = []
    for number in range(1, base.list_count + 1):
        for sheet, (first, last) in enumerate(spread, 1):
            pages.append(PageSpec(sheet_key(f"list-{number}", sheet), "task-list",
                                  str(number), 1, first, last, sheet, total))
        for item in range(1, base.tasks_per_list + 1):
            for part in range(1, base.detail_pages + 1):
                pages.append(PageSpec(f"task-{number}-{item}-{part}", "task-notes",
                                      f"{number}-{item}", part))
    return pages


def _projects(base: "PlannerConfig") -> list[PageSpec]:
    if not base.project_count:
        return []
    pages = [PageSpec("projects", "projects-index", "")]
    for number in range(1, base.project_count + 1):
        pages.append(PageSpec(f"project-{number}", "project", str(number)))
        for part in range(1, base.project_notes_pages + 1):
            pages.append(PageSpec(f"project-{number}-notes-{part}", "project-notes",
                                  str(number), part))
    return pages


def _days(count: int, notes_pages: int, meeting_layout: str = "classic") -> list[PageSpec]:
    pages = []
    for day in range(1, count + 1):
        pages.append(PageSpec(f"day-{day}", "meeting", str(day)))
        if meeting_layout == "both":
            pages.append(PageSpec(f"day-{day}-actions", "meeting-actions", str(day)))
        for part in range(1, notes_pages + 1):
            pages.append(PageSpec(f"day-{day}-notes-{part}", "meeting-notes",
                                  str(day), part))
    return pages


def undated_manifest(config: "PlannerConfig") -> tuple[PageSpec, ...]:
    layout = make_layout(config)
    pages = [PageSpec("home", "home", "")]
    for block, (first, last) in enumerate(
            sheets(config.days, layout.index_capacity, balance=False)):
        pages.append(PageSpec(f"days-{block}", "day-index", str(block),
                              1, first, last, block + 1, config.index_pages))
    pages += _days(config.days, config.notes_pages, config.meeting_layout)
    pages += _backlog(config, layout)
    pages += _projects(config)
    return tuple(pages)


def dated_manifest(schedule: "DatedPlannerConfig") -> tuple[PageSpec, ...]:
    base = schedule.render_config
    layout = make_layout(base)
    pages = [PageSpec("home", "home", "")]
    for month in schedule.calendar_months:
        pages.append(PageSpec(f"calendar-{month:%Y-%m}", "calendar", month.isoformat()))
        if getattr(schedule, "monthly_priorities", False):
            pages.append(PageSpec(f"month-plan-{month:%Y-%m}", "month-plan", month.isoformat()))
    week_sheets = sheets(schedule.weekly_tasks, layout.weekly_capacity)
    for monday in schedule.weeks:
        if getattr(schedule, "weekly_overview", False):
            pages.append(PageSpec(f"week-overview-{monday.isoformat()}", "week-overview",
                                  monday.isoformat()))
        for part in range(1, schedule.week_pages + 1):
            target = f"{schedule.week_key(monday)}-{part}"
            for sheet, (first, last) in enumerate(week_sheets, 1):
                pages.append(PageSpec(sheet_key(target, sheet), "weekly",
                                      monday.isoformat(), part, first, last,
                                      sheet, len(week_sheets)))
        if getattr(schedule, "weekly_review", False):
            pages.append(PageSpec(f"week-review-{monday.isoformat()}", "week-review",
                                  monday.isoformat()))
    pages += _days(len(schedule.dates), base.notes_pages, base.meeting_layout)
    pages += _backlog(base, layout)
    pages += _projects(base)
    return tuple(pages)


def build_manifest(config) -> tuple[PageSpec, ...]:
    if hasattr(config, "calendar_months"):
        return dated_manifest(config)
    return undated_manifest(config)


# One representative page per section, in the order a reader meets them.
PREVIEW_KINDS = {
    "undated": ("meeting", "meeting-actions", "task-list", "task-notes",
                "projects-index", "project", "project-notes"),
    "dated": ("calendar", "month-plan", "week-overview", "weekly", "week-review",
              "meeting", "meeting-actions", "task-list", "task-notes",
              "projects-index", "project", "project-notes"),
}


def preview_specs(manifest: tuple[PageSpec, ...], mode: str) -> tuple[PageSpec, ...]:
    """The pages a visual preview shows, skipping sections the notebook omits."""
    available = {}
    for spec in manifest:
        available.setdefault(spec.kind, spec)
    return tuple(available[kind] for kind in PREVIEW_KINDS[mode] if kind in available)


def preview_kinds(manifest: tuple[PageSpec, ...], mode: str) -> tuple[str, ...]:
    return tuple(spec.kind for spec in preview_specs(manifest, mode))


def first_of(manifest: tuple[PageSpec, ...], kind: str) -> PageSpec:
    """The representative page of a section, used by the visual previews."""
    for spec in manifest:
        if spec.kind == kind:
            return spec
    raise KeyError(f"Aucune page de type {kind} dans ce carnet.")
