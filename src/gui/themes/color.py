from PyQt6.QtGui import QColor


def parse_color(s: str, alpha: int | None = None) -> QColor:
    """Parse 'rgb(r,g,b)' or 'rgba(r,g,b,a)' into QColor."""
    s = s.strip()
    if s.startswith('rgba('):
        parts = s[5:-1].split(',')
        r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
        a = int(float(parts[3])) if len(parts) > 3 else 255
    elif s.startswith('rgb('):
        parts = s[4:-1].split(',')
        r, g, b, a = int(parts[0]), int(parts[1]), int(parts[2]), 255
    else:
        return QColor(s)
    if alpha is not None:
        a = alpha
    return QColor(r, g, b, a)
