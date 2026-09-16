"""Writing backgrounds. Nothing is drawn outside the bounds it is given.

`lined` and `dots` reproduce the historical Meeting and task-context pages
exactly, operation for operation, so the published notebooks stay identical.
"""

NOTE_STYLES = {"lined": "Ligné", "dots": "Pointillé", "grid": "Quadrillé", "blank": "Blanc"}
RULE = 0.70
DOT_GRAY = 0.52
DOT_RADIUS = 0.42
GRID_GRAY = 0.74


def draw_note_background(canvas, bounds, style, spacing):
    """Fill one writing area, from `bounds` = (left, bottom, right, top)."""
    if style not in NOTE_STYLES:
        raise ValueError("Fond de notes inconnu : " + ", ".join(NOTE_STYLES) + ".")
    left, bottom, right, top = bounds
    if style == "blank" or spacing <= 0 or right <= left or top <= bottom:
        return
    if style == "lined":
        # The stroke state is set per line, exactly as the historical rules did.
        y = top
        while y >= bottom:
            canvas.setStrokeGray(RULE)
            canvas.setLineWidth(0.45)
            canvas.line(left, y, right, y)
            y -= spacing
    elif style == "dots":
        canvas.setFillGray(DOT_GRAY)
        x = left
        while x <= right:
            y = bottom
            while y <= top:
                canvas.circle(x, y, DOT_RADIUS, stroke=0, fill=1)
                y += spacing
            x += spacing
    else:
        canvas.setStrokeGray(GRID_GRAY)
        canvas.setLineWidth(0.35)
        y = top
        while y >= bottom:
            canvas.line(left, y, right, y)
            y -= spacing
        x = left
        while x <= right:
            canvas.line(x, bottom, x, top)
            x += spacing
