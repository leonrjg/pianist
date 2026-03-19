# Anki Integration

This module provides integration with Anki via the AnkiConnect add-on, enabling your application to fetch flashcards and submit reviews directly to Anki.

## Setup

### 1. Install Anki

Download and install Anki from [https://apps.ankiweb.net/](https://apps.ankiweb.net/)

### 2. Install AnkiConnect Add-on

1. Open Anki
2. Navigate to: **Tools → Add-ons → Get Add-ons...**
3. Enter the code: **2055492159**
4. Click **OK** and restart Anki

### 3. Verify Installation

You can verify AnkiConnect is running by:
- Opening your browser and visiting `http://127.0.0.1:8765`
- You should see the message "AnkiConnect"

### 4. Install Python Dependencies

```bash
cd src
pip install -r requirements.txt
```

## Usage

### Basic Example

```python
from core.integrations.anki_service import AnkiService, AnkiConnectError

# Test connection
if AnkiService.test_connection():
    print("Connected to Anki!")

# Get list of decks
decks = AnkiService.get_deck_names()
print(f"Available decks: {decks}")

# Get a random card from a deck
try:
    card = AnkiService.get_card("Spanish", reminder_id=1)
    print(f"Question: {card.front}")
    print(f"Answer: {card.back}")

    # Submit a rating (1=Again, 2=Hard, 3=Good, 4=Easy)
    AnkiService.submit_rating(card.card_id, ease=3)

except AnkiConnectError as e:
    print(f"Error: {e}")
```

### Testing

Run the test script to verify your setup:

```bash
cd src
python test_anki_integration.py
```

## API Reference

### AnkiService

#### `test_connection() -> bool`
Test if AnkiConnect is accessible.

**Returns:** True if connection successful, False otherwise.

#### `get_deck_names() -> List[str]`
Get list of all deck names.

**Returns:** List of deck names.

**Raises:** `AnkiConnectError` if request fails.

#### `get_random_card(deck_name: str, reminder_id: Optional[int] = None) -> AnkiCard`
Get a random card from the specified deck.

**Parameters:**
- `deck_name`: Name of the Anki deck
- `reminder_id`: Optional reminder ID to cache card for later retrieval

**Returns:** AnkiCard object with card details.

**Raises:** `AnkiConnectError` if connection fails or deck is empty.

#### `get_cached_card(reminder_id: int) -> Optional[AnkiCard]`
Get previously fetched card for a reminder.

**Parameters:**
- `reminder_id`: ID of the reminder

**Returns:** Cached AnkiCard or None if not found.

#### `submit_rating(card_id: int, ease: int) -> bool`
Submit rating to Anki.

**Parameters:**
- `card_id`: ID of the card being rated
- `ease`: Rating value
  - 1 = Again (forgot)
  - 2 = Hard (difficult to remember)
  - 3 = Good (remembered correctly)
  - 4 = Easy (very easy to remember)

**Returns:** True if successful.

**Raises:**
- `AnkiConnectError` if submission fails
- `ValueError` if ease is not between 1 and 4

#### `clear_cache(reminder_id: int)`
Clear cached card for a reminder.

**Parameters:**
- `reminder_id`: ID of the reminder

### AnkiCard

Dataclass representing an Anki flashcard.

**Attributes:**
- `card_id` (int): Unique card identifier
- `deck_name` (str): Name of the deck containing the card
- `front` (str): Front side of the card (question)
- `back` (str): Back side of the card (answer)

### AnkiConnectError

Exception raised for AnkiConnect API errors.

**Common Causes:**
- Anki is not running
- AnkiConnect add-on is not installed
- Network connectivity issues
- Invalid deck name
- Empty deck

## Integration with Reminders

The Anki integration is automatically used when you create a reminder with:
- **Action type:** `anki_card`
- **Payload:** Name of the Anki deck (e.g., "Spanish", "Programming")

When the reminder triggers:
1. A random card is fetched from the specified deck
2. The question is displayed in a notification toast
3. User clicks "Show Answer" to reveal the back of the card
4. User rates the card (Again/Hard/Good/Easy)
5. Rating is submitted to Anki and the card's schedule is updated

## Troubleshooting

### "Could not connect to Anki"
- Ensure Anki is running in the background
- Verify AnkiConnect is installed: Tools → Add-ons → Browse Add-ons
- Check that AnkiConnect is accessible at http://127.0.0.1:8765

### "No cards found in deck"
- Verify the deck name is correct (case-sensitive)
- Ensure the deck contains cards
- Check that cards aren't all suspended

### "Request to AnkiConnect timed out"
- Anki might be busy or frozen
- Try restarting Anki
- Check system resources

### "Invalid response format from AnkiConnect"
- AnkiConnect add-on might be outdated
- Update the add-on: Tools → Add-ons → Check for Updates
- Ensure you're using AnkiConnect version 6 or later

## Configuration

### Default Settings

- **URL:** `http://127.0.0.1:8765`
- **Version:** 6
- **Timeout:** 5 seconds

### Custom Configuration

You can modify these settings in `anki_service.py`:

```python
class AnkiService:
    ANKICONNECT_URL = "http://127.0.0.1:8765"  # Change if using custom port
    ANKICONNECT_VERSION = 6
    REQUEST_TIMEOUT = 5  # Increase if you have a slow system
```

## Advanced Usage

### Custom Queries

The integration uses Anki's search syntax. You can customize the query in `get_random_card()`:

```python
# Get only due cards from a specific deck
query = f'deck:"{deck_name}" is:due'

# Get new cards only
query = f'deck:"{deck_name}" is:new'

# Get cards with specific tags
query = f'deck:"{deck_name}" tag:vocabulary'
```

See [Anki's search documentation](https://docs.ankiweb.net/searching.html) for more query options.

## Security

- AnkiConnect runs locally on `127.0.0.1` (localhost only)
- No external network connections are made
- API key authentication is supported but optional
- See [AnkiConnect documentation](https://git.sr.ht/~foosoft/anki-connect) for security options

## Performance

- Card queries are fast (typically < 100ms)
- Cards are cached per reminder to avoid duplicate fetches
- Timeout set to 5 seconds to prevent hanging
- Uses persistent HTTP connections via `requests` library

## Future Enhancements

Potential features that could be added:
- Support for filtered decks
- Study statistics retrieval
- Custom card templates
- Batch card operations
- API key authentication support
- Configurable card selection strategies (due cards only, weighted by interval, etc.)
