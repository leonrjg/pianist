# Proposal: SVG Icon Engine for Tinted Icons

## Context

Sheet menu icons are SVGs tinted at theme-application time via `_tinted_icon()` in
`sheet_menu.py`. The current patch (as of this writing) fixes the immediate blur by
rasterizing at `size × devicePixelRatio` and tagging the result pixmap with the DPR.

This works, but the approach is still fundamentally eager: rasterization happens once
at construction time, baking a specific physical resolution into the `QIcon`. Two
scenarios where this breaks down:

- **Multi-monitor with mixed DPR** — if the window moves from a 1× to a 2× screen
  (or vice versa), the pre-baked pixmap is the wrong physical size.
- **Size variation** — if Qt ever needs the icon at a different size (e.g. a larger
  active-state representation, or a future toolbar resize), it stretches the baked
  pixmap rather than re-rendering the vector.

## Proposed Solution: `TintedSvgIconEngine`

Subclass `QIconEngine` to defer all rasterization to paint time.

```python
from PyQt6.QtCore import QRect, QSize
from PyQt6.QtGui import QColor, QIcon, QIconEngine, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import Qt


class TintedSvgIconEngine(QIconEngine):
    def __init__(self, svg_path: str, tint: str):
        super().__init__()
        self._svg_path = svg_path
        self._tint = tint  # "rgb(r,g,b)" or ""

    def paint(self, painter: QPainter, rect: QRect, mode, state):
        renderer = QSvgRenderer(self._svg_path)
        # Render SVG into a pixmap at physical pixel dimensions
        dpr = painter.device().devicePixelRatioF()
        px = QPixmap(int(rect.width() * dpr), int(rect.height() * dpr))
        px.fill(Qt.GlobalColor.transparent)
        px.setDevicePixelRatio(dpr)
        p = QPainter(px)
        renderer.render(p, px.rect())
        p.end()
        if self._tint:
            p2 = QPainter(px)
            p2.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            r, g, b = [int(v.strip()) for v in self._tint[4:-1].split(',')]
            p2.fillRect(px.rect(), QColor(r, g, b))
            p2.end()
        painter.drawPixmap(rect, px)

    def pixmap(self, size: QSize, mode, state) -> QPixmap:
        px = QPixmap(size)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        self.paint(p, px.rect(), mode, state)
        p.end()
        return px

    def clone(self):
        return TintedSvgIconEngine(self._svg_path, self._tint)


def _tinted_icon(icon_path: str, tint: str) -> QIcon:
    return QIcon(TintedSvgIconEngine(icon_path, tint))
```

The `size` parameter disappears from the signature — the engine receives the correct
size from Qt at every paint call, so there is nothing to pre-specify.

## Tradeoffs

| | Current patch | Engine |
|---|---|---|
| Blurry on same-DPR screen | Fixed | Fixed |
| Correct on DPR change (window move) | No | Yes |
| Handles arbitrary sizes | No | Yes |
| Code complexity | Low | Medium |
| Extra dependency | None | `PyQt6.QtSvg` |

`PyQt6.QtSvg` is already a standard part of PyQt6 (no extra install), so the only
real cost is the added indirection of the engine class.

## Recommendation

Adopt the engine when/if multi-monitor support or icon size flexibility becomes a
priority. The current patch is adequate for single-monitor, fixed-size icon use.
