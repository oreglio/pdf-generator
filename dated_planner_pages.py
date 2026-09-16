"""Dated navigation and layouts, isolated from the reproducible undated edition."""

import calendar
from datetime import date, timedelta
from math import ceil

from planner_manifest import sheet_key
from planner_pages import PlannerPages, INK, MUTED


MONTHS = {
    "fr": ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
           "septembre", "octobre", "novembre", "décembre"),
    "en": ("January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"),
}
WEEKDAYS = {"fr": ("Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"),
            "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")}
MONTH_TABS = {
    "fr": ("JANV", "FÉVR", "MARS", "AVR", "MAI", "JUIN", "JUIL", "AOÛT",
           "SEPT", "OCT", "NOV", "DÉC"),
    "en": ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG",
           "SEP", "OCT", "NOV", "DEC"),
}


class DatedPlannerPages(PlannerPages):
    def __init__(self, canvas, schedule, *, interactive=True):
        self.schedule = schedule
        self.current_date = None
        self.active_week = None
        super().__init__(canvas, schedule.render_config, interactive=interactive)

    def label(self, french, english):
        return french if self.config.language == "fr" else english

    def text(self, x, y, value, size=10, **kwargs):
        if value == "·":
            size = 10
            kwargs["bold"] = True
        super().text(x, y, value, size, **kwargs)

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

    def month_tab(self, value):
        return MONTH_TABS[self.config.language][value.month - 1]

    def backlog_rail(self, label_y, active):
        """Shared bottom of both rails: the backlog keeps the same tabs."""
        self.text(self.w - 19, label_y, "BACKLOG", 5.5, bold=True, align="center")
        self.link("Backlog", "home", (self.w - 34, label_y - 7, self.w - 4, label_y + 9))
        top = label_y - 10
        step = min(30, (top - 69) / self.config.list_count)
        for number in range(1, self.config.list_count + 1):
            self.pill(self.w - 32, top - number * step + 4, 26, step - 4,
                      f"{number:02d}", f"list-{number}", selected=number == active,
                      title=self.tr("Liste {number:02d}", number=number), size=9)

    def month_rail(self, active=None):
        """Long periods index their months; weeks stay inside each calendar."""
        self.line(self.w - 39, 69, self.w - 39, self.h - 31, gray=0.85)
        self.text(self.w - 19, self.h - 39, self.label("MOIS", "MONTHS"), 5.5, bold=True, align="center")
        months = self.schedule.calendar_months
        two_years = self.schedule.spans_two_years
        step = min(26, 300 / len(months))
        current = self.current_date
        for index, month in enumerate(months):
            y = self.h - 50 - (index + 1) * step
            height = step - 3
            selected = (current is not None
                        and (current.year, current.month) == (month.year, month.month))
            self.pill(self.w - 32, y, 26, height, "", self.month_key(month),
                      selected=selected, title=self.month_key(month))
            ink = 1 if selected else INK
            if two_years:
                self.text(self.w - 19, y + height - 7, self.month_tab(month), 5.5, bold=True,
                          gray=ink, align="center", max_width=22)
                self.text(self.w - 19, y + 2.5, f"{month.year % 100:02d}", 5,
                          gray=1 if selected else MUTED, align="center")
            else:
                self.text(self.w - 19, y + (height - 5.5) / 2 + 1, self.month_tab(month), 5.5,
                          bold=True, gray=ink, align="center", max_width=22)
        self.backlog_rail(self.h - 63 - len(months) * step, active)

    def rail(self, active=None):
        if self.schedule.long_navigation:
            return self.month_rail(active)
        self.line(self.w - 39, 69, self.w - 39, self.h - 31, gray=0.85)
        self.text(self.w - 19, self.h - 39, self.label("SEMAINES", "WEEKS"), 5.5, bold=True, align="center")
        step = min(26, 270 / len(self.schedule.weeks))
        for index, monday in enumerate(self.schedule.weeks):
            self.pill(self.w - 32, self.h - 50 - (index + 1) * step, 26, step - 3,
                      self.week_label(monday), self.week_target(monday),
                      selected=monday == self.active_week, size=7,
                      title=self.schedule.week_key(monday))
        self.backlog_rail(self.h - 63 - len(self.schedule.weeks) * step, active)

    def footer(self, *, day=None, context=None, previous=None, next_page=None,
               next_day=None, previous_day=None, previous_label=None, next_width=76,
               previous_week=None, next_week=None):
        self.line(self.left, 45, self.right, 45, gray=0.55)
        self.text(self.left, 25, self.tr("Accueil"), 8, bold=True)
        self.link("Home", "home", (self.left, 15, self.left + 49, 40))
        self.text(self.left + 61, 25, self.label("Calendrier", "Calendar"), 8, bold=True)
        month = self.current_date or self.schedule.start
        self.link("Calendar", self.month_key(month), (self.left + 57, 15, self.left + 120, 40))
        if context:
            label, target, title = context
            self.text(self.left + 140, 25, label, 8, bold=True, max_width=89)
            self.link(title, target, (self.left + 135, 15, self.left + 230, 40))
        elif previous_week or next_week:
            if previous_week:
                self.text(self.left + 140, 25, "< " + previous_week[0], 8, bold=True, max_width=44)
                self.link("Previous week", previous_week[1], (self.left + 135, 15, self.left + 186, 40))
            if next_week:
                self.text(self.left + 238, 25, next_week[0] + " >", 8, bold=True,
                          align="right", max_width=44)
                self.link("Next week", next_week[1], (self.left + 192, 15, self.left + 238, 40))
        if previous_day or next_day:
            self.text(self.right - 110, 25, self.tr("Jour"), 8, bold=True, align="center")
            if previous_day:
                self.text(self.right - 126, 25, "<", 8, bold=True, align="center")
                self.link("Previous day", previous_day, (self.right - 141, 15, self.right - 113, 40))
            if next_day:
                self.text(self.right - 94, 25, ">", 8, bold=True, align="center")
                self.link("Next day", next_day, (self.right - 107, 15, self.right - 79, 40))
            next_width = 66
        elif previous and previous_label:
            self.text(self.right - next_width - 59, 25, "< " + previous_label, 8, bold=True, max_width=49)
            self.link("Previous", previous, (self.right - next_width - 64, 15, self.right - next_width - 10, 40))
        if next_page:
            label, target = next_page
            self.text(self.right - 5, 25, label + " >", 8, bold=True, align="right", max_width=next_width - 5)
            self.link("Next", target, (self.right - next_width, 15, self.right, 40))
        self.text(self.w - 19, 25, self.ordinal, 7, gray=MUTED, align="center", numeric=True)

    def home_weeks(self):
        """Historical layout: every month, then every week of the period."""
        months = self.schedule.calendar_months
        width = (self.width - 7 * (len(months) - 1)) / len(months)
        for index, month in enumerate(months):
            label = f"{self.month_name(month).capitalize()} {month.year}"
            self.pill(self.left + index * (width + 7), self.h - 154, width, 27,
                      label, self.month_key(month), title=self.month_key(month), size=8)
        self.text(self.left, self.h - 198, self.label("Mes semaines", "My weeks"), 13, bold=True)
        columns = min(7, len(self.schedule.weeks))
        width = (self.width - 6 * (columns - 1)) / columns
        week_step = self.layout.fit(self.h - 231, 31,
                                    ceil(len(self.schedule.weeks) / columns) * 2)
        for index, monday in enumerate(self.schedule.weeks):
            row, col = divmod(index, columns)
            x, y = self.left + col * (width + 6), self.h - 231 - row * week_step
            sunday = monday + timedelta(days=6)
            date_range = (f"{monday.day:02d}–{sunday:%d/%m}" if monday.month == sunday.month
                          else f"{monday:%d/%m}–{sunday:%d/%m}")
            self.pill(x, y, width, min(25, week_step - 6), "", self.week_target(monday),
                      title=self.schedule.week_key(monday))
            self.text(x + width / 2, y + 14, self.week_label(monday), 8,
                      bold=True, align="center")
            self.text(x + width / 2, y + 4, date_range, 6, gray=MUTED,
                      align="center", max_width=width - 6)
        return self.h - 307

    def home_months(self):
        """Long periods: a readable grid of months instead of 53 week buttons."""
        months = self.schedule.calendar_months
        columns = min(4, len(months))
        rows = ceil(len(months) / columns)
        month_step = self.layout.fit(self.h - 154, 34, rows * 3)
        width = (self.width - 7 * (columns - 1)) / columns
        for index, month in enumerate(months):
            row, col = divmod(index, columns)
            self.pill(self.left + col * (width + 7), self.h - 154 - row * month_step, width,
                      min(27, month_step - 7),
                      f"{self.month_name(month).capitalize()} {month.year}",
                      self.month_key(month), title=self.month_key(month), size=8)
        bottom = self.h - 154 - (rows - 1) * month_step
        self.text(self.left, bottom - 26, self.label(
            "Chaque calendrier ouvre ses semaines et ses journées.",
            "Each calendar opens its weeks and its days."), 8, gray=MUTED, max_width=self.width - 130)
        first = self.schedule.weeks[0]
        self.pill(self.right - 118, bottom - 34, 118, 22,
                  self.label(f"Première semaine · {self.week_label(first)}",
                             f"First week · {self.week_label(first)}"),
                  self.week_target(first), title=self.schedule.week_key(first), size=7.5)
        return bottom - 66

    def draw(self, spec):
        if spec.kind == "calendar":
            return self.calendar(spec)
        if spec.kind == "month-plan":
            return self.month_plan(spec)
        if spec.kind == "week-overview":
            return self.week_overview(spec)
        if spec.kind == "week-review":
            return self.week_review(spec)
        if spec.kind == "weekly":
            return self.weekly(spec)
        return super().draw(spec)

    def home(self):
        self.current_date = self.active_week = None
        self.start("home", outline=self.config.title)
        self.header(self.label("VIWOODS AIPAPER / CARNET DATÉ", "VIWOODS AIPAPER / DATED NOTEBOOK"),
                    self.config.title, subtitle=f"{self.schedule.start:%d.%m.%Y} — {self.schedule.end_date:%d.%m.%Y}")
        self.rail()
        self.text(self.left, self.h - 117, self.label("Mon calendrier", "My calendar"), 13, bold=True)
        backlog_y = self.home_months() if self.schedule.long_navigation else self.home_weeks()
        self.text(self.left, backlog_y, "Backlog", 15, bold=True)
        cell = (self.width - 12) / 2
        backlog_step = self.layout.fit(backlog_y - 33, 46, ceil(self.config.list_count / 2),
                                       floor=self.layout.footer_rule + 22)
        for number in range(1, self.config.list_count + 1):
            row, col = divmod(number - 1, 2)
            x, y = self.left + col * (cell + 12), backlog_y - 33 - row * backlog_step
            self.text(x, y, f"{number:02d}", 13, bold=True)
            if number <= len(self.config.list_names) and self.config.list_names[number - 1].strip():
                self.text(x + 28, y + 1, self.config.list_names[number - 1], 9, max_width=cell - 44)
            self.text(x + cell - 2, y, ">", 11, align="right")
            self.line(x, y - 9, x + cell, y - 9)
            self.link(self.tr("Liste {number:02d}", number=number), f"list-{number}",
                      (x, y - 8, x + cell, y + 22))
        self.footer(next_page=(self.label("Commencer", "Start"), "day-1"))
        self.end()

    def calendar(self, spec):
        month = date.fromisoformat(spec.reference).replace(day=1)
        index = self.schedule.calendar_months.index(month)
        self.current_date = month
        self.active_week = None
        self.start(self.month_key(month), outline=f"{self.month_name(month).capitalize()} {month.year}", level=1)
        self.header(self.label("CALENDRIER", "CALENDAR"), f"{self.month_name(month).capitalize()} {month.year}")
        self.rail()
        week_width, gap = 29, 3
        cell = (self.width - week_width) / 7
        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(month.year, month.month)
        top = self.h - 145
        row_height = min(59, (top - self.layout.footer_rule - 14) / len(weeks))
        self.text(self.left + 11, top + 15, "W", 7, gray=MUTED, align="center")
        for col, name in enumerate(WEEKDAYS[self.config.language]):
            self.text(self.left + week_width + col * cell + cell / 2, top + 15,
                      name.upper(), 7, bold=True, gray=MUTED, align="center")
        for row, days in enumerate(weeks):
            monday = days[0]
            y = top - (row + 1) * row_height
            if monday in self.schedule.weeks:
                self.pill(self.left, y + 15, 24, 25, self.week_label(monday), self.week_target(monday),
                          title=self.schedule.week_key(monday), size=6.5)
            for col, value in enumerate(days):
                x = self.left + week_width + col * cell
                in_month = value.month == month.month
                enabled = in_month and self.schedule.includes_day(value)
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

    def month_plan(self, spec):
        """Three priorities for the month, next to its calendar rather than inside it."""
        month = date.fromisoformat(spec.reference).replace(day=1)
        first, last = self.schedule.month_bounds(month)
        self.current_date = month
        self.active_week = None
        title = f"{self.month_name(month).capitalize()} {month.year}"
        self.start(spec.key, outline=self.label("Priorités — ", "Priorities — ") + title, level=2)
        self.header(self.label("PRIORITÉS DU MOIS", "MONTH PRIORITIES"), title,
                    subtitle=f"{first:%d.%m} — {last:%d.%m.%Y}")
        self.rail()
        self.text(self.left, self.h - 117, self.label("Mes trois priorités", "My three priorities"),
                  13, bold=True)
        top = self.h - 146
        step = min(62, (top - self.layout.body_bottom) * 0.5 / 3)
        deadline = self.label("Échéance", "Due")
        for index in range(3):
            y = top - index * step
            self.text(self.left, y - 20, f"{index + 1:02d}", 19, bold=True, gray=0.72, numeric=True)
            self.line(self.left + 36, y - 24, self.right, y - 24)
            self.text(self.left + 36, y - 42, deadline, 6, gray=MUTED)
            self.line(self.left + 36 + 40, y - 44, self.left + 36 + 170, y - 44)
        weeks = self.schedule.month_weeks(month)
        weeks_y = top - 3 * step - 24
        self.text(self.left, weeks_y + 12, self.label("Ses semaines", "Its weeks"), 8,
                  bold=True, gray=MUTED)
        width = min(58, (self.width - 6 * (len(weeks) - 1)) / max(1, len(weeks)))
        for index, monday in enumerate(weeks):
            self.pill(self.left + index * (width + 6), weeks_y - 16, width, 22,
                      self.week_label(monday), self.week_target(monday),
                      title=self.schedule.week_key(monday), size=7)
        notes_y = weeks_y - 34
        self.text(self.left, notes_y, self.label("Ce que je garde en tête", "What I keep in mind"),
                  8, bold=True, gray=MUTED)
        self.rules(notes_y - 18)
        months = self.schedule.calendar_months
        index = months.index(month)
        following = months[index + 1] if index + 1 < len(months) else None
        # The footer already opens this month's calendar: no second link to it.
        self.footer(next_page=(self.month_name(following).capitalize(),
                               f"month-plan-{following:%Y-%m}") if following else None)
        self.end()

    def week_header(self, spec, eyebrow, title):
        """Shared opening of the three weekly pages of one week."""
        monday = date.fromisoformat(spec.reference)
        self.active_week = monday
        self.current_date = max(monday, self.schedule.start)
        first = max(monday, self.schedule.start)
        last = min(monday + timedelta(days=6), self.schedule.end_date)
        iso_year = monday.isocalendar().year
        self.start(spec.key, outline=f"{self.week_label(monday)} — {title}", level=2)
        self.header(f"{self.week_label(monday)} / {iso_year} — " + eyebrow, title,
                    subtitle=f"{first:%d.%m} — {last:%d.%m.%Y}")
        self.rail()
        return monday

    def week_overview(self, spec):
        """Seven day zones to plan the week; days outside it stay visible."""
        monday = self.week_header(spec, self.label("EN UN COUP D’ŒIL", "AT A GLANCE"),
                                  self.label("Mes sept jours", "Week at a glance"))
        top = self.h - 128
        floor = self.layout.body_bottom
        planning = min(96, (top - floor) * 0.22)
        band = (top - floor - planning - 12) / 7
        label_width = 68
        for index in range(7):
            value = monday + timedelta(days=index)
            y = top - (index + 1) * band
            active = self.schedule.includes_day(value)
            self.line(self.left, y, self.right, y, gray=0.82)
            self.c.setFillGray(1 if active else 0.965)
            self.c.setStrokeGray(0.80 if active else 0.92)
            self.c.setLineWidth(0.45)
            self.c.roundRect(self.left, y + 3, label_width, band - 6, 3, fill=1, stroke=1)
            label = f"{WEEKDAYS[self.config.language][index]} {value.day:02d}"
            self.text(self.left + label_width / 2, y + band / 2 - 3, label, 9, bold=active,
                      gray=0.12 if active else 0.68, align="center", max_width=label_width - 10)
            if active:
                self.link(value.isoformat(), self.day_key(value),
                          (self.left, y + 3, self.left + label_width, y + band - 3))
        plan_y = top - 7 * band - 14
        self.text(self.left, plan_y, self.label("À caler cette semaine", "To place this week"),
                  8, bold=True, gray=MUTED)
        self.rules(plan_y - 16, bottom=floor)
        self.footer(context=(self.week_label(monday), self.week_target(monday),
                             self.schedule.week_key(monday)),
                    next_page=(self.label("Tâches", "Tasks"), self.week_target(monday)))
        self.end()

    def week_review(self, spec):
        """Done / to carry over / to remember, closing the week that ends."""
        monday = self.week_header(spec, self.label("BILAN", "REVIEW"),
                                  self.label("Mon bilan", "Weekly review"))
        top = self.h - 122
        floor = self.layout.body_bottom
        block = (top - floor) / 3
        sections = ((self.label("Terminé", "Done"), self.label("Ce qui est sorti cette semaine.",
                                                              "What shipped this week.")),
                    (self.label("À reporter", "To carry over"),
                     self.label("À réécrire dans la semaine suivante ou dans le backlog.",
                                "To rewrite next week or in the backlog.")),
                    (self.label("À retenir", "To remember"),
                     self.label("Ce qui mérite d’être relu plus tard.", "Worth reading again later.")))
        for index, (title, hint) in enumerate(sections):
            y = top - index * block
            self.text(self.left, y, title, 13, bold=True)
            self.text(self.left + 110, y, hint, 7, gray=MUTED, max_width=self.width - 110)
            self.rules(y - 20, bottom=y - block + 16)
        index = self.schedule.weeks.index(monday)
        following = self.schedule.weeks[index + 1] if index + 1 < len(self.schedule.weeks) else None
        self.footer(context=(self.week_label(monday), self.week_target(monday),
                             self.schedule.week_key(monday)),
                    next_page=(self.week_label(following), self.week_target(following))
                    if following else None)
        self.end()

    def weekly(self, spec):
        monday, part = date.fromisoformat(spec.reference), spec.part
        self.active_week = monday
        self.current_date = max(monday, self.schedule.start)
        first = max(monday, self.schedule.start)
        last = min(monday + timedelta(days=6), self.schedule.end_date)
        iso_year = monday.isocalendar().year
        tasks = spec.last_item - spec.first_item + 1
        subtitle = f"{first:%d.%m} — {last:%d.%m.%Y}   /   {part:02d}/{self.schedule.week_pages:02d}"
        if spec.sheets > 1:
            subtitle += f"   ·   {self.label('feuille', 'sheet')} {spec.sheet}/{spec.sheets}"
        self.start(spec.key, level=1, outline=(
            f"{self.week_label(monday)} / {iso_year}" if part == 1 and spec.sheet == 1 else None))
        self.header(f"{self.week_label(monday)} / {iso_year} — " + self.label("TÂCHES", "TASKS"),
                    self.label("Ma semaine", "Weekly tasks"), subtitle=subtitle)
        self.rail()
        cell = (self.width - 6 * 5) / 7
        for col in range(7):
            value = monday + timedelta(days=col)
            label = f"{WEEKDAYS[self.config.language][col]} {value.day:02d}"
            x = self.left + col * (cell + 5)
            if self.schedule.includes_day(value):
                self.pill(x, self.h - 130, cell, 25, label, self.day_key(value), title=value.isoformat(), size=7)
            else:
                self.text(x + cell / 2, self.h - 121, label, 7, gray=0.7, align="center")
        rows = ceil(tasks / 2)
        row_step = self.layout.fit(self.h - 165, self.layout.weekly_row_height, rows)
        reference_width, reference_gap = 22, 7
        reference_step = reference_width + reference_gap
        reference_end = 2 * reference_step + reference_width
        task_start = reference_end + 11
        right_width = (self.width - 20 - task_start) / 2
        left_width = task_start + right_width
        reference_labels = ("BKLG", "#", self.label("JOUR", "DAY"))
        if tasks > 1:
            divider_x = self.left + left_width + 10
            self.line(divider_x, self.h - 148, divider_x, self.h - 168 - (rows - 1) * row_step,
                      gray=0, width=0.25)
        for index in range(tasks):
            col, row = divmod(index, rows)
            col_width = left_width if col == 0 else right_width
            x = self.left if col == 0 else self.left + left_width + 20
            y = self.h - 165 - row * row_step
            if col == 1:
                if row == 0:
                    self.text(x, y + 16, self.label("TÂCHE", "TASK"), 5.5, gray=MUTED)
                self.line(x, y, x + col_width, y)
                continue
            for field, label in enumerate(reference_labels):
                field_x = x + field * reference_step
                if row == 0:
                    self.text(field_x + reference_width / 2, y + 16, label, 5.5,
                              gray=MUTED, align="center")
                self.line(field_x, y, field_x + reference_width, y)
                if field < 2:
                    separator_x = field_x + reference_width + reference_gap / 2
                    self.line(separator_x, y + 1, separator_x, y + 8)
            if row == 0:
                self.text(x + task_start, y + 16, self.label("TÂCHE", "TASK"), 5.5, gray=MUTED)
            self.text(x + reference_end + 5, y + 2, "·", 10, bold=True, gray=MUTED, align="center")
            self.line(x + task_start, y, x + col_width, y)
        steps = {}
        if self.schedule.long_navigation:
            index = self.schedule.weeks.index(monday)
            if index:
                neighbour = self.schedule.weeks[index - 1]
                steps["previous_week"] = (self.week_label(neighbour), self.week_target(neighbour))
            if index + 1 < len(self.schedule.weeks):
                neighbour = self.schedule.weeks[index + 1]
                steps["next_week"] = (self.week_label(neighbour), self.week_target(neighbour))
        companions = []
        if self.schedule.weekly_overview:
            companions.append((self.label("Vue", "Glance"), f"week-overview-{monday.isoformat()}"))
        if self.schedule.weekly_review:
            companions.append((self.label("Bilan", "Review"), f"week-review-{monday.isoformat()}"))
        for order, (label, target) in enumerate(companions):
            x = self.right - 52 - order * 56
            self.pill(x, self.h - 46, 52, 21, label, target, title=target, size=7)
        chain = [(number, sheet) for number in range(1, self.schedule.week_pages + 1)
                 for sheet in range(1, spec.sheets + 1)]
        position = chain.index((part, spec.sheet))
        if position:
            target, label = self.week_step(monday, chain[position - 1], part, spec.sheets)
            steps["previous"], steps["previous_label"] = target, label
        if position + 1 < len(chain):
            target, label = self.week_step(monday, chain[position + 1], part, spec.sheets)
            steps["next_page"] = (label, target)
        self.footer(**steps)
        self.end()

    def week_step(self, monday, step, part, sheets):
        """(destination, label) of a neighbouring sheet of the same week."""
        number, sheet = step
        target = sheet_key(self.week_target(monday, number), sheet)
        return target, (f"{sheet}/{sheets}" if number == part else f"Page {number}")

    def meeting(self, day):
        value = self.schedule.dates[day - 1]
        self.current_date = value
        self.active_week = self.schedule.week_for_day(day)
        self.start(f"day-{day}", outline=self.full_date(value), level=1)
        self.header(f"{self.week_label(self.active_week)} / {self.full_date(value).upper()}", "Meetings")
        self.text(self.left + 183, self.h - 48, self.label("Sujet / temps fort", "Focus / subject"), 7, gray=MUTED)
        self.line(self.left + 183, self.h - 74, self.right, self.h - 74, gray=0.55)
        self.rail()
        self.meeting_body()
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
        header_right = self.right
        if self.schedule.long_navigation:
            header_right = self.right - 52
            self.pill(self.right - 46, self.h - 46, 46, 21, self.week_label(self.active_week),
                      self.week_target(self.active_week), size=7.5,
                      title=self.schedule.week_key(self.active_week))
        self.link(f"Meeting {value.isoformat()}", f"day-{day}", (self.left, self.h - 43, header_right, self.h - 22))
        self.text(self.left + 183, self.h - 48, self.label("Sujet", "Subject"), 7, gray=MUTED)
        self.line(self.left + 183, self.h - 74, self.right, self.h - 74, gray=0.55)
        self.rail()
        self.rules(self.h - 111)
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
            eyebrow = "BACKLOG"
        super().header(eyebrow, title, subtitle=subtitle)

    def task_list(self, spec):
        self.current_date = self.active_week = None
        if spec.last_item > spec.first_item:
            rows, _, row_step = self.list_geometry(spec)
            divider_x = self.left + self.width / 2
            self.line(divider_x, self.h - 114, divider_x, self.h - 129 - (rows - 1) * row_step,
                      gray=0, width=0.25)
        super().task_list(spec)

    def task_notes(self, number, item, part):
        self.current_date = self.active_week = None
        super().task_notes(number, item, part)
