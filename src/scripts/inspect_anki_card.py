#!/usr/bin/env python3
"""
Inspect AnkiConnect card structure to understand field mapping.

This script fetches a card and shows ALL available information
to help determine the correct way to extract front/back content.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.integrations.anki_service import AnkiService, AnkiConnectError


def inspect_card(deck_name):
    """Fetch and display full card structure."""
    print(f"Inspecting card from deck: {deck_name}\n")
    print("=" * 80)

    try:
        # Get card IDs
        query = f'deck:"{deck_name}"'
        card_ids = AnkiService._invoke("findCards", {"query": query})

        if not card_ids:
            print(f"No cards found in deck '{deck_name}'")
            return

        # Get info for first card
        cards_info = AnkiService._invoke("cardsInfo", {"cards": [card_ids[0]]})
        card_info = cards_info[0]

        print("FULL CARD INFO:")
        print(json.dumps(card_info, indent=2, ensure_ascii=False))
        print("\n" + "=" * 80)

        # Extract key information
        print("\nKEY INFORMATION:")
        print(f"Card ID: {card_info['cardId']}")
        print(f"Model Name (Note Type): {card_info['modelName']}")
        print(f"Deck Name: {card_info['deckName']}")
        print(f"Card Ordinal: {card_info.get('ord', 'N/A')}")

        print("\n" + "-" * 80)
        print("FIELDS (raw values):")
        fields = card_info.get('fields', {})
        for field_name, field_data in fields.items():
            print(f"  {field_name}: {field_data['value'][:100]}...")

        print("\n" + "-" * 80)
        print("RENDERED CONTENT:")
        print(f"Question (front): {card_info.get('question', 'N/A')[:200]}...")
        print(f"\nAnswer (back): {card_info.get('answer', 'N/A')[:200]}...")

        print("\n" + "=" * 80)
        print("\nNOW CHECKING MODEL INFORMATION...")

        # Get model (note type) information
        model_names = AnkiService._invoke("modelNames")
        print(f"\nAvailable models: {model_names}")

        # Get field names for this model
        model_name = card_info['modelName']
        field_names = AnkiService._invoke("modelFieldNames", {"modelName": model_name})
        print(f"\nField names for '{model_name}': {field_names}")

        # Get templates for this model
        try:
            templates = AnkiService._invoke("modelTemplates", {"modelName": model_name})
            print(f"\nTemplates for '{model_name}':")
            print(json.dumps(templates, indent=2))
        except:
            print("\nCould not retrieve templates")

    except AnkiConnectError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_anki_card.py <deck_name>")
        print("\nAvailable decks:")
        try:
            decks = AnkiService.get_deck_names()
            for deck in decks:
                print(f"  - {deck}")
        except AnkiConnectError as e:
            print(f"Error: {e}")
        sys.exit(1)

    deck_name = sys.argv[1]
    inspect_card(deck_name)
