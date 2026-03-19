# Anki Integration Migration Guide

## Overview

The Anki integration has been upgraded from a mock implementation to a real AnkiConnect integration. This document outlines the changes and migration steps.

## Changes Made

### 1. Core Service (`anki_service.py`)

**Before:**
- Used mock card data stored in dictionaries
- No actual connection to Anki
- Printed mock messages to console

**After:**
- Real HTTP connection to AnkiConnect API at `localhost:8765`
- Fetches actual cards from Anki decks
- Submits ratings that update Anki's scheduling
- Comprehensive error handling with custom `AnkiConnectError` exception
- New utility methods: `get_deck_names()` and `test_connection()`

### 2. Action Handler (`actions.py`)

**Updated:**
- Enhanced error handling to catch `AnkiConnectError` separately
- Better error messages for users when Anki connection fails
- Prevents toast crashes if rating submission fails

### 3. Dependencies (`requirements.txt`)

**Added:**
- `requests==2.32.3` - HTTP library for AnkiConnect communication

### 4. New Files

- `test_anki_integration.py` - Comprehensive test script
- `README.md` - Full documentation
- `MIGRATION.md` - This file

### 5. Updated Files

- `__init__.py` - Now exports `AnkiConnectError`

## API Compatibility

### Methods Unchanged

All existing method signatures remain the same:

```python
AnkiService.get_card(deck_name, reminder_id=None)  # ✓ Compatible
AnkiService.get_cached_card(reminder_id)  # ✓ Compatible
AnkiService.submit_rating(card_id, ease)  # ✓ Compatible
AnkiService.clear_cache(reminder_id)  # ✓ Compatible
```

### New Methods

```python
AnkiService.get_deck_names()                               # ✓ New
AnkiService.test_connection()                              # ✓ New
```

### Exception Handling

**Before:**

```python
try:
    card = AnkiService.get_card("Spanish")
except Exception as e:
    print(f"Error: {e}")
```

**After:**

```python
from core.integrations.anki_service import AnkiConnectError

try:
    card = AnkiService.get_card("Spanish")
except AnkiConnectError as e:
    # Anki-specific errors (connection, empty deck, etc.)
    print(f"Anki error: {e}")
except Exception as e:
    # Other unexpected errors
    print(f"Unexpected error: {e}")
```

## Migration Steps

### For End Users

1. **Install AnkiConnect**
   ```
   1. Open Anki
   2. Tools → Add-ons → Get Add-ons...
   3. Enter code: 2055492159
   4. Restart Anki
   ```

2. **Install Dependencies**
   ```bash
   cd src
   pip install -r requirements.txt
   ```

3. **Verify Setup**
   ```bash
   python test_anki_integration.py
   ```

4. **Keep Anki Running**
   - Anki must be running in the background for the integration to work
   - You can verify by visiting http://127.0.0.1:8765 in your browser

### For Developers

1. **Update Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Test Your Code**
   - Run existing tests to ensure compatibility
   - All existing code using `AnkiService` should work without changes
   - Add error handling for `AnkiConnectError` in new code

3. **Update Error Handling (Optional but Recommended)**
   ```python
   # Old style (still works)
   try:
       card = AnkiService.get_card(deck_name)
   except Exception as e:
       handle_error(e)

   # New style (recommended)
   from core.integrations.anki_service import AnkiConnectError

   try:
       card = AnkiService.get_card(deck_name)
   except AnkiConnectError as e:
       # User-friendly error (Anki not running, empty deck, etc.)
       show_user_message(str(e))
   except Exception as e:
       # Unexpected error - log for debugging
       logger.error(f"Unexpected error: {e}")
   ```

## Breaking Changes

**None!** The API is fully backward compatible.

However, behavior changes:
- **Before:** Always returned a card (from mock data)
- **After:** Raises `AnkiConnectError` if Anki is not running or deck is empty

## Testing Checklist

- [ ] Install `requests` library
- [ ] Install AnkiConnect add-on in Anki
- [ ] Run `test_anki_integration.py` successfully
- [ ] Create a reminder with action type `anki_card`
- [ ] Trigger the reminder and verify card displays
- [ ] Submit a rating and verify it updates in Anki
- [ ] Test with Anki closed (should show error message)
- [ ] Test with empty deck (should show error message)
- [ ] Test with invalid deck name (should show error message)

## Rollback Plan

If you need to rollback to the mock implementation:

1. Checkout the previous version:
   ```bash
   git checkout <previous-commit> -- core/integrations/anki_service.py
   ```

2. Revert requirements.txt:
   ```bash
   git checkout <previous-commit> -- requirements.txt
   ```

3. The old mock data will be restored

## Common Issues

### Issue: "Could not connect to Anki"

**Solution:** Ensure Anki is running and AnkiConnect is installed.

### Issue: "No cards found in deck"

**Solution:** Check deck name spelling (case-sensitive) and ensure deck has cards.

### Issue: Import error for `requests`

**Solution:** Run `pip install -r requirements.txt`

### Issue: "AnkiConnect error: permission denied"

**Solution:** Check AnkiConnect settings (Tools → Add-ons → AnkiConnect → Config)

## Performance Considerations

- Card fetching: ~50-100ms (fast)
- Rating submission: ~50-100ms (fast)
- Timeout: 5 seconds (configurable)
- Cards are cached per reminder (no duplicate fetches)

## Security Notes

- AnkiConnect only listens on localhost (127.0.0.1)
- No data is sent over the internet
- Optional API key authentication available (see AnkiConnect docs)

## Support

For issues or questions:
1. Check the README.md for documentation
2. Run test_anki_integration.py for diagnostics
3. Verify AnkiConnect is working: http://127.0.0.1:8765
4. Check Anki logs: Help → About → Copy Debug Info
