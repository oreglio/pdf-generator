"""Configuration of the undated AiPaper planner, independent of Streamlit."""

from dataclasses import asdict, dataclass
from math import ceil

from planner_formats import DEFAULT_DEVICE, DEVICES
from planner_i18n import LANGUAGES, translate
from planner_layout import make_layout
from planner_note_styles import NOTE_STYLES
from planner_manifest import sheets, undated_manifest


PAGE_WIDTH = DEVICES[DEFAULT_DEVICE].width_pt
PAGE_HEIGHT = DEVICES[DEFAULT_DEVICE].height_pt
MEETING_LAYOUTS = {"classic": "Objectifs & agenda",
                   "notes_actions": "Notes, décisions & actions",
                   "both": "Les deux, sur deux pages"}
TYPOGRAPHIES = {
    "manrope": "Manrope",
    "manrope-contrast": "Manrope - contraste renforcé",
    "atkinson": "Atkinson Hyperlegible Next",
}


@dataclass(frozen=True)
class PlannerConfig:
    list_count: int = 10
    tasks_per_list: int = 40
    detail_pages: int = 2
    days: int = 200
    notes_pages: int = 2
    typography: str = "manrope"
    title: str = "Meetings & actions"
    list_names: tuple = ()
    language: str = "fr"
    device: str = DEFAULT_DEVICE
    density: str = "standard"
    custom_width_mm: float | None = None
    custom_height_mm: float | None = None
    meeting_note_style: str = "lined"
    task_note_style: str = "dots"
    meeting_layout: str = "classic"
    project_count: int = 0
    project_names: tuple = ()
    project_notes_pages: int = 1

    def __post_init__(self):
        for name, low, high in (
            ("list_count", 1, 10), ("tasks_per_list", 1, 40),
            ("detail_pages", 1, 5), ("days", 1, 400), ("notes_pages", 0, 3),
            ("project_count", 0, 12), ("project_notes_pages", 0, 4),
        ):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} doit être un entier entre {low} et {high}.")
        if self.meeting_layout not in MEETING_LAYOUTS:
            raise ValueError("Composition de Meeting inconnue : "
                             + ", ".join(MEETING_LAYOUTS) + ".")
        for name in ("meeting_note_style", "task_note_style"):
            if getattr(self, name) not in NOTE_STYLES:
                raise ValueError("Fond de notes inconnu : " + ", ".join(NOTE_STYLES) + ".")
        if not isinstance(self.typography, str) or self.typography not in TYPOGRAPHIES:
            raise ValueError("Police inconnue.")
        if not isinstance(self.language, str) or self.language not in LANGUAGES:
            raise ValueError("Langue inconnue : choisir fr ou en.")
        if not isinstance(self.title, str) or not self.title.strip() or len(self.title) > 48:
            raise ValueError("Le titre doit contenir entre 1 et 48 caractères.")
        for field, limit, label in (("list_names", self.list_count, "listes"),
                                    ("project_names", self.project_count, "projets")):
            names = getattr(self, field)
            if not isinstance(names, (tuple, list)) or len(names) > limit:
                raise ValueError(f"Il ne peut pas y avoir plus de noms que de {label}.")
            if any(not isinstance(s, str) or len(s) > 24 or '\n' in s for s in names):
                raise ValueError("Chaque nom doit tenir sur une ligne de 24 caractères.")
            object.__setattr__(self, field, tuple(s.strip() for s in names))
        if any(ord(c) < 32 for c in self.title + ''.join(self.list_names)
               + ''.join(self.project_names)):
            raise ValueError("Les caractères de contrôle ne sont pas autorisés.")
        self.layout  # Refuse an unknown device, comfort or custom size right away.

    @property
    def layout(self):
        return make_layout(self)

    @property
    def format_suffix(self):
        """Empty for the historical profile, so published names never move."""
        if self.device == DEFAULT_DEVICE and self.density == "standard":
            return ""
        device = self.device if self.device in DEVICES else "custom"
        return f"-{device}" + ("" if self.density == "standard" else "-aere")

    @property
    def days_per_index(self):
        """Days one index page holds, from the room the device actually has."""
        return self.layout.index_capacity

    @property
    def index_pages(self):
        return ceil(self.days / self.days_per_index)

    @property
    def tasks_per_list_page(self):
        return self.layout.backlog_capacity

    @property
    def list_sheets(self):
        return len(sheets(self.tasks_per_list, self.tasks_per_list_page))

    @property
    def task_count(self):
        return self.list_count * self.tasks_per_list

    @property
    def total_pages(self):
        return len(undated_manifest(self))

    def list_name(self, number):
        if number <= len(self.list_names) and self.list_names[number - 1]:
            return self.list_names[number - 1]
        return self.text("Liste {number:02d}", number=number)

    def project_name(self, number):
        if number <= len(self.project_names) and self.project_names[number - 1]:
            return self.project_names[number - 1]
        return self.text("Projet {number:02d}", number=number)

    def text(self, source, **values):
        return translate(self.language, source, **values)

    @property
    def pdf_filename(self):
        suffix = f"{self.days}j" if self.language == "fr" else f"en-{self.days}d"
        return f"aipaper-{self.typography}-{suffix}{self.format_suffix}.pdf"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, values):
        if not isinstance(values, dict):
            raise ValueError("La configuration doit être un objet JSON.")
        unknown = set(values) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError("Paramètres inconnus : " + ', '.join(sorted(unknown)))
        return cls(**values)
