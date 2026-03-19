#!/usr/bin/env python3
"""
Test what the actual AnkiCard object looks like when fetched.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.integrations.anki_service import AnkiService, AnkiConnectError


def test_fetch_tsp_card():
    """Fetch the TSP card and show what we'd send to the notification."""
    try:
        # Search for the card
        query = '"The Traveling Salesman Problem (TSP) seeks to"'
        card_ids = AnkiService._invoke("findCards", {"query": query})

        if not card_ids:
            print("Card not found!")
            return

        # Fetch it the same way the app would
        card_id = card_ids[0]
        cards_info = AnkiService._invoke("cardsInfo", {"cards": [card_id]})
        card_info = cards_info[0]

        # Simulate what get_random_card does
        model_name = card_info.get("modelName", "")
        card_ord = card_info.get("ord", 0)
        fields = card_info.get("fields", {})

        front_fields, back_fields = AnkiService._get_field_extraction_strategy(model_name, card_ord)
        front = AnkiService._extract_field_values(fields, front_fields)
        back = AnkiService._extract_field_values(fields, back_fields)

        print("=" * 80)
        print("WHAT GETS SENT TO NOTIFICATION:")
        print("=" * 80)

        print(f"\nFront (as string):")
        print(repr(front))
        print(f"\nFront (as displayed):")
        print(front)

        print(f"\n{'-' * 80}")

        print(f"\nBack (as string):")
        print(repr(back))
        print(f"\nBack (as displayed):")
        print(back)

        print(f"\n{'-' * 80}")

        # Check if there's actual text content
        import re
        front_text = re.sub(r'<[^>]+>', '', front)  # Strip HTML tags
        back_text = re.sub(r'<[^>]+>', '', back)

        print(f"\nFront (HTML stripped):")
        print(repr(front_text))

        print(f"\nBack (HTML stripped):")
        print(repr(back_text))

        print("\n" + "=" * 80)
        print("ANALYSIS:")
        print("=" * 80)

        if front and not front_text.strip():
            print("⚠️  Front has HTML but no visible text after stripping tags")

        if back and not back_text.strip():
            print("⚠️  Back has HTML but no visible text after stripping tags")

        if back and back_text.strip():
            print(f"✓ Back has visible text: {len(back_text.strip())} characters")
            print(f"  Preview: {back_text.strip()[:100]}...")

        # Check for special characters
        if back and '&nbsp;' in back:
            print(f"ℹ️  Back contains HTML entities (&nbsp;)")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_fetch_tsp_card()
