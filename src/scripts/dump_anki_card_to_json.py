#!/usr/bin/env python3
"""
Dump complete AnkiConnect card data to JSON file for review.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from core.integrations.anki_service import AnkiService, AnkiConnectError


def dump_card_data():
    """Fetch card and write complete data to JSON file."""
    output_file = Path(__file__).parent.parent / "anki_card_dump.json"

    try:
        # Test connection
        if not AnkiService.test_connection():
            print("Error: Cannot connect to Anki. Make sure Anki is running.")
            return

        # Get decks
        decks = AnkiService.get_deck_names()
        print(f"Found {len(decks)} deck(s): {decks}")

        if not decks:
            print("No decks found!")
            return

        # Use first deck
        deck_name = decks[0]
        print(f"\nUsing deck: {deck_name}")

        # Find cards
        query = f'deck:"{deck_name}"'
        card_ids = AnkiService._invoke("findCards", {"query": query})

        if not card_ids:
            print(f"No cards found in deck '{deck_name}'")
            return

        print(f"Found {len(card_ids)} card(s)")

        # Get first card info
        card_id = card_ids[0]
        print(f"Fetching card ID: {card_id}")

        cards_info = AnkiService._invoke("cardsInfo", {"cards": [card_id]})
        card_info = cards_info[0]

        # Get model templates
        model_name = card_info["modelName"]
        print(f"Model: {model_name}")

        templates = AnkiService._invoke("modelTemplates", {"modelName": model_name})
        field_names = AnkiService._invoke("modelFieldNames", {"modelName": model_name})

        # Compile all data
        dump_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "deck_name": deck_name,
                "total_cards_in_deck": len(card_ids),
                "note": "This is a complete dump of a single card's data from AnkiConnect"
            },
            "card_info": card_info,
            "model_info": {
                "model_name": model_name,
                "field_names": field_names,
                "templates": templates
            }
        }

        # Write to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dump_data, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Data written to: {output_file}")
        print(f"\nFile contains:")
        print(f"  - Complete card info (fields, question, answer, etc.)")
        print(f"  - Model templates (Front/Back templates)")
        print(f"  - Field names for the note type")

        # Print summary
        print(f"\nQuick Summary:")
        print(f"  Card ID: {card_info['cardId']}")
        print(f"  Model: {card_info['modelName']}")
        print(f"  Deck: {card_info['deckName']}")
        print(f"  Fields: {list(card_info['fields'].keys())}")
        print(f"  Template names: {list(templates.keys())}")

    except AnkiConnectError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    dump_card_data()
