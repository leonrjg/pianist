"""
Inline-Markdown serialization for the notepad.

The note's canonical stored form is Markdown. The QTextDocument shown in the
editor is only a *view* of that string, so this module owns the single mapping
between the two — there is no second source of truth.

Only *inline* character styling is encoded as Markdown:

    **bold**   *italic*   `code`   ~~strike~~   ++underline++

Markdown has no native underline syntax; ``++...++`` is borrowed from the
same doubled-delimiter family as ``~~strike~~`` rather than ``_underline_``,
since underscores are deliberately not treated as emphasis (see below).

Block structure (line breaks and the leading tabs produced by the editor's
auto-indent) is preserved verbatim: each document block is one line joined by a
single ``\n``, and tabs are ordinary text that pass through untouched. This is
deliberately *not* Qt's ``QTextDocument.toMarkdown()`` — that imposes a
paragraph/blank-line model and rewrites leading tabs into indented code blocks,
which would corrupt the auto-indent.

Emphasis is parsed with ``*``/``**`` only (never ``_``), so identifiers such as
``file_name_here`` are never mistaken for italics when a legacy plain-text note
is reinterpreted as Markdown.
"""

from typing import Optional

from PyQt6.QtGui import (
    QColor,
    QFont,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
)

# Marks a character run as inline code. Stored as a boolean on the char format
# so detection is unambiguous (independent of font heuristics).
CODE_PROPERTY = QTextFormat.Property.UserProperty + 1

# Weight applied to bold runs. Kept above Normal so bold detection stays
# weight-based and heavier faces are used on fonts that provide them. The
# editor's actual body font (Oxygen) ships a single weight face, so weight
# alone is invisible there; color (below) carries the emphasis instead.
BOLD_WEIGHT = QFont.Weight.Black

# Characters that carry meaning in our inline dialect and must be backslash-
# escaped when they appear as literal text, so a round-trip is lossless.
_SPECIAL = set("\\*`~+")

# Doubled-delimiter emphasis markers, outer -> inner nesting order. Code is
# handled separately below since it is exclusive rather than nestable.
_MARKERS = [
    ("strike", "~~"),
    ("bold", "**"),
    ("italic", "*"),
    ("underline", "++"),
]


def _is_bold(fmt: QTextCharFormat) -> bool:
    return fmt.fontWeight() > QFont.Weight.Normal


def _is_code(fmt: QTextCharFormat) -> bool:
    return fmt.boolProperty(CODE_PROPERTY)


def make_format(*, bold=False, italic=False, code=False, strike=False, underline=False,
                bold_color: Optional[QColor] = None) -> QTextCharFormat:
    """Build a char format for the given inline flags.

    ``bold_color`` is a view/theme concern injected by the editor: when given,
    bold runs are tinted with it so emphasis reads clearly on fonts whose weight
    faces are indistinguishable. Bold detection stays weight-based, so the color
    is purely decorative and never affects serialization.
    """
    fmt = QTextCharFormat()
    if bold:
        fmt.setFontWeight(BOLD_WEIGHT)
        if bold_color is not None:
            fmt.setForeground(QColor(bold_color))
    fmt.setFontItalic(italic)
    fmt.setFontStrikeOut(strike)
    fmt.setFontUnderline(underline)
    if code:
        fmt.setProperty(CODE_PROPERTY, True)
        fmt.setFontFixedPitch(True)
        fmt.setFontFamilies(["monospace"])
    return fmt


def format_flags(fmt: QTextCharFormat) -> dict:
    """Extract the inline flags from a char format."""
    return {
        "bold": _is_bold(fmt),
        "italic": fmt.fontItalic(),
        "code": _is_code(fmt),
        "strike": fmt.fontStrikeOut(),
        "underline": fmt.fontUnderline(),
    }


# ---------------------------------------------------------------------------
# Document -> Markdown
# ---------------------------------------------------------------------------

def _escape(text: str) -> str:
    return "".join("\\" + ch if ch in _SPECIAL else ch for ch in text)


def _serialize_block(block) -> str:
    out: list[str] = []
    _no_emphasis = {name: False for name, _ in _MARKERS}
    # Currently-open emphasis markers, in nesting order (outer -> inner).
    open_flags = dict(_no_emphasis)

    def transition(target: dict) -> None:
        """Close/open emphasis markers so the open set matches ``target``."""
        if open_flags == target:
            return
        # Close inner -> outer.
        for name, token in reversed(_MARKERS):
            if open_flags[name]:
                out.append(token)
        # Open outer -> inner.
        for name, token in _MARKERS:
            if target[name]:
                out.append(token)
        open_flags.update(target)

    it = block.begin()
    while not it.atEnd():
        fragment = it.fragment()
        if fragment.isValid():
            flags = format_flags(fragment.charFormat())
            text = fragment.text()
            if flags["code"]:
                # Code is exclusive: drop any open emphasis around it.
                transition(_no_emphasis)
                # Use enough backticks to wrap text that itself contains them.
                fence = "`"
                while fence in text:
                    fence += "`"
                pad = " " if text.startswith("`") or text.endswith("`") else ""
                out.append(f"{fence}{pad}{text}{pad}{fence}")
            else:
                transition({name: flags[name] for name, _ in _MARKERS})
                out.append(_escape(text))
        it += 1

    transition(_no_emphasis)
    return "".join(out)


