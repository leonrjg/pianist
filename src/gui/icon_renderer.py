"""Render SVG icons with a theme-driven ink color while preserving accents.

The theme owns the *ink* color: it is substituted for ``currentColor`` in the
SVG source before rendering. Any color the icon hard-codes (for example the amber
accent in the app's glyph set) is left untouched, so a two-tone glyph keeps its
accent under every theme.

This replaces the previous ``CompositionMode_SourceIn`` flatten, which collapsed
every opaque pixel to a single color and therefore destroyed the accent. Color
ownership now has a single, coherent boundary: theme -> ink, icon -> accent.
"""
from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer


def render_icon_pixmap(svg_path: str, ink: str, size: int, dpr: float) -> QPixmap:
    """Return a crisp ``QPixmap`` of ``svg_path`` with ink set to ``ink``.

    ``ink`` is any SVG-valid color string (e.g. ``'rgb(255, 255, 255)'``) that is
    substituted for ``currentColor``; pass an empty string to render the SVG
    exactly as authored. ``size`` is in logical pixels; the pixmap is rendered at
    ``size * dpr`` physical pixels for sharpness on high-DPI screens.
    """
    with open(svg_path, 'r', encoding='utf-8') as f:
        svg = f.read()
    if ink:
        svg = svg.replace('currentColor', ink)
    renderer = QSvgRenderer(QByteArray(svg.encode('utf-8')))
    target = max(1, int(round(size * dpr)))
    pixmap = QPixmap(target, target)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter, QRectF(0, 0, target, target))
    painter.end()
    pixmap.setDevicePixelRatio(dpr)
    return pixmap


def ink_string(color: QColor) -> str:
    """Format a ``QColor`` as an ``rgb(r, g, b)`` string for SVG substitution."""
    return f"rgb({color.red()}, {color.green()}, {color.blue()})"
