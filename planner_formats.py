"""Device catalogue: useful drawing surface of each supported tablet.

Sizes come from the official specification sheets and are converted from
pixels to PDF points with the panel density. The PDF stays vectorial: these
numbers describe a physical surface, not a raster export.
"""

from dataclasses import dataclass


MM = 72 / 25.4
CUSTOM = "custom"
# A page shorter than 150 mm cannot hold the Meeting blocks above the writing
# area, so the documented minimum height stays higher than the minimum width.
CUSTOM_WIDTH_MM = (100.0, 400.0)
CUSTOM_HEIGHT_MM = (150.0, 400.0)
DENSITIES = {"standard": "Standard", "comfortable": "Aéré"}
BRANDS = {"viwoods": "Viwoods", "boox": "BOOX", "ipad": "iPad", CUSTOM: "Personnalisé"}


@dataclass(frozen=True)
class DeviceFormat:
    key: str
    brand: str
    label: str
    width_pt: float
    height_pt: float
    source_url: str

    @property
    def width_mm(self):
        return self.width_pt / MM

    @property
    def height_mm(self):
        return self.height_pt / MM

    @property
    def summary(self):
        return f"{self.width_mm:.0f} × {self.height_mm:.0f} mm"


CATALOGUE = (
    # Viwoods AiPaper: 1920 × 2560 px at 300 ppi. Reference profile; keep the
    # exact expression so the historical notebooks stay byte identical.
    DeviceFormat("viwoods-aipaper", "viwoods", "AiPaper 10,65″",
                 1920 * 72 / 300, 2560 * 72 / 300,
                 "https://viwoods.com/products/viwoods-aipaper"),
    DeviceFormat("viwoods-aipaper-mini", "viwoods", "AiPaper Mini 8,2″",
                 1440 * 72 / 292, 1920 * 72 / 292,
                 "https://viwoods.com/pages/compare-aipapermini"),
    DeviceFormat("boox-go-103", "boox", "Go 10.3",
                 1860 * 72 / 300, 2480 * 72 / 300,
                 "https://shop.boox.com/products/go103"),
    DeviceFormat("boox-note-air4c", "boox", "Note Air4 C",
                 1860 * 72 / 300, 2480 * 72 / 300,
                 "https://onyxboox.com/boox_noteair4c"),
    DeviceFormat("boox-note-max", "boox", "Note Max 13,3″",
                 2400 * 72 / 300, 3200 * 72 / 300,
                 "https://shop.boox.com/products/notemax"),
    DeviceFormat("ipad-pro-11-m4", "ipad", "iPad Pro 11″ (M4/M5)",
                 1668 * 72 / 264, 2420 * 72 / 264,
                 "https://support.apple.com/en-us/119892"),
    DeviceFormat("ipad-pro-13-m4", "ipad", "iPad Pro 13″ (M4/M5)",
                 2064 * 72 / 264, 2752 * 72 / 264,
                 "https://support.apple.com/en-us/119891"),
)
DEVICES = {device.key: device for device in CATALOGUE}
DEFAULT_DEVICE = CATALOGUE[0].key


def devices_of(brand):
    return tuple(device for device in CATALOGUE if device.brand == brand)


def _millimetres(value, name, bounds):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} doit être un nombre de millimètres.")
    value = float(value)
    low, high = bounds
    if value != value or value in (float("inf"), float("-inf")) or not low <= value <= high:
        raise ValueError(f"{name} doit être comprise entre {low:.0f} et {high:.0f} mm.")
    return value


def resolve_format(config):
    """Return the drawing surface of a configuration, refusing unknown keys."""
    key = getattr(config, "device", DEFAULT_DEVICE)
    width_mm = getattr(config, "custom_width_mm", None)
    height_mm = getattr(config, "custom_height_mm", None)
    if key == CUSTOM:
        if width_mm is None or height_mm is None:
            raise ValueError("Un format personnalisé demande une largeur et une hauteur en mm.")
        width = _millimetres(width_mm, "La largeur", CUSTOM_WIDTH_MM)
        height = _millimetres(height_mm, "La hauteur", CUSTOM_HEIGHT_MM)
        if width > height:
            raise ValueError("Cette livraison ne dessine que des pages portrait : "
                             "la largeur doit rester inférieure ou égale à la hauteur.")
        return DeviceFormat(CUSTOM, CUSTOM, f"{width:.0f} × {height:.0f} mm",
                            width * MM, height * MM, "")
    if not isinstance(key, str) or key not in DEVICES:
        raise ValueError("Appareil inconnu : " + ", ".join(DEVICES) + " ou custom.")
    if width_mm is not None or height_mm is not None:
        raise ValueError("Les dimensions en millimètres concernent uniquement "
                         "le format personnalisé.")
    return DEVICES[key]
