"""Per-instance page geometry. Nothing here mutates a module constant.

Margins, rails and footers keep their physical size on every device: a 24 pt
margin stays 8,5 mm whatever the screen. Only the writing column follows the
page, so the layout scales without any anisotropic distortion.
"""

from dataclasses import dataclass

from planner_formats import DENSITIES, DeviceFormat, resolve_format


MARGIN = 24
RAIL_GUTTER = 49
RAIL_WIDTH = 39
# (note rules, backlog task rows, weekly task rows) for each writing comfort.
ROW_HEIGHTS = {"standard": (22, 22.5, 20), "comfortable": (28, 28.5, 26)}


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

    @property
    def writing_height(self):
        """Vertical space a full-page writing area can use."""
        return self.height - 111 - self.body_bottom


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
