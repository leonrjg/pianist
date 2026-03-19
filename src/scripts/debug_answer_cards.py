#!/usr/bin/env python3
"""
Debug what happens when we try to answer a card.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.integrations.anki_service import AnkiService, AnkiConnectError

def test_answer_card():
    """Try to answer a random card and see what error we get."""
    print("Testing answerCards with a random card...")
    print("=" * 80)

    try:
        # Get a random card
        decks = AnkiService.get_deck_names()
        deck = decks[0]

        query = f'deck:"{deck}"'
        card_ids = AnkiService._invoke("findCards", {"query": query})

        if not card_ids:
            print("No cards found")
            return

        card_id = card_ids[0]
        print(f"Card ID: {card_id}")
        print(f"Deck: {deck}")

        # Try to answer it
        print(f"\nAttempting to answer card with ease=3 (Good)...")

        result = AnkiService._invoke("answerCards", {
            "answers": [{"cardId": card_id, "ease": 3}]
        })

        print(f"✓ Success! Result: {result}")

    except AnkiConnectError as e:
        print(f"\n✗ AnkiConnect Error:")
        print(f"  {e}")
        print(f"\nThis is expected - answerCards requires:")
        print(f"  1. Anki GUI review session active")
        print(f"  2. This specific card at top of review queue")
        print(f"\nWe need an alternative approach for standalone reviewing.")

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_answer_card()
