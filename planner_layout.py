"""Per-instance page geometry. Nothing here mutates a module constant.

Margins, rails and footers keep their physical size on every device: a 24 pt
margin stays 8,5 mm whatever the screen. Only the writing column follows the
page, so the layout scales without any anisotropic distortion.
"""

from dataclasses import dataclass

from planner_formats import DEFAULT_DEVICE, DENSITIES, DEVICES, DeviceFormat, resolve_format


# Ink levels shared by every page template.
INK = 0.12
MUTED = 0.37
RULE = 0.70

MARGIN = 24
RAIL_GUTTER = 49
RAIL_WIDTH = 39
# (note rules, backlog task rows, weekly task rows) for each writing comfort.
ROW_HEIGHTS = {"standard": (22, 22.5, 20), "comfortable": (28, 28.5, 26)}
REFERENCE_HEIGHT = DEVICES[DEFAULT_DEVICE].height_pt


@dataclass(frozen=True)
class PageLayout:
    device: DeviceFormat
    density: str
    width: float
    height: float
    left: float
    right: float
    content_width: float
    rail_width: float
    row_height: float
    task_row_height: float
    weekly_row_height: float
    body_bottom: float
    footer_rule: float

    @property
    def pagesize(self):
        return (self.width, self.height)

    # A writing grid may tighten its lines by this much before it gives up and
    # asks for a second sheet: two tight pages beat two three-fifths empty ones.
    COMPRESSION = 0.85

    def _rows(self, top_offset, step, compression=1.0):
        """Rows fitting between a top offset and the footer, at least one."""
        return max(1, int((self.height - top_offset - 59) // (step * compression)) + 1)

    @property
    def backlog_capacity(self):
        """Backlog tasks a single list sheet can hold, in two columns."""
        return self._rows(126, self.task_row_height, self.COMPRESSION) * 2

    @property
    def weekly_capacity(self):
        return self._rows(165, self.weekly_row_height, self.COMPRESSION) * 2

    @property
    def index_capacity(self):
        """Days a single undated index page can hold, in four columns."""
        return self._rows(154, 43) * 4

    @property
    def writing_height(self):
        """Vertical space a full-page writing area can use."""
        return self.height - 111 - self.body_bottom

    def scaled(self, value):
        """A reference measure grown or shrunk with the page, exact at 1:1."""
        return value * (self.height / REFERENCE_HEIGHT)

    def background_spacing(self, style):
        """A grid wants finer squares than a ruled page wants lines."""
        return {"grid": self.row_height / 2, "dots": 14}.get(style, self.row_height)

    def fit(self, top, step, count, floor=None):
        """Shrink a vertical step so `count` rows stay above the footer."""
        floor = self.footer_rule + 14 if floor is None else floor
        return step if count < 2 else min(step, (top - floor) / (count - 1))

    def fill(self, top, step, count, floor=None, stretch=2.2):
        """Shrink to fit, and spread to the foot of the page when room is left.

        A writing grid that stops two thirds down wastes the paper it was asked
        for, so the lines spread to the foot of the page; `stretch` only stops
        a single surviving row from floating in the middle of nowhere.
        """
        floor = self.footer_rule + 14 if floor is None else floor
        if count < 2:
            return step
        ideal = (top - floor) / (count - 1)
        if ideal < step:
            return ideal  # Not enough room: shrink, exactly as `fit` does.
        return min(ideal, step * stretch)


def make_layout(config):
    device = resolve_format(config)
    density = getattr(config, "density", "standard")
    if not isinstance(density, str) or density not in DENSITIES:
        raise ValueError("Confort d’écriture inconnu : standard ou comfortable.")
    rules, task, weekly = ROW_HEIGHTS[density]
    return PageLayout(
        device=device, density=density,
        width=device.width_pt, height=device.height_pt,
        left=MARGIN, right=device.width_pt - RAIL_GUTTER,
        content_width=device.width_pt - RAIL_GUTTER - MARGIN,
        rail_width=RAIL_WIDTH, row_height=rules,
        task_row_height=task, weekly_row_height=weekly,
        body_bottom=67, footer_rule=45,
    )
