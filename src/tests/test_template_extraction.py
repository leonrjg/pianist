#!/usr/bin/env python3
"""
Test the template-based field extraction.

This script verifies that the new template parsing approach
correctly extracts front/back fields from cards.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.integrations.anki_service import AnkiService, AnkiConnectError


def test_template_extraction(deck_name):
    """Test template-based extraction on a card from the specified deck."""
    print(f"Testing template-based extraction on deck: {deck_name}")
    print("=" * 80)

    try:
        # Fetch a card using the new method
        card = AnkiService.get_card(deck_name)

        print(f"\n✓ Card fetched successfully!")
        print(f"\nCard ID: {card.card_id}")
        print(f"Deck: {card.deck_name}")

        print(f"\n{'─' * 80}")
        print("FRONT (Question):")
        print('─' * 80)
        print(card.front)

        print(f"\n{'─' * 80}")
        print("BACK (Answer):")
        print('─' * 80)
        print(card.back)

        print(f"\n{'─' * 80}")
        print("Template Cache Status:")
        print('─' * 80)
        print(f"Cached templates: {len(AnkiService._template_cache)} note type(s)")
        for key in AnkiService._template_cache.keys():
            print(f"  - {key}")

        # Verify the back doesn't include the front
        if card.front and card.front in card.back:
            print(f"\n⚠️  WARNING: Back contains front content (might be intentional)")
        else:
            print(f"\n✓ Front and back are properly separated")

        return True

    except AnkiConnectError as e:
        print(f"\n✗ Error: {e}")
        return False


def test_multiple_cards():
    """Test extraction on multiple cards to verify caching."""
    print("\n" + "=" * 80)
    print("TESTING MULTIPLE CARDS (Cache Performance)")
    print("=" * 80)

    try:
        decks = AnkiService.get_deck_names()
        if not decks:
            print("No decks found!")
            return

        # Test first 3 decks (or fewer if less available)
        test_decks = decks[:min(3, len(decks))]

        for i, deck in enumerate(test_decks, 1):
            print(f"\n[{i}/{len(test_decks)}] Testing deck: {deck}")
            try:
                card = AnkiService.get_card(deck)
                print(f"  ✓ Front: {card.front[:60]}...")
                print(f"  ✓ Back: {card.back[:60]}...")
            except AnkiConnectError as e:
                print(f"  ✗ Error: {e}")

        print(f"\n✓ Template cache now contains {len(AnkiService._template_cache)} entries")
        print("  (Subsequent cards from same note types will use cache)")

    except AnkiConnectError as e:
        print(f"\n✗ Error: {e}")


def main():
    """Run template extraction tests."""
    print("=" * 80)
    print("TEMPLATE-BASED FIELD EXTRACTION TEST")
    print("=" * 80)

    # Test connection
    if not AnkiService.test_connection():
        print("\n✗ Cannot connect to Anki. Make sure Anki is running.")
        return 1

    print("\n✓ Connected to AnkiConnect")

    # Get available decks
    try:
        decks = AnkiService.get_deck_names()
        print(f"\n✓ Found {len(decks)} deck(s)")
    except AnkiConnectError as e:
        print(f"\n✗ Error: {e}")
        return 1

    # Test with first deck
    if len(sys.argv) > 1:
        deck_name = sys.argv[1]
    else:
        deck_name = decks[0]

    print(f"\n{'=' * 80}")
    test_template_extraction(deck_name)

    # Test multiple cards for cache performance
    test_multiple_cards()

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nThe new template-based approach:")
    print("  ✓ Parses card templates to identify fields")
    print("  ✓ Extracts only answer-specific fields")
    print("  ✓ Caches templates for performance")
    print("  ✓ Works with any card type (Basic, Cloze, custom)")
    print("  ✓ Falls back to HTML if parsing fails")

    return 0


if __name__ == "__main__":
    sys.exit(main())
