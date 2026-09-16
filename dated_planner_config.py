"""Configuration for dated weekly planners, separate from the undated notebook."""

from calendar import monthrange
from dataclasses import asdict, dataclass, field, replace
from datetime import date, timedelta

from planner_config import PlannerConfig
from planner_manifest import dated_manifest, sheets


MONTH_RANGE = (1, 12)
QUICK_MONTHS = (1, 2, 3, 6, 12)


def month_choices(current=None):
    """The five quick durations, plus any other valid value already chosen."""
    values = set(QUICK_MONTHS)
    if type(current) is int and MONTH_RANGE[0] <= current <= MONTH_RANGE[1]:
        values.add(current)
    return tuple(sorted(values))


def month_label(months, language='fr'):
    if language == 'en':
        return '12 months · 1 year' if months == 12 else f'{months} month' + ('s' if months > 1 else '')
    return '12 mois · 1 an' if months == 12 else f'{months} mois'


@dataclass(frozen=True)
class DatedPlannerConfig:
    base: PlannerConfig = field(default_factory=PlannerConfig)
    start_date: str = field(default_factory=lambda: date.today().isoformat())
    months: int = 3
    week_pages: int = 1
    weekly_tasks: int = 40
    include_weekends: bool = True

    def __post_init__(self):
        if type(self.include_weekends) is not bool:
            raise ValueError("include_weekends doit être un booléen.")
        if not isinstance(self.base, PlannerConfig):
            raise ValueError("La configuration du backlog doit être un PlannerConfig.")
        for name, low, high in (
            ("months", *MONTH_RANGE), ("week_pages", 1, 3), ("weekly_tasks", 1, 40),
        ):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name} doit être un entier entre {low} et {high}.")
        try:
            if not isinstance(self.start_date, str):
                raise ValueError
            if date.fromisoformat(self.start_date).isoformat() != self.start_date:
                raise ValueError
            self.end_date
        except (ValueError, OverflowError) as exc:
            raise ValueError("La date de début doit être une date ISO valide (AAAA-MM-JJ) "
                             "permettant de calculer toute la période.") from exc

    @property
    def start(self):
        return date.fromisoformat(self.start_date)

    @property
    def end_date(self):
        month_index = self.start.year * 12 + self.start.month - 1 + self.months
        year, month = divmod(month_index, 12)
        month += 1
        day = min(self.start.day, monthrange(year, month)[1])
        return date(year, month, day) - timedelta(days=1)

    @property
    def dates(self):
        candidates = (self.start + timedelta(days=offset)
                      for offset in range((self.end_date - self.start).days + 1))
        return tuple(value for value in candidates if self.includes_day(value))

    def includes_day(self, value):
        return (type(value) is date and self.start <= value <= self.end_date
                and (self.include_weekends or value.weekday() < 5))

    @property
    def weeks(self):
        first = self.start - timedelta(days=self.start.weekday())
        return tuple(first + timedelta(days=offset)
                     for offset in range(0, (self.end_date - first).days + 1, 7))

    @property
    def calendar_months(self):
        first_index = self.start.year * 12 + self.start.month - 1
        last_index = self.end_date.year * 12 + self.end_date.month - 1
        return tuple(date(index // 12, index % 12 + 1, 1)
                     for index in range(first_index, last_index + 1))

    @property
    def long_navigation(self):
        """Month tabs replace the full week index once a period stops fitting."""
        return self.months > 3

    @property
    def spans_two_years(self):
        return self.start.year != self.end_date.year

    @property
    def render_config(self):
        return replace(self.base, days=len(self.dates))

    @property
    def week_sheets(self):
        """Sheets one weekly list needs on this device and writing comfort."""
        capacity = self.render_config.layout.weekly_capacity
        return len(sheets(self.weekly_tasks, capacity))

    @property
    def total_pages(self):
        return len(dated_manifest(self))

    @property
    def pdf_filename(self):
        suffix = "" if self.include_weekends else "-weekdays"
        return (f"dated-aipaper-{self.base.typography}-{self.base.language}-"
                f"{self.start_date}-{self.end_date.isoformat()}{suffix}"
                f"{self.base.format_suffix}.pdf")

    def day_number(self, value):
        if not self.includes_day(value):
            raise ValueError("La journée doit appartenir à la période du carnet.")
        return self.dates.index(value) + 1

    def week_for_day(self, number):
        if type(number) is not int or not 1 <= number <= len(self.dates):
            raise ValueError("Le numéro de journée doit appartenir au carnet.")
        value = self.dates[number - 1]
        return value - timedelta(days=value.weekday())

    def week_key(self, monday):
        if type(monday) is not date or monday not in self.weeks:
            raise ValueError("La semaine doit commencer un lundi et appartenir au carnet.")
        return f"week-{monday.isoformat()}"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, values):
        if not isinstance(values, dict):
            raise ValueError("La configuration doit être un objet JSON.")
        unknown = set(values) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError("Paramètres inconnus : " + ', '.join(sorted(unknown)))
        parsed = dict(values)
        if "base" in parsed:
            parsed["base"] = PlannerConfig.from_dict(parsed["base"])
        return cls(**parsed)
