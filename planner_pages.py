"""Vector page templates and shared navigation for the AiPaper planner."""

from math import ceil
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from planner_layout import INK, MUTED, RULE, make_layout  # noqa: F401  (re-exported)
from planner_manifest import list_key, sheet_key, sheet_of
from planner_note_styles import draw_note_background
from planner_project_pages import ProjectPages


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


class PlannerPages(ProjectPages):
    def __init__(self, canvas, config, *, interactive=True):
        self.c = canvas
        self.config = config
        self.layout = layout = make_layout(config)
        self.w, self.h = layout.width, layout.height        # page box
        self.left, self.right = layout.left, layout.right   # writing column
        self.width = layout.content_width
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
        # Centre on the cap height, not on the em box: digits sit on the baseline.
        cap = pdfmetrics.getFont(self.bold).face.capHeight / 1000 * size
        self.text(x + width / 2, y + (height - cap) / 2, label, size,
                  bold=True, gray=1 if selected else INK, align="center", max_width=width - 8)
        if target is not None:
            self.link(title or label, target, (x, y, x + width, y + height))

    def start(self, key, *, outline=None, level=0):
        self.ordinal += 1
        if self.interactive:
            self.c.bookmarkPage(key, fit="Fit")
            if outline:
                self.c.addOutlineEntry(outline, key, level=level, closed=True)

    def end(self):
        self.c.showPage()

    def writing_header(self, eyebrow, label, back=None):
        """A writing page states what it belongs to, then gets out of the way.

        `back` prefixes a chevron and sizes the tap area to the words: an
        invisible full-width link nobody can see is not an affordance.
        """
        text = f"‹ {eyebrow}" if back else eyebrow
        self.text(self.left, self.h - 34, text, 8, bold=True, gray=MUTED, max_width=self.width)
        if back:
            width = min(self.width, pdfmetrics.stringWidth(text, self.bold, 8))
            self.link(back[1], back[0],
                      (self.left - 3, self.h - 43, self.left + width + 3, self.h - 22))
        self.text(self.left, self.h - 52, label, 7, gray=MUTED)
        self.line(self.left, self.h - 74, self.right, self.h - 74, gray=0.55)

    def header(self, eyebrow, title, *, subtitle=None):
        self.text(self.left, self.h - 34, eyebrow, 8, bold=True, gray=MUTED, max_width=self.width)
        self.text(self.left - 1, self.h - 69, title, 30, bold=True, max_width=self.width)
        if subtitle:
            self.text(self.left, self.h - 90, subtitle, 8.5, gray=MUTED, max_width=self.width)

    def rail(self, active=None):
        self.line(self.w - 39, 69, self.w - 39, self.h - 31, gray=0.85)
        self.text(self.w - 19, self.h - 39, self.tr("JOURS"), 6.5, bold=True, align="center")
        blocks = self.config.index_pages
        per_index = self.config.days_per_index
        tabs = blocks + self.config.list_count + self.config.project_count
        day_step = min(30, (self.h - 146) / tabs)
        day_height = day_step - 4
        for block in range(blocks):
            first = block * per_index + 1
            last = min(first + per_index - 1, self.config.days)
            y = self.h - 51 - day_height - block * day_step
            self.pill(self.w - 32, y, 26, day_height, "", f"days-{block}",
                      title=f"Index {first:03d}–{last:03d}")
            if day_height < 20:  # Too short for two numbers and an arrow.
                self.text(self.w - 19, y + (day_height - 6.5) / 2 + 1, f"{first:03d}",
                          6.5, bold=True, align="center")
                continue
            self.text(self.w - 19, y + day_height - 8, f"{first:03d}", 6.5, bold=True, align="center")
            self.text(self.w - 19, y + 3, f"{last:03d}", 6.5, bold=True, align="center")
            center_y = y + day_height / 2
            triangle = self.c.beginPath()
            triangle.moveTo(self.w - 21, center_y + 1)
            triangle.lineTo(self.w - 17, center_y + 1)
            triangle.lineTo(self.w - 19, center_y - 1.5)
            triangle.close()
            self.c.setFillGray(0)
            self.c.drawPath(triangle, stroke=0, fill=1)
        todo_label_y = self.h - 63 - blocks * day_step
        self.text(self.w - 19, todo_label_y, "TODO", 6.5, bold=True, align="center")
        self.link(self.tr("Mes listes"), "home", (self.w - 34, todo_label_y - 7, self.w - 4, todo_label_y + 9))
        todo_top = todo_label_y - 10
        projects = self.config.project_count
        room = max(0, todo_top - 69) - (13 if projects else 0)
        todo_step = min(31, room / (self.config.list_count + projects))
        if todo_step < 10:
            return
        for number in range(1, self.config.list_count + 1):
            self.pill(self.w - 32, todo_top - number * todo_step + 4, 26, todo_step - 4,
                      f"B{number:02d}", f"list-{number}", selected=number == active,
                      title=self.tr("Liste {number:02d}", number=number),
                      size=8 if todo_step >= 20 else 7)
        self.project_tabs(todo_top - self.config.list_count * todo_step, todo_step)

    def footer_bound(self, *, previous_day, next_day, previous, previous_label,
                     next_page, next_width, edge=None):
        """Leftmost x the right-hand footer slots already occupy."""
        edge = self.right if edge is None else edge
        if previous_day or next_day:
            return edge - 141
        if previous and previous_label:
            return edge - next_width - 64
        if next_page:
            return edge - next_width
        return edge

    def footer(self, *, day=None, context=None, previous=None, next_page=None, next_day=None,
               previous_day=None, previous_label=None, next_width=48):
        self.line(self.left, 45, self.right, 45, gray=0.55)
        self.text(self.left, 25, self.tr("Accueil"), 8, bold=True)
        self.link(self.tr("Accueil"), "home", (self.left, 15, self.left + 49, 40))
        self.text(self.left + 63, 25, self.tr("Journées"), 8, bold=True)
        block = (day - 1) // self.config.days_per_index if day else 0
        self.link(self.tr("Journees"), f"days-{block}", (self.left + 60, 15, self.left + 120, 40))
        bound = self.footer_bound(previous_day=previous_day, next_day=next_day,
                                  previous=previous, previous_label=previous_label,
                                  next_page=next_page, next_width=next_width)
        end = min(self.left + 233, bound - 6)
        if context and end - (self.left + 135) >= 40:
            label, target, title = context
            self.text(self.left + 140, 25, label, 8, bold=True, max_width=end - self.left - 145)
            self.link(title, target, (self.left + 135, 15, end, 40))
        if (previous_day or next_day) and self.right - 141 >= self.left + 130:
            self.text(self.right - 110, 25, self.tr("Jour"), 8, bold=True, align="center")
            if previous_day:
                self.text(self.right - 126, 25, "<", 8, bold=True, align="center")
                self.link(self.tr("Jour precedent"), previous_day, (self.right - 141, 15, self.right - 113, 40))
            if next_day:
                self.text(self.right - 94, 25, ">", 8, bold=True, align="center")
                self.link(self.tr("Jour suivant"), next_day, (self.right - 107, 15, self.right - 79, 40))
        elif previous and previous_label:
            self.text(self.right - next_width - 59, 25, "< " + previous_label, 8,
                      bold=True, max_width=49)
            self.link(previous_label, previous,
                      (self.right - next_width - 64, 15, self.right - next_width - 10, 40))
        elif previous and previous != f"days-{block}":
            self.text(self.right - 69, 25, "<", 12, bold=True, align="center")
            self.link(self.tr("Precedent"), previous, (self.right - 85, 15, self.right - 52, 40))
        next_width = min(next_width, max(30, self.right - (self.left + 128)))
        if next_page:
            label, target = next_page
            self.text(self.right - 5, 25, label + " >", 8, bold=True, align="right", max_width=next_width - 5)
            self.link(self.tr("Suite"), target, (self.right - next_width, 15, self.right, 40))
        self.text(self.w - 19, 25, str(self.ordinal), 7, gray=MUTED, align="center", numeric=True)

    def rules(self, top, bottom=None, step=None, *, left=None, right=None, style=None):
        """The Meeting and Notes writing area, in the chosen background."""
        bottom = self.layout.body_bottom if bottom is None else bottom
        left = self.left if left is None else left
        right = self.right if right is None else right
        style = self.config.meeting_note_style if style is None else style
        step = self.layout.background_spacing(style) if step is None else step
        draw_note_background(self.c, (left, bottom, right, top), style, step)

    @property
    def task_bounds(self):
        """One full row below the subject rule, so no line looks squeezed."""
        return (self.left + 1, 68, self.right, self.h - 74 - self.layout.row_height)

    def _make_dot_form(self):
        """Repeated on every context page: worth one reusable form object."""
        if self.config.task_note_style != "dots" or self.c.hasForm(self.dot_form):
            return
        self.c.beginForm(self.dot_form, 0, 0, self.w, self.h)
        draw_note_background(self.c, self.task_bounds, "dots", 14)
        self.c.endForm()

    def task_background(self):
        if self.config.task_note_style == "dots":
            self.c.doForm(self.dot_form)
        else:
            draw_note_background(self.c, self.task_bounds,
                                 self.config.task_note_style, self.layout.row_height)

    def project_tabs(self, top, step):
        """Numbered project tabs under the lists; the label alone opens the index."""
        count = self.config.project_count
        if not count:
            return
        label_y = top - 13
        self.text(self.w - 19, label_y, self.tr("PROJETS"), 5.5, bold=True, align="center")
        self.link(self.tr("Projets"), "projects",
                  (self.w - 34, label_y - 7, self.w - 4, label_y + 9))
        if step < 10:  # No room for readable tabs: the label still opens the index.
            return
        start = label_y - 10
        for number in range(1, count + 1):
            self.pill(self.w - 32, start - number * step + 4, 26, step - 4,
                      f"P{number:02d}", f"project-{number}",
                      title=self.tr("Projet {number:02d}", number=number),
                      size=8 if step >= 20 else 7)

    def meeting_shortcut(self, day):
        """`both` pushes Notes behind the decisions page: keep them in the footer."""
        if not (self.split_meeting and self.config.notes_pages):
            return None
        return ("Notes ›", f"day-{day}-notes-1", f"Notes {day:03d}")

    def project_slot(self):
        """A fixed place to write which project a meeting belongs to."""
        if not self.config.project_count:
            return
        self.text(self.left, self.h - 88, self.tr("PROJET"), 6.5, gray=MUTED)
        self.line(self.left + 36, self.h - 90, self.left + 172, self.h - 90, gray=0.55)

    def index_key(self, day):
        """The day index holding one day, from the capacity of this device."""
        return f"days-{(day - 1) // self.config.days_per_index}"

    def projects_link(self):
        """Only produced when the notebook actually holds project sheets."""
        if not self.config.project_count:
            return None
        return (self.tr("Projets"), "projects", self.tr("Projets"))

    def draw(self, spec):
        """Draw one manifest entry; the manifest owns the order and the keys."""
        if spec.kind == "home":
            return self.home()
        if spec.kind == "day-index":
            return self.day_index(spec)
        if spec.kind == "meeting":
            return self.meeting(int(spec.reference))
        if spec.kind == "meeting-actions":
            return self.meeting_actions(int(spec.reference))
        if spec.kind == "meeting-notes":
            return self.meeting_notes(int(spec.reference), spec.part)
        if spec.kind == "task-list":
            return self.task_list(spec)
        if spec.kind == "task-notes":
            number, item = (int(value) for value in spec.reference.split("-"))
            return self.task_notes(number, item, spec.part)
        if spec.kind == "projects-index":
            return self.projects_index(spec)
        if spec.kind == "project":
            return self.project_sheet(spec)
        if spec.kind == "project-notes":
            return self.project_notes(spec)
        raise ValueError(f"Type de page inconnu : {spec.kind}")

    def home(self):
        self.start("home", outline=self.config.title)
        self.header(self.tr("VIWOODS AIPAPER / CARNET NON DATÉ"), self.config.title)
        self.rail()
        self.text(self.left, self.h - 119, self.tr("Mes journées"), 15, bold=True)
        self.text(self.right, self.h - 118, self.tr("Première journée >"), 8, align="right", gray=MUTED)
        self.link(self.tr("Premiere journee"), "day-1", (self.right - 105, self.h - 126, self.right, self.h - 106))
        blocks = self.config.index_pages
        per_index = self.config.days_per_index
        columns = min(5, blocks)
        index_rows = ceil(blocks / columns)
        index_step = self.layout.fit(self.h - 154, 32, index_rows * 2)
        index_width = (self.width - 7 * (columns - 1)) / columns
        for block in range(blocks):
            row, col = divmod(block, columns)
            first = block * per_index + 1
            last = min(first + per_index - 1, self.config.days)
            label = f"{first:03d}–{last:03d}"
            self.pill(self.left + col * (index_width + 7), self.h - 154 - row * index_step,
                      index_width, min(26, index_step - 6), label, f"days-{block}",
                      title=self.tr("Journees {label}", label=label), size=8)
        index_extra = (index_rows - 1) * index_step
        self.text(self.left, self.h - 214 - index_extra, self.tr("Mes listes"), 15, bold=True)
        self.text(self.right, self.h - 214 - index_extra, self.tr("{count} tâches / liste", count=self.config.tasks_per_list), 8,
                  align="right", gray=MUTED)
        gap = 12
        cell_w = (self.width - gap) / 2
        list_top = self.h - 250 - index_extra
        list_step = self.layout.fit(list_top, 44, ceil(self.config.list_count / 2),
                                    floor=self.layout.footer_rule + 22)
        for number in range(1, self.config.list_count + 1):
            row, col = divmod(number - 1, 2)
            x = self.left + col * (cell_w + gap)
            y = list_top - row * list_step
            self.line(x, y - 8, x + cell_w, y - 8)
            self.text(x, y + 6, f"{number:02d}", 13, bold=True)
            self.text(x + 28, y + 7, self.config.list_name(number), 9,
                      max_width=cell_w - 44)
            self.text(x + cell_w - 2, y + 6, ">", 11, align="right")
            self.link(self.tr("Liste {number:02d}", number=number), f"list-{number}",
                      (x, y - 7, x + cell_w, y - 7 + min(35, list_step - 2)))
        self.footer(context=self.projects_link(), next_page=(self.tr("Journées"), "days-0"))
        self.end()

    def day_index(self, spec):
        block, first, last = int(spec.reference), spec.first_item, spec.last_item
        self.start(f"days-{block}", outline=self.tr("Journées {first:03d}-{last:03d}", first=first, last=last), level=1)
        self.header(self.tr("INDEX DES JOURNÉES"), self.tr("Journées"),
                    subtitle=f"{first:03d} - {last:03d}")
        self.rail()
        cols, gap = 4, 10
        cell_w = (self.width - gap * (cols - 1)) / cols
        row_step = self.layout.fit(self.h - 154, 43, ceil((last - first + 1) / cols))
        for day in range(first, last + 1):
            row, col = divmod(day - first, cols)
            x = self.left + col * (cell_w + gap)
            y = self.h - 154 - row * row_step
            self.text(x, y + 12, f"{day:03d}", 12, bold=True, numeric=True)
            self.text(x + cell_w - 2, y + 13, ">", 10, align="right", gray=MUTED)
            self.line(x, y + 5, x + cell_w, y + 5)
            self.link(f"Meeting {day:03d}", f"day-{day}",
                      (x, y - 8, x + cell_w, y - 8 + min(37, row_step - 2)))
        next_page = (self.tr("Suite"), f"days-{block + 1}") if block + 1 < self.config.index_pages else (self.tr("Début"), "day-1")
        self.footer(day=first, previous=f"days-{block - 1}" if block else "home", next_page=next_page)
        self.end()

    def meeting(self, day):
        self.start(f"day-{day}", outline=f"Meeting {day:03d}", level=1)
        self.header(self.tr("JOURNÉE {day:03d}", day=day), "Meetings")
        self.rail()
        self.text(self.left + 183, self.h - 48, self.tr("Date / période"), 7, gray=MUTED)
        self.line(self.left + 183, self.h - 74, self.right, self.h - 74, gray=0.55)
        self.project_slot()
        self.meeting_body()
        following = ((self.tr("Décisions"), f"day-{day}-actions") if self.split_meeting
                     else self.meeting_tail(day))
        self.meeting_footer(day, following)
        self.end()

    def meeting_tail(self, day):
        """Where a Meeting leads once its own pages are done."""
        if self.config.notes_pages:
            return ("Notes", f"day-{day}-notes-1")
        if day < self.config.days:
            return (self.tr("Suite"), f"day-{day + 1}")
        return ("Index", self.index_key(day))

    def meeting_footer(self, day, following, **extra):
        extra.setdefault("context", self.meeting_shortcut(day))
        self.footer(day=day, next_page=following,
                    next_day=f"day-{day + 1}" if day < self.config.days else None,
                    previous_day=f"day-{day - 1}" if day > 1 else None, **extra)

    def meeting_actions(self, day):
        """Second page of the same meeting: what was decided, and by whom."""
        self.start(f"day-{day}-actions", outline=f"Meeting {day:03d} — "
                   + self.tr("Décisions & actions"), level=2)
        self.header(self.tr("JOURNÉE {day:03d}", day=day), self.tr("Décisions & actions"))
        self.link(f"Meeting {day:03d}", f"day-{day}",
                  (self.left, self.h - 43, self.left + 120, self.h - 22))
        self.rail()
        self.meeting_notes_actions()
        self.meeting_footer(day, self.meeting_tail(day),
                            context=(f"< Meeting {day:03d}", f"day-{day}", f"Meeting {day:03d}"))
        self.end()

    @property
    def split_meeting(self):
        """`both` gives one meeting two pages: prepare it, then close it."""
        return self.config.meeting_layout == "both"

    def meeting_body(self):
        """The written part of a Meeting page; its navigation never changes."""
        if self.config.meeting_layout == "notes_actions":
            return self.meeting_notes_actions()
        return self.meeting_classic()

    def meeting_classic(self):
        mid = self.left + self.width * 0.55
        self.text(self.left, self.h - 113, "Objectives", 13, bold=True)
        self.text(mid + 14, self.h - 113, "Agenda", 14, bold=True)
        self.line(mid, self.h - 106, mid, self.h - 227, gray=0.8)
        for i in range(5):
            y = self.h - 134 - i * 21
            self.text(self.left, y + 4, f"0{i + 1}", 7, gray=MUTED, numeric=True)
            self.line(self.left + 22, y, mid - 15, y)
        self.text(self.left, self.h - 254, "Notes", 14, bold=True)
        self.rules(self.h - 286)

    def meeting_notes_actions(self):
        """Notes take most of the page; decisions and actions close it."""
        floor = self.layout.body_bottom
        split = floor + (self.h - 111 - floor) * 0.36
        self.text(self.left, self.h - 113, "Notes", 14, bold=True)
        self.rules(self.h - 140, bottom=split + 30)
        if self.config.meeting_note_style != "lined":
            # Ruled notes already close the block; a separator would only add ink.
            self.line(self.left, split + 18, self.right, split + 18, gray=0.55)
        mid = self.left + self.width / 2
        self.text(self.left, split - 4, self.tr("Décisions"), 13, bold=True)
        self.text(mid + 14, split - 4, self.tr("Actions"), 13, bold=True)
        self.line(mid, split + 6, mid, floor - 6, gray=0.8)
        self.rules(split - 26, bottom=floor, right=mid - 14)
        self.rules(split - 26, bottom=floor, left=mid + 14)

    def meeting_notes(self, day, number):
        self.start(f"day-{day}-notes-{number}")
        self.writing_header(f"MEETING {day:03d} / NOTES {number:02d}", self.tr("Date / sujet"),
                            back=(f"day-{day}", f"MEETING {day:03d}"))
        self.rail()
        self.rules(self.h - 74 - self.layout.row_height)
        previous = f"day-{day}-notes-{number - 1}" if number > 1 else None
        if number < self.config.notes_pages:
            next_page = (f"Notes {number + 1}", f"day-{day}-notes-{number + 1}")
        elif day < self.config.days:
            next_page = (self.tr("Jour suivant"), f"day-{day + 1}")
        else:
            next_page = ("Index", self.index_key(day))
        self.footer(day=day, context=(f"< Meeting {day:03d}", f"day-{day}", f"Meeting {day:03d}"),
                    previous=previous, previous_label=f"Notes {number - 1}" if number > 1 else None,
                    next_page=next_page, next_width=76)
        self.end()

    def list_eyebrow(self, number):
        """BACKLOG 01, plus the list's own name when it has one."""
        label = self.tr("TODO / LISTE {number:02d}", number=number)
        if number <= len(self.config.list_names) and self.config.list_names[number - 1]:
            label += f" · {self.config.list_names[number - 1].upper()}"
        return label

    def list_geometry(self, spec):
        """Rows, column width and vertical step shared by both editions."""
        rows = ceil((spec.last_item - spec.first_item + 1) / 2)
        step = self.layout.fill(self.h - 84, self.layout.task_row_height, rows)
        return rows, (self.width - 20) / 2, step

    def task_list(self, spec):
        number, sheet, total = int(spec.reference), spec.sheet, spec.sheets
        self.start(spec.key, level=1, outline=(
            f"TODO {number:02d} - {self.config.list_name(number)}" if sheet == 1 else None))
        eyebrow = self.list_eyebrow(number)
        if total > 1:
            eyebrow += (f"   ·   {spec.first_item:02d} – {spec.last_item:02d}"
                        f"   ·   {sheet:02d}/{total:02d}")
        self.text(self.left, self.h - 34, eyebrow, 8, bold=True, gray=MUTED, max_width=self.width)
        self.link(self.tr("Retour aux listes"), "home",
                  (self.left - 3, self.h - 43,
                   self.left + pdfmetrics.stringWidth(eyebrow, self.bold, 8) + 3, self.h - 22))
        self.rail(active=number)
        rows, col_w, row_step = self.list_geometry(spec)
        for index, item in enumerate(range(spec.first_item, spec.last_item + 1)):
            col, row = divmod(index, rows)
            x = self.left + col * (col_w + 20)
            y = self.h - 84 - row * row_step
            self.line(x, y, x + 21, y)
            self.text(x + 26, y + 2, "·", 8, gray=MUTED, align="center")
            self.text(x + 32, y + 2, f"{item:02d}", 7.5, gray=MUTED, numeric=True)
            self.line(x + 49, y, x + col_w - 20, y)
            self.text(x + col_w - 6, y + 2, ">", 12, bold=True, align="center")
            target = f"task-{number}-{item}-1"
            self.link(self.tr("Tache {number:02d}-{item:02d}", number=number, item=item), target,
                      (x + col_w - 22, y - 5, x + col_w + 2, y - 5 + min(22, row_step)))
        if sheet < total:
            next_page = (f"{sheet + 1}/{total}", sheet_key(f"list-{number}", sheet + 1))
        elif number < self.config.list_count:
            next_page = (self.tr("Liste"), f"list-{number + 1}")
        else:
            next_page = (self.tr("Accueil"), "home")
        self.footer(next_page=next_page,
                    previous=sheet_key(f"list-{number}", sheet - 1) if sheet > 1 else None,
                    previous_label=f"{sheet - 1}/{total}" if sheet > 1 else None)
        self.end()

    def task_notes(self, number, item, part):
        self.start(f"task-{number}-{item}-{part}")
        total_tasks, capacity = self.config.tasks_per_list, self.layout.backlog_capacity
        sheets = self.config.list_sheets
        sheet = sheet_of(item, total_tasks, capacity)
        home_sheet = list_key(number, item, total_tasks, capacity)
        self.writing_header(f"{self.config.list_name(number).upper()} · {number:02d}-{item:02d}"
                            f" — NOTES {part:02d}/{self.config.detail_pages:02d}",
                            self.tr("Sujet"),
                            back=(home_sheet,
                                  self.tr("Retour liste {number:02d}", number=number)))
        self.rail(active=number)
        self.task_background()
        previous = f"task-{number}-{item}-{part - 1}" if part > 1 else None
        next_page = (f"Notes {part + 1}", f"task-{number}-{item}-{part + 1}") if part < self.config.detail_pages else None
        list_label = self.tr("Liste {number:02d}", number=number)
        # A split list keeps one tab per list: name the exact sheet in the footer.
        sheet_label = list_label if sheets == 1 else f"{list_label} {sheet}/{sheets}"
        self.footer(context=("< " + list_label, home_sheet, sheet_label),
                    previous=previous, previous_label=f"Notes {part - 1}" if part > 1 else None,
                    next_page=next_page, next_width=76)
        self.end()
