# Anki HTML Rendering Fix

## Issue

Cards with HTML content (like the TSP card) showed empty answers in notifications, even though the field extraction was working correctly.

## Root Cause

**Mismatch between content format and renderer:**

1. **Anki cards use HTML** - Fields contain `<p>`, `<br>`, `&nbsp;`, etc.
2. **Notification toast was set to Markdown** - `Qt.TextFormat.MarkdownText`
3. **Result:** HTML tags weren't rendered, leaving blank or invisible content

## Investigation

### Debug Output

For the TSP card:
```
Front: '<p>The Traveling Salesman Problem (TSP) seeks to</p>'
Back: '<p>find the shortest possible route...</p>'
```

Field extraction was **working correctly** (template parsing succeeded, fields identified, values extracted). The issue was in the display layer.

### Confirmation

- Template extraction: ✓ Correct
- Field values: ✓ Present (222 chars)
- HTML stripped text: ✓ Has visible content
- Notification display: ✗ Not rendering HTML

## Solution

Changed notification toast text format from **Markdown** to **RichText** (HTML):

**File:** `gui/widgets/notification_toast.py` (line 199)

**Before:**
```python
self._message_label.setTextFormat(Qt.TextFormat.MarkdownText)
```

**After:**
```python
self._message_label.setTextFormat(Qt.TextFormat.RichText)  # Support HTML from Anki cards
```

## Qt.TextFormat Options

- `PlainText` - No formatting, literal text
- `RichText` - HTML subset (Qt HTML4 support)
- `MarkdownText` - Markdown formatting
- `AutoText` - Auto-detect format

**RichText** supports common HTML tags:
- `<p>`, `<br>`, `<div>`, `<span>`
- `<b>`, `<i>`, `<u>`, `<s>`
- `<ul>`, `<ol>`, `<li>`
- `<img>` (limited)
- HTML entities (`&nbsp;`, `&amp;`, etc.)

## Impact

**Positive:**
- ✅ Anki cards with HTML now display correctly
- ✅ Formatting preserved (bold, italic, lists, etc.)
- ✅ HTML entities render properly (&nbsp; → space)
- ✅ No changes needed to Anki card content

**Potential Issues:**
- If any non-Anki notifications were using Markdown syntax, they may not render correctly
- HTML must be valid (unclosed tags may cause rendering issues)

## Testing

**Test Cards:**
1. TSP card - Now shows: "find the shortest possible route..."
2. Cards with `<br>` tags - Line breaks render
3. Cards with formatting - Bold/italic preserved
4. Cards with HTML entities - Render correctly

**Verification:**
```bash
# Create an Anki reminder and trigger it
# Verify HTML content displays properly in notification toast
```

## Alternative Considered

**Auto-detect format** (`Qt.TextFormat.AutoText`):
- Pros: Would handle both HTML and Markdown
- Cons: Less predictable, may misdetect format

Chose **RichText** for explicitness since Anki always uses HTML.

---

**Status:** ✅ Fixed
**Files Changed:** `gui/widgets/notification_toast.py`
**Lines Changed:** 1 line
**Testing:** Verified with TSP card and other HTML cards
**Date:** 2026-02-04
