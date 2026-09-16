"""Dated navigation and layouts, isolated from the reproducible undated edition."""

import calendar
from datetime import timedelta
from math import ceil

from planner_config import PAGE_HEIGHT as H, PAGE_WIDTH as W
from planner_pages import PlannerPages, LEFT, RIGHT, WIDTH, MUTED


MONTHS = {
    "fr": ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
           "septembre", "octobre", "novembre", "décembre"),
    "en": ("January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"),
}
WEEKDAYS = {"fr": ("Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"),
            "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")}


class DatedPlannerPages(PlannerPages):
    def __init__(self, canvas, schedule, *, interactive=True):
        self.schedule = schedule
        self.current_date = None
        self.active_week = None
        super().__init__(canvas, schedule.render_config, interactive=interactive)

    def label(self, french, english):
        return french if self.config.language == "fr" else english

    def month_name(self, value):
        return MONTHS[self.config.language][value.month - 1]

    def full_date(self, value):
        return f"{WEEKDAYS[self.config.language][value.weekday()]} {value.day} {self.month_name(value)} {value.year}"

    @staticmethod
    def month_key(value):
        return f"calendar-{value:%Y-%m}"

    def day_key(self, value):
        return f"day-{self.schedule.day_number(value)}"

    @staticmethod
    def week_label(monday):
        return f"W{monday.isocalendar().week:02d}"

    def week_target(self, monday, part=1):
        return f"{self.schedule.week_key(monday)}-{part}"

    def rail(self, active=None):
        self.line(W - 39, 69, W - 39, H - 31, gray=0.85)
        self.text(W - 19, H - 39, self.label("SEMAINES", "WEEKS"), 5.5, bold=True, align="center")
        step = min(26, 270 / len(self.schedule.weeks))
        for index, monday in enumerate(self.schedule.weeks):
            self.pill(W - 32, H - 50 - (index + 1) * step, 26, step - 3,
                      self.week_label(monday), self.week_target(monday),
                      selected=monday == self.active_week, size=7,
                      title=self.schedule.week_key(monday))
        label_y = H - 63 - len(self.schedule.weeks) * step
        self.text(W - 19, label_y, "BACKLOG", 5.5, bold=True, align="center")
        self.link("Backlog", "home", (W - 34, label_y - 7, W - 4, label_y + 9))
        top = label_y - 10
        step = min(30, (top - 69) / self.config.list_count)
        for number in range(1, self.config.list_count + 1):
            self.pill(W - 32, top - number * step + 4, 26, step - 4,
                      f"{number:02d}", f"list-{number}", selected=number == active,
                      title=self.tr("Liste {number:02d}", number=number), size=9)

    def footer(self, *, day=None, context=None, previous=None, next_page=None,
               next_day=None, previous_day=None, previous_label=None, next_width=76):
        self.line(LEFT, 45, RIGHT, 45, gray=0.55)
        self.text(LEFT, 25, self.tr("Accueil"), 8, bold=True)
        self.link("Home", "home", (LEFT, 15, LEFT + 49, 40))
        self.text(LEFT + 61, 25, self.label("Calendrier", "Calendar"), 8, bold=True)
        month = self.current_date or self.schedule.start
        self.link("Calendar", self.month_key(month), (LEFT + 57, 15, LEFT + 120, 40))
        if context:
            label, target, title = context
            self.text(LEFT + 140, 25, label, 8, bold=True, max_width=89)
            self.link(title, target, (LEFT + 135, 15, LEFT + 230, 40))
        if previous_day or next_day:
            self.text(RIGHT - 110, 25, self.tr("Jour"), 8, bold=True, align="center")
            if previous_day:
                self.text(RIGHT - 126, 25, "<", 8, bold=True, align="center")
                self.link("Previous day", previous_day, (RIGHT - 141, 15, RIGHT - 113, 40))
            if next_day:
                self.text(RIGHT - 94, 25, ">", 8, bold=True, align="center")
                self.link("Next day", next_day, (RIGHT - 107, 15, RIGHT - 79, 40))
            next_width = 66
        elif previous and previous_label:
            self.text(RIGHT - next_width - 59, 25, "< " + previous_label, 8, bold=True, max_width=49)
            self.link("Previous", previous, (RIGHT - next_width - 64, 15, RIGHT - next_width - 10, 40))
        if next_page:
            label, target = next_page
            self.text(RIGHT - 5, 25, label + " >", 8, bold=True, align="right", max_width=next_width - 5)
            self.link("Next", target, (RIGHT - next_width, 15, RIGHT, 40))
        self.text(W - 19, 25, self.ordinal, 7, gray=MUTED, align="center", numeric=True)

    def home(self):
        self.current_date = self.active_week = None
        self.start("home", outline=self.config.title)
        self.header(self.label("VIWOODS AIPAPER / CARNET DATÉ", "VIWOODS AIPAPER / DATED NOTEBOOK"),
                    self.config.title, subtitle=f"{self.schedule.start:%d.%m.%Y} — {self.schedule.end_date:%d.%m.%Y}")
        self.rail()
        self.text(LEFT, H - 117, self.label("Mon calendrier", "My calendar"), 13, bold=True)
        months = self.schedule.calendar_months
        width = (WIDTH - 7 * (len(months) - 1)) / len(months)
        for index, month in enumerate(months):
            label = f"{self.month_name(month).capitalize()} {month.year}"
            self.pill(LEFT + index * (width + 7), H - 154, width, 27,
                      label, self.month_key(month), title=self.month_key(month), size=8)
        self.text(LEFT, H - 188, self.label("Mes semaines", "My weeks"), 13, bold=True)
        columns = min(7, len(self.schedule.weeks))
        width = (WIDTH - 6 * (columns - 1)) / columns
        for index, monday in enumerate(self.schedule.weeks):
            row, col = divmod(index, columns)
            x, y = LEFT + col * (width + 6), H - 221 - row * 31
            sunday = monday + timedelta(days=6)
            date_range = (f"{monday.day:02d}–{sunday:%d/%m}" if monday.month == sunday.month
                          else f"{monday:%d/%m}–{sunday:%d/%m}")
            self.pill(x, y, width, 25, "", self.week_target(monday),
                      title=self.schedule.week_key(monday))
            self.text(x + width / 2, y + 14, self.week_label(monday), 8,
                      bold=True, align="center")
            self.text(x + width / 2, y + 4, date_range, 6, gray=MUTED,
                      align="center", max_width=width - 6)
        self.text(LEFT, H - 287, "Backlog", 15, bold=True)
        cell = (WIDTH - 12) / 2
        for number in range(1, self.config.list_count + 1):
            row, col = divmod(number - 1, 2)
            x, y = LEFT + col * (cell + 12), H - 320 - row * 42
            self.text(x, y, f"{number:02d}", 13, bold=True)
            self.text(x + 28, y + 1, self.config.list_name(number), 9, max_width=cell - 44)
            self.text(x + cell - 2, y, ">", 11, align="right")
            self.line(x, y - 9, x + cell, y - 9)
            self.link(self.tr("Liste {number:02d}", number=number), f"list-{number}",
                      (x, y - 8, x + cell, y + 22))
        self.footer(next_page=(self.label("Commencer", "Start"), "day-1"))
        self.end()

    def calendar(self, index):
        month = self.schedule.calendar_months[index]
        self.current_date = month
        self.active_week = None
        self.start(self.month_key(month), outline=f"{self.month_name(month).capitalize()} {month.year}", level=1)
        self.header(self.label("CALENDRIER", "CALENDAR"), f"{self.month_name(month).capitalize()} {month.year}")
        self.rail()
        week_width, gap = 29, 3
        cell = (WIDTH - week_width) / 7
        top, row_height = H - 145, 59
        self.text(LEFT + 11, top + 15, "W", 7, gray=MUTED, align="center")
        for col, name in enumerate(WEEKDAYS[self.config.language]):
            self.text(LEFT + week_width + col * cell + cell / 2, top + 15,
                      name.upper(), 7, bold=True, gray=MUTED, align="center")
        for row, days in enumerate(calendar.Calendar(firstweekday=0).monthdatescalendar(month.year, month.month)):
            monday = days[0]
            y = top - (row + 1) * row_height
            if monday in self.schedule.weeks:
                self.pill(LEFT, y + 15, 24, 25, self.week_label(monday), self.week_target(monday),
                          title=self.schedule.week_key(monday), size=6.5)
            for col, value in enumerate(days):
                x = LEFT + week_width + col * cell
                in_month = value.month == month.month
                enabled = in_month and self.schedule.start <= value <= self.schedule.end_date
                self.c.setFillGray(1 if col < 5 else 0.965)
                self.c.setStrokeGray(0.80 if enabled else 0.92)
                self.c.setLineWidth(0.45)
                self.c.roundRect(x, y, cell - gap, row_height - gap, 3, fill=1, stroke=1)
                if in_month:
                    self.text(x + 7, y + row_height - 19, value.day, 11,
                              bold=enabled, gray=0.12 if enabled else 0.72, numeric=True)
                if enabled:
                    self.link(value.isoformat(), self.day_key(value),
                              (x, y, x + cell - gap, y + row_height - gap))
        previous = self.schedule.calendar_months[index - 1] if index else None
        following = self.schedule.calendar_months[index + 1] if index + 1 < len(self.schedule.calendar_months) else None
        self.footer(previous=self.month_key(previous) if previous else None,
                    previous_label=self.month_name(previous).capitalize()[:4] if previous else None,
                    next_page=(self.month_name(following).capitalize(), self.month_key(following)) if following else None)
        self.end()

    def weekly(self, monday, part):
        self.active_week = monday
        self.current_date = max(monday, self.schedule.start)
        first = max(monday, self.schedule.start)
        last = min(monday + timedelta(days=6), self.schedule.end_date)
        iso_year = monday.isocalendar().year
        self.start(self.week_target(monday, part),
                   outline=f"{self.week_label(monday)} / {iso_year}" if part == 1 else None, level=1)
        self.header(f"{self.week_label(monday)} / {iso_year} — " + self.label("TÂCHES", "TASKS"),
                    self.label("Ma semaine", "Weekly tasks"),
                    subtitle=f"{first:%d.%m} — {last:%d.%m.%Y}   /   {part:02d}/{self.schedule.week_pages:02d}")
        self.rail()
        cell = (WIDTH - 6 * 5) / 7
        for col in range(7):
            value = monday + timedelta(days=col)
            label = f"{WEEKDAYS[self.config.language][col]} {value.day:02d}"
            x = LEFT + col * (cell + 5)
            if self.schedule.start <= value <= self.schedule.end_date:
                self.pill(x, H - 130, cell, 25, label, self.day_key(value), title=value.isoformat(), size=7)
            else:
                self.text(x + cell / 2, H - 121, label, 7, gray=0.7, align="center")
        rows = ceil(self.schedule.weekly_tasks / 2)
        col_width = (WIDTH - 20) / 2
        for index in range(self.schedule.weekly_tasks):
            col, row = divmod(index, rows)
            x, y = LEFT + col * (col_width + 20), H - 165 - row * 20
            self.c.setStrokeGray(0.55)
            self.c.setLineWidth(0.45)
            self.c.rect(x, y + 1, 6, 6, fill=0, stroke=1)
            self.line(x + 12, y, x + 44, y)
            self.text(x + 49, y + 2, "·", 8, gray=MUTED, align="center")
            self.line(x + 55, y, x + col_width, y)
        self.footer(previous=self.week_target(monday, part - 1) if part > 1 else None,
                    previous_label=f"Page {part - 1}" if part > 1 else None,
                    next_page=(f"Page {part + 1}", self.week_target(monday, part + 1))
                    if part < self.schedule.week_pages else None)
        self.end()

    def meeting(self, day):
        value = self.schedule.dates[day - 1]
        self.current_date = value
        self.active_week = self.schedule.week_for_day(day)
        self.start(f"day-{day}", outline=self.full_date(value), level=1)
        self.header(f"{self.week_label(self.active_week)} / {self.full_date(value).upper()}", "Meetings")
        self.text(LEFT + 183, H - 48, self.label("Sujet / temps fort", "Focus / subject"), 7, gray=MUTED)
        self.line(LEFT + 183, H - 74, RIGHT, H - 74, gray=0.55)
        self.rail()
        mid = LEFT + WIDTH * 0.55
        self.text(LEFT, H - 113, "Objectives", 13, bold=True)
        self.text(mid + 14, H - 113, "Agenda", 14, bold=True)
        self.line(mid, H - 106, mid, H - 227, gray=0.8)
        for index in range(5):
            y = H - 134 - index * 21
            self.text(LEFT, y + 4, f"{index + 1:02d}", 7, gray=MUTED, numeric=True)
            self.line(LEFT + 22, y, mid - 15, y)
        self.text(LEFT, H - 254, "Notes", 14, bold=True)
        self.rules(H - 286)
        next_page = ("Notes 1", f"day-{day}-notes-1") if self.config.notes_pages else None
        self.footer(context=(self.week_label(self.active_week), self.week_target(self.active_week),
                             self.schedule.week_key(self.active_week)), next_page=next_page,
                    previous_day=f"day-{day - 1}" if day > 1 else None,
                    next_day=f"day-{day + 1}" if day < len(self.schedule.dates) else None)
        self.end()

    def meeting_notes(self, day, number):
        value = self.schedule.dates[day - 1]
        self.current_date = value
        self.active_week = self.schedule.week_for_day(day)
        self.start(f"day-{day}-notes-{number}")
        self.header(f"{self.full_date(value).upper()} / NOTES {number:02d}", "Notes")
        self.link(f"Meeting {value.isoformat()}", f"day-{day}", (LEFT, H - 43, RIGHT, H - 22))
        self.text(LEFT + 183, H - 48, self.label("Sujet", "Subject"), 7, gray=MUTED)
        self.line(LEFT + 183, H - 74, RIGHT, H - 74, gray=0.55)
        self.rail()
        self.rules(H - 111)
        if number < self.config.notes_pages:
            following = (f"Notes {number + 1}", f"day-{day}-notes-{number + 1}")
        elif day < len(self.schedule.dates):
            following = (self.label("Jour suivant", "Next day"), f"day-{day + 1}")
        else:
            following = (self.label("Calendrier", "Calendar"), self.month_key(value))
        self.footer(context=(f"< Meeting {value:%d/%m}", f"day-{day}", f"Meeting {value.isoformat()}"),
                    previous=f"day-{day}-notes-{number - 1}" if number > 1 else None,
                    previous_label=f"Notes {number - 1}" if number > 1 else None, next_page=following)
        self.end()

    def header(self, eyebrow, title, *, subtitle=None):
        if eyebrow.startswith("TODO / "):
            eyebrow = eyebrow.replace("TODO / ", "BACKLOG / ", 1)
        super().header(eyebrow, title, subtitle=subtitle)

    def task_list(self, number):
        self.current_date = self.active_week = None
        super().task_list(number)

    def task_notes(self, number, item, part):
        self.current_date = self.active_week = None
        super().task_notes(number, item, part)
