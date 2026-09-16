"""Vector page templates and shared navigation for the AiPaper planner."""

from math import ceil
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from planner_config import PAGE_HEIGHT as H, PAGE_WIDTH as W


LEFT = 24
RIGHT = W - 49
WIDTH = RIGHT - LEFT
INK = 0.12
MUTED = 0.37
RULE = 0.70


def register_fonts(variant):
    root = Path(__file__).resolve().parent / "assets/fonts"
    if variant == "atkinson":
        files = (
            ("AtkinsonHyperlegibleNext", "Regular"),
            ("AtkinsonHyperlegibleNext", "SemiBold"),
            ("AtkinsonHyperlegibleMono", "Medium"),
        )
    else:
        regular, bold = ("Medium", "Bold") if variant == "manrope-contrast" else ("Regular", "SemiBold")
        files = (("Manrope", regular), ("Manrope", bold), ("Manrope", regular))
    names = []
    for family, weight in files:
        name = f"Planner-{family}-{weight}"
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(root / family / f"{family}-{weight}.ttf")))
        names.append(name)
    return tuple(names)


class PlannerPages:
    def __init__(self, canvas, config, *, interactive=True):
        self.c = canvas
        self.config = config
        self.tr = config.text
        self.regular, self.bold, self.numbers = register_fonts(config.typography)
        self.interactive = interactive
        self.ordinal = 0
        self.dot_form = f"planner-dots-{config.typography}"
        self._make_dot_form()

    def text(self, x, y, value, size=10, *, bold=False, gray=INK, max_width=None, align="left", numeric=False):
        font = self.numbers if numeric else self.bold if bold else self.regular
        value = str(value)
        if max_width:
            measured = pdfmetrics.stringWidth(value, font, size)
            if measured > max_width:
                size *= max_width / measured
        self.c.setFont(font, size)
        self.c.setFillGray(gray)
        if align == "right":
            self.c.drawRightString(x, y, value)
        elif align == "center":
            self.c.drawCentredString(x, y, value)
        else:
            self.c.drawString(x, y, value)

    def line(self, x1, y1, x2, y2, gray=RULE, width=0.45):
        self.c.setStrokeGray(gray)
        self.c.setLineWidth(width)
        self.c.line(x1, y1, x2, y2)

    def link(self, title, target, rect):
        if self.interactive:
            self.c.linkRect(title, target, rect, relative=0, thickness=0)

    def pill(self, x, y, width, height, label, target, *, selected=False, title=None, size=9):
        self.c.setFillGray(INK if selected else 1)
        self.c.setStrokeGray(INK if selected else 0.65)
        self.c.setLineWidth(0.5)
        self.c.roundRect(x, y, width, height, 4, fill=1, stroke=1)
        self.text(x + width / 2, y + (height - size) / 2 + 2, label, size,
                  bold=True, gray=1 if selected else INK, align="center", max_width=width - 8)
        self.link(title or label, target, (x, y, x + width, y + height))

    def start(self, key, *, outline=None, level=0):
        self.ordinal += 1
        if self.interactive:
            self.c.bookmarkPage(key, fit="Fit")
            if outline:
                self.c.addOutlineEntry(outline, key, level=level, closed=True)

    def end(self):
        self.c.showPage()

    def header(self, eyebrow, title, *, subtitle=None):
        self.text(LEFT, H - 34, eyebrow, 8, bold=True, gray=MUTED, max_width=WIDTH)
        self.text(LEFT - 1, H - 69, title, 30, bold=True, max_width=WIDTH)
        if subtitle:
            self.text(LEFT, H - 90, subtitle, 8.5, gray=MUTED, max_width=WIDTH)

    def rail(self, active=None):
        self.line(W - 39, 69, W - 39, H - 31, gray=0.85)
        self.text(W - 19, H - 39, self.tr("JOURS"), 6.5, bold=True, align="center")
        day_height = 26 if self.config.index_pages <= 5 else 20
        day_step = day_height + 4
        for block in range(self.config.index_pages):
            first = block * 40 + 1
            last = min(first + 39, self.config.days)
            y = H - 51 - day_height - block * day_step
            self.pill(W - 32, y, 26, day_height, "", f"days-{block}",
                      title=f"Index {first:03d}–{last:03d}")
            self.text(W - 19, y + day_height - 8, f"{first:03d}", 6.5, bold=True, align="center")
            self.text(W - 19, y + 3, f"{last:03d}", 6.5, bold=True, align="center")
            center_y = y + day_height / 2
            triangle = self.c.beginPath()
            triangle.moveTo(W - 21, center_y + 1)
            triangle.lineTo(W - 17, center_y + 1)
            triangle.lineTo(W - 19, center_y - 1.5)
            triangle.close()
            self.c.setFillGray(0)
            self.c.drawPath(triangle, stroke=0, fill=1)
        todo_label_y = H - 63 - self.config.index_pages * day_step
        self.text(W - 19, todo_label_y, "TODO", 6.5, bold=True, align="center")
        self.link(self.tr("Mes listes"), "home", (W - 34, todo_label_y - 7, W - 4, todo_label_y + 9))
        todo_top = todo_label_y - 10
        todo_step = min(31, (todo_top - 69) / self.config.list_count)
        for number in range(1, self.config.list_count + 1):
            self.pill(W - 32, todo_top - number * todo_step + 4, 26, todo_step - 4,
                      f"{number:02d}", f"list-{number}", selected=number == active,
                      title=self.tr("Liste {number:02d}", number=number), size=9)

    def footer(self, *, day=None, context=None, previous=None, next_page=None, next_day=None,
               previous_day=None, previous_label=None, next_width=48):
        self.line(LEFT, 45, RIGHT, 45, gray=0.55)
        self.text(LEFT, 25, self.tr("Accueil"), 8, bold=True)
        self.link(self.tr("Accueil"), "home", (LEFT, 15, LEFT + 49, 40))
        self.text(LEFT + 63, 25, self.tr("Journées"), 8, bold=True)
        block = (day - 1) // 40 if day else 0
        self.link(self.tr("Journees"), f"days-{block}", (LEFT + 60, 15, LEFT + 120, 40))
        if context:
            label, target, title = context
            self.text(LEFT + 140, 25, label, 8, bold=True, max_width=90)
            self.link(title, target, (LEFT + 135, 15, LEFT + 233, 40))
        if previous_day or next_day:
            self.text(RIGHT - 110, 25, self.tr("Jour"), 8, bold=True, align="center")
            if previous_day:
                self.text(RIGHT - 126, 25, "<", 8, bold=True, align="center")
                self.link(self.tr("Jour precedent"), previous_day, (RIGHT - 141, 15, RIGHT - 113, 40))
            if next_day:
                self.text(RIGHT - 94, 25, ">", 8, bold=True, align="center")
                self.link(self.tr("Jour suivant"), next_day, (RIGHT - 107, 15, RIGHT - 79, 40))
        elif previous and previous_label:
            self.text(RIGHT - next_width - 59, 25, "< " + previous_label, 8,
                      bold=True, max_width=49)
            self.link(previous_label, previous,
                      (RIGHT - next_width - 64, 15, RIGHT - next_width - 10, 40))
        elif previous and previous != f"days-{block}":
            self.text(RIGHT - 69, 25, "<", 12, bold=True, align="center")
            self.link(self.tr("Precedent"), previous, (RIGHT - 85, 15, RIGHT - 52, 40))
        if next_page:
            label, target = next_page
            self.text(RIGHT - 5, 25, label + " >", 8, bold=True, align="right", max_width=next_width - 5)
            self.link(self.tr("Suite"), target, (RIGHT - next_width, 15, RIGHT, 40))
        self.text(W - 19, 25, str(self.ordinal), 7, gray=MUTED, align="center", numeric=True)

    def rules(self, top, bottom=67, step=22, *, left=LEFT, right=RIGHT):
        y = top
        while y >= bottom:
            self.line(left, y, right, y)
            y -= step

    def _make_dot_form(self):
        if self.c.hasForm(self.dot_form):
            return
        self.c.beginForm(self.dot_form, 0, 0, W, H)
        self.c.setFillGray(0.52)
        x = LEFT + 1
        while x <= RIGHT:
            y = 68
            while y <= H - 105:
                self.c.circle(x, y, 0.42, stroke=0, fill=1)
                y += 14
            x += 14
        self.c.endForm()

    def home(self):
        self.start("home", outline=self.config.title)
        self.header(self.tr("VIWOODS AIPAPER / CARNET NON DATÉ"), self.config.title)
        self.rail()
        self.text(LEFT, H - 119, self.tr("Mes journées"), 15, bold=True)
        self.text(RIGHT, H - 118, self.tr("Première journée >"), 8, align="right", gray=MUTED)
        self.link(self.tr("Premiere journee"), "day-1", (RIGHT - 105, H - 126, RIGHT, H - 106))
        columns = min(5, self.config.index_pages)
        index_width = (WIDTH - 7 * (columns - 1)) / columns
        for block in range(self.config.index_pages):
            row, col = divmod(block, columns)
            first = block * 40 + 1
            last = min(first + 39, self.config.days)
            label = f"{first:03d}–{last:03d}"
            self.pill(LEFT + col * (index_width + 7), H - 154 - row * 32,
                      index_width, 26, label, f"days-{block}",
                      title=self.tr("Journees {label}", label=label), size=8)
        index_extra = (ceil(self.config.index_pages / columns) - 1) * 32
        self.text(LEFT, H - 214 - index_extra, self.tr("Mes listes"), 15, bold=True)
        self.text(RIGHT, H - 214 - index_extra, self.tr("{count} tâches / liste", count=self.config.tasks_per_list), 8,
                  align="right", gray=MUTED)
        gap = 12
        cell_w = (WIDTH - gap) / 2
        for number in range(1, self.config.list_count + 1):
            row, col = divmod(number - 1, 2)
            x = LEFT + col * (cell_w + gap)
            y = H - 250 - index_extra - row * 44
            self.line(x, y - 8, x + cell_w, y - 8)
            self.text(x, y + 6, f"{number:02d}", 13, bold=True)
            self.text(x + 28, y + 7, self.config.list_name(number), 9,
                      max_width=cell_w - 44)
            self.text(x + cell_w - 2, y + 6, ">", 11, align="right")
            self.link(self.tr("Liste {number:02d}", number=number), f"list-{number}", (x, y - 7, x + cell_w, y + 28))
        self.footer(next_page=(self.tr("Journées"), "days-0"))
        self.end()

    def day_index(self, block):
        first = block * 40 + 1
        last = min(first + 39, self.config.days)
        self.start(f"days-{block}", outline=self.tr("Journées {first:03d}-{last:03d}", first=first, last=last), level=1)
        self.header(self.tr("INDEX DES JOURNÉES"), self.tr("Journées"),
                    subtitle=f"{first:03d} - {last:03d}")
        self.rail()
        cols, gap = 4, 10
        cell_w = (WIDTH - gap * (cols - 1)) / cols
        for day in range(first, last + 1):
            row, col = divmod(day - first, cols)
            x = LEFT + col * (cell_w + gap)
            y = H - 154 - row * 43
            self.text(x, y + 12, f"{day:03d}", 12, bold=True, numeric=True)
            self.text(x + cell_w - 2, y + 13, ">", 10, align="right", gray=MUTED)
            self.line(x, y + 5, x + cell_w, y + 5)
            self.link(f"Meeting {day:03d}", f"day-{day}", (x, y - 8, x + cell_w, y + 29))
        next_page = (self.tr("Suite"), f"days-{block + 1}") if block + 1 < self.config.index_pages else (self.tr("Début"), "day-1")
        self.footer(day=first, previous=f"days-{block - 1}" if block else "home", next_page=next_page)
        self.end()

    def meeting(self, day):
        self.start(f"day-{day}", outline=f"Meeting {day:03d}", level=1)
        self.header(self.tr("JOURNÉE {day:03d}", day=day), "Meetings")
        self.rail()
        self.text(LEFT + 183, H - 48, self.tr("Date / période"), 7, gray=MUTED)
        self.line(LEFT + 183, H - 74, RIGHT, H - 74, gray=0.55)
        mid = LEFT + WIDTH * 0.55
        self.text(LEFT, H - 113, "Objectives", 13, bold=True)
        self.text(mid + 14, H - 113, "Agenda", 14, bold=True)
        self.line(mid, H - 106, mid, H - 227, gray=0.8)
        for i in range(5):
            y = H - 134 - i * 21
            self.text(LEFT, y + 4, f"0{i + 1}", 7, gray=MUTED, numeric=True)
            self.line(LEFT + 22, y, mid - 15, y)
        self.text(LEFT, H - 254, "Notes", 14, bold=True)
        self.rules(H - 286)
        next_page = ("Notes", f"day-{day}-notes-1") if self.config.notes_pages else (
            (self.tr("Suite"), f"day-{day + 1}") if day < self.config.days else ("Index", f"days-{(day - 1) // 40}"))
        prev = f"day-{day - 1}" if day > 1 else "days-0"
        self.footer(day=day, previous=prev, next_page=next_page,
                    next_day=f"day-{day + 1}" if day < self.config.days else None,
                    previous_day=f"day-{day - 1}" if day > 1 else None)
        self.end()

    def meeting_notes(self, day, number):
        self.start(f"day-{day}-notes-{number}")
        self.header(f"MEETING {day:03d} / NOTES {number:02d}", "Notes")
        self.rail()
        self.text(LEFT + 183, H - 48, self.tr("Date / sujet"), 7, gray=MUTED)
        self.line(LEFT + 183, H - 74, RIGHT, H - 74, gray=0.55)
        self.rules(H - 111)
        previous = f"day-{day}-notes-{number - 1}" if number > 1 else None
        if number < self.config.notes_pages:
            next_page = (f"Notes {number + 1}", f"day-{day}-notes-{number + 1}")
        elif day < self.config.days:
            next_page = (self.tr("Jour suivant"), f"day-{day + 1}")
        else:
            next_page = ("Index", f"days-{(day - 1) // 40}")
        self.footer(day=day, context=(f"< Meeting {day:03d}", f"day-{day}", f"Meeting {day:03d}"),
                    previous=previous, previous_label=f"Notes {number - 1}" if number > 1 else None,
                    next_page=next_page, next_width=76)
        self.end()

    def task_list(self, number):
        self.start(f"list-{number}", outline=f"TODO {number:02d} - {self.config.list_name(number)}", level=1)
        self.header(self.tr("TODO / LISTE {number:02d}", number=number), self.config.list_name(number))
        self.link(self.tr("Retour aux listes"), "home", (LEFT, H - 43, LEFT + 110, H - 22))
        self.rail(active=number)
        rows = ceil(self.config.tasks_per_list / 2)
        col_w = (WIDTH - 20) / 2
        for item in range(1, self.config.tasks_per_list + 1):
            col, row = divmod(item - 1, rows)
            x = LEFT + col * (col_w + 20)
            y = H - 126 - row * 22.5
            self.line(x, y, x + 21, y)
            self.text(x + 26, y + 2, "·", 8, gray=MUTED, align="center")
            self.text(x + 32, y + 2, f"{item:02d}", 7.5, gray=MUTED, numeric=True)
            self.line(x + 49, y, x + col_w - 20, y)
            self.text(x + col_w - 6, y + 2, ">", 12, bold=True, align="center")
            target = f"task-{number}-{item}-1"
            self.link(self.tr("Tache {number:02d}-{item:02d}", number=number, item=item), target,
                      (x + col_w - 22, y - 5, x + col_w + 2, y + 17))
        next_page = (self.tr("Liste"), f"list-{number + 1}") if number < self.config.list_count else (self.tr("Accueil"), "home")
        self.footer(context=(self.tr("{count} tâches", count=self.config.tasks_per_list), f"list-{number}", self.tr("Liste {number:02d}", number=number)),
                    previous=f"list-{number - 1}" if number > 1 else "home", next_page=next_page)
        self.end()

    def task_notes(self, number, item, part):
        self.start(f"task-{number}-{item}-{part}")
        self.header(f"{self.config.list_name(number).upper()} — NOTES {part:02d}/{self.config.detail_pages:02d}",
                    f"{number:02d}-{item:02d}")
        self.link(self.tr("Retour liste {number:02d}", number=number), f"list-{number}", (LEFT, H - 43, RIGHT, H - 22))
        self.rail(active=number)
        self.text(LEFT + 115, H - 48, self.tr("Sujet"), 7, gray=MUTED)
        self.line(LEFT + 115, H - 74, RIGHT, H - 74, gray=0.55)
        self.c.doForm(self.dot_form)
        previous = f"task-{number}-{item}-{part - 1}" if part > 1 else f"list-{number}"
        next_page = (self.tr("Suite"), f"task-{number}-{item}-{part + 1}") if part < self.config.detail_pages else (self.tr("Liste"), f"list-{number}")
        self.footer(context=(self.tr("Liste {number:02d}", number=number), f"list-{number}", self.tr("Liste {number:02d}", number=number)),
                    previous=previous, next_page=next_page)
        self.end()
