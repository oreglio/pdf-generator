"""Configuration of the undated AiPaper planner, independent of Streamlit."""

from dataclasses import asdict, dataclass
from math import ceil

from planner_i18n import LANGUAGES, translate


PAGE_WIDTH = 1920 * 72 / 300
PAGE_HEIGHT = 2560 * 72 / 300
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

    def __post_init__(self):
        for name, low, high in (
            ("list_count", 1, 10), ("tasks_per_list", 1, 40),
            ("detail_pages", 1, 5), ("days", 1, 400), ("notes_pages", 0, 3),
        ):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} doit être un entier entre {low} et {high}.")
        if not isinstance(self.typography, str) or self.typography not in TYPOGRAPHIES:
            raise ValueError("Police inconnue.")
        if not isinstance(self.language, str) or self.language not in LANGUAGES:
            raise ValueError("Langue inconnue : choisir fr ou en.")
        if not isinstance(self.title, str) or not self.title.strip() or len(self.title) > 48:
            raise ValueError("Le titre doit contenir entre 1 et 48 caractères.")
        if not isinstance(self.list_names, (tuple, list)) or len(self.list_names) > self.list_count:
            raise ValueError("Il ne peut pas y avoir plus de noms que de listes.")
        if any(not isinstance(s, str) or len(s) > 24 or '\n' in s for s in self.list_names):
            raise ValueError("Chaque nom de liste doit tenir sur une ligne de 24 caractères.")
        if any(ord(c) < 32 for c in self.title + ''.join(self.list_names)):
            raise ValueError("Les caractères de contrôle ne sont pas autorisés.")
        object.__setattr__(self, "list_names", tuple(s.strip() for s in self.list_names))

    @property
    def index_pages(self):
        return ceil(self.days / 40)

    @property
    def task_count(self):
        return self.list_count * self.tasks_per_list

    @property
    def total_pages(self):
        return (1 + self.index_pages + self.days * (1 + self.notes_pages)
                + self.list_count + self.task_count * self.detail_pages)

    def list_name(self, number):
        if number <= len(self.list_names) and self.list_names[number - 1]:
            return self.list_names[number - 1]
        return self.text("Liste {number:02d}", number=number)

    def text(self, source, **values):
        return translate(self.language, source, **values)

    @property
    def pdf_filename(self):
        suffix = f"{self.days}j" if self.language == "fr" else f"en-{self.days}d"
        return f"aipaper-{self.typography}-{suffix}.pdf"

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
