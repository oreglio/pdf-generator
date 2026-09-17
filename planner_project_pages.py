"""Project index and project sheets, mixed into the page templates.

A project sheet does not duplicate the detailed notes of the backlog: it keeps
a fixed place for a handwritten backlog reference, and nothing more. A written
reference stays an annotation; it never becomes a link.
"""

from math import ceil

from reportlab.pdfbase import pdfmetrics

from planner_layout import MUTED


class ProjectPages:
    """Pages produced only when a notebook asks for at least one project."""

    def project_eyebrow(self, number, text, target, title):
        """Eyebrow line: the label returns, the note tabs close the right side."""
        self.link(title, target, (self.left - 3, self.h - 43,
                                  self.left + pdfmetrics.stringWidth(text, self.bold, 8) + 3,
                                  self.h - 22))
        self.project_notes_bar(number, current=None)

    def project_notes_bar(self, number, current=None):
        """Every note page of a project, one tap away, on the eyebrow line."""
        self.notes_bar(self.config.project_notes_pages, current,
                       lambda part: f"project-{number}-notes-{part}",
                       self.tr("Projet {number:02d}", number=number))

    def projects_index(self, spec):
        self.start("projects", outline=self.tr("Projets"), level=1)
        self.header(self.tr("PROJETS"), self.tr("Projets"),
                    subtitle=self.tr("{count} fiches", count=self.config.project_count))
        self.rail()
        gap = 12
        cell = (self.width - gap) / 2
        rows = ceil(self.config.project_count / 2)
        top = self.h - 140
        step = self.layout.fit(top, 46, rows, floor=self.layout.footer_rule + 22)
        for number in range(1, self.config.project_count + 1):
            row, col = divmod(number - 1, 2)
            x = self.left + col * (cell + gap)
            y = top - row * step
            self.text(x, y, f"{number:02d}", 13, bold=True)
            names = self.config.project_names
            if number <= len(names) and names[number - 1]:
                self.text(x + 28, y + 1, names[number - 1], 9, max_width=cell - 44)
            self.text(x + cell - 2, y, ">", 11, align="right")
            self.line(x, y - 9, x + cell, y - 9)
            self.link(self.tr("Projet {number:02d}", number=number), f"project-{number}",
                      (x, y - 8, x + cell, y - 8 + min(30, step - 2)))
        self.footer(next_page=(self.tr("Projet"), "project-1"))
        self.end()

    def project_sheet(self, spec):
        """Goal, next actions, decisions and free notes, in that reading order."""
        number = int(spec.reference)
        name = self.config.project_name(number)
        eyebrow = self.tr("PROJET {number:02d}", number=number)
        named = bool(number <= len(self.config.project_names)
                     and self.config.project_names[number - 1])
        self.start(f"project-{number}", outline=f"{number:02d} — {name}", level=2)
        if named:
            self.header(eyebrow, name)
            goal_y = self.h - 108
        else:  # The title would only repeat the eyebrow: give the room away.
            self.text(self.left, self.h - 34, eyebrow, 8, bold=True, gray=MUTED,
                      max_width=self.width)
            goal_y = self.h - 66
        self.project_eyebrow(number, eyebrow, "projects", self.tr("Retour aux projets"))
        self.rail(project=number)
        floor = self.layout.body_bottom
        room = goal_y - floor
        self.text(self.left, goal_y, self.tr("Objectif"), 12, bold=True)
        self.rules(goal_y - 20, bottom=goal_y - room * 0.16)
        actions_y = goal_y - room * 0.2
        self.text(self.left, actions_y, self.tr("Prochaines actions"), 12, bold=True)
        reference = self.tr("BKLG")
        step = min(22, room * 0.24 / 5)
        for index in range(5):
            y = actions_y - 27 - index * step
            self.line(self.left, y, self.left + 21, y)
            self.text(self.left + 32, y + 2, f"{index + 1:02d}", 7.5, gray=MUTED, numeric=True)
            if index == 0:  # One caption row, no column left to guess at.
                self.text(self.left + 10, y + 14, self.tr("FAIT"), 5.5, gray=MUTED,
                          align="center")
                self.text(self.left + 72, y + 14, reference, 5.5, gray=MUTED, align="center")
                self.text(self.left + 104, y + 14, self.tr("ACTION"), 5.5, gray=MUTED)
            self.line(self.left + 50, y, self.left + 94, y)
            self.line(self.left + 104, y, self.right, y)
        decisions_y = actions_y - 34 - 5 * step
        self.text(self.left, decisions_y, self.tr("Décisions"), 12, bold=True)
        self.rules(decisions_y - 20, bottom=decisions_y - room * 0.16)
        notes_y = decisions_y - room * 0.2
        self.text(self.left, notes_y, "Notes", 12, bold=True)
        self.rules(notes_y - 20, bottom=floor)
        following = ((self.tr("Notes"), f"project-{number}-notes-1")
                     if self.config.project_notes_pages else
                     (self.tr("Projet"), f"project-{number + 1}")
                     if number < self.config.project_count else (self.tr("Projets"), "projects"))
        self.footer(context=(self.tr("< Projets"), "projects", self.tr("Projets")),
                    previous=f"project-{number - 1}" if number > 1 else None,
                    previous_label=f"{number - 1:02d}" if number > 1 else None,
                    next_page=following)
        self.end()

    def project_notes(self, spec):
        number, part = int(spec.reference), spec.part
        total = self.config.project_notes_pages
        name = self.config.project_name(number)
        eyebrow = f"{name.upper()} — NOTES {part:02d}/{total:02d}"
        self.start(f"project-{number}-notes-{part}")
        self.writing_header(eyebrow, self.tr("Sujet"),
                            back=(f"project-{number}",
                                  self.tr("Projet {number:02d}", number=number)))
        self.project_notes_bar(number, current=part)
        self.rail(project=number)
        self.rules(self.h - 74 - self.layout.row_height)
        if part < total:
            following = (f"Notes {part + 1}", f"project-{number}-notes-{part + 1}")
        elif number < self.config.project_count:
            following = (self.tr("Projet"), f"project-{number + 1}")
        else:
            following = (self.tr("Projets"), "projects")
        label = self.tr("Projet {number:02d}", number=number)
        self.footer(context=("< " + label, f"project-{number}", label),
                    previous=f"project-{number}-notes-{part - 1}" if part > 1 else None,
                    previous_label=f"Notes {part - 1}" if part > 1 else None,
                    next_page=following, next_width=76)
        self.end()