def document_to_markdown(doc: QTextDocument) -> str:
    """Serialize a whole document to inline Markdown (one line per block)."""
    lines: list[str] = []
    block = doc.begin()
    while block.isValid():
        lines.append(_serialize_block(block))
        block = block.next()
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown -> Document
# ---------------------------------------------------------------------------

def _has_closer(line: str, token: str, start: int) -> bool:
    """True if an unescaped ``token`` occurs at/after ``start`` on the line."""
    i, n = start, len(line)
    while i < n:
        if line[i] == "\\":
            i += 2
            continue
        if line.startswith(token, i):
            return True
        i += 1
    return False


def _parse_line_runs(line: str) -> list[tuple[str, dict]]:
    """Split one line into (text, flags) runs by toggling inline markers.

    An emphasis marker only *opens* a span when a matching closer exists later
    on the line; otherwise it is treated as literal text. This keeps stray
    markers in legacy plain-text notes (``2 * 3``, ``* bullet``) from styling
    the rest of the line.
    """
    runs: list[tuple[str, dict]] = []
    buf: list[str] = []
    bold = italic = strike = underline = False
    i, n = 0, len(line)

    def flush() -> None:
        if buf:
            runs.append(("".join(buf), {
                "bold": bold, "italic": italic, "code": False,
                "strike": strike, "underline": underline,
            }))
            buf.clear()

    while i < n:
        ch = line[i]

        if ch == "\\" and i + 1 < n and line[i + 1] in _SPECIAL:
            buf.append(line[i + 1])
            i += 2
            continue

        if ch == "`":
            # Code span: matched by a run of the same number of backticks.
            fence_len = 1
            while i + fence_len < n and line[i + fence_len] == "`":
                fence_len += 1
            fence = "`" * fence_len
            close = line.find(fence, i + fence_len)
            if close != -1:
                flush()
                inner = line[i + fence_len:close]
                if inner.startswith(" ") and inner.endswith(" ") and inner.strip():
                    inner = inner[1:-1]
                runs.append((inner, {
                    "bold": bold, "italic": italic, "code": True,
                    "strike": strike, "underline": underline,
                }))
                i = close + fence_len
                continue
            buf.append(ch)
            i += 1
            continue

        if line.startswith("~~", i) and (strike or _has_closer(line, "~~", i + 2)):
            flush()
            strike = not strike
            i += 2
            continue

        if line.startswith("++", i) and (underline or _has_closer(line, "++", i + 2)):
            flush()
            underline = not underline
            i += 2
            continue

        if line.startswith("**", i) and (bold or _has_closer(line, "**", i + 2)):
            flush()
            bold = not bold
            i += 2
            continue

        if ch == "*" and (italic or _has_closer(line, "*", i + 1)):
            flush()
            italic = not italic
            i += 1
            continue

        buf.append(ch)
        i += 1

    flush()
    return runs


def apply_markdown(doc: QTextDocument, markdown: str, bold_color: Optional[QColor] = None,
                   block_spacing: float = 0.0) -> None:
    """Replace ``doc`` contents with the parsed Markdown, styling inline runs.

    ``bold_color`` tints bold runs to match the live editor toggle, so bold
    looks the same whether just typed or reloaded from storage.

    ``block_spacing`` is a purely visual gap (in pixels) added above each block
    — i.e. between actual line breaks, not wrapped lines. It is injected by the
    view; since new blocks inherit the current block format, typing Enter keeps
    the same spacing without any further work.
    """
    doc.clear()
    cursor = QTextCursor(doc)
    cursor.beginEditBlock()
    block_format = QTextBlockFormat()
    block_format.setTopMargin(block_spacing)
    cursor.setBlockFormat(block_format)
    for line_index, line in enumerate(markdown.split("\n")):
        if line_index > 0:
            cursor.insertBlock(block_format)
        for text, flags in _parse_line_runs(line):
            cursor.insertText(text, make_format(**flags, bold_color=bold_color))
    cursor.endEditBlock()


def fragment_to_markdown(fragment) -> str:
    """Serialize a selected QTextDocumentFragment to inline Markdown."""
    tmp = QTextDocument()
    QTextCursor(tmp).insertFragment(fragment)
    return document_to_markdown(tmp)
