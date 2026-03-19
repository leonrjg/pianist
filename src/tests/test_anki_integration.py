#!/usr/bin/env python3
"""
Test script for AnkiConnect integration.

This script tests the basic functionality of the Anki integration.
Before running:
1. Ensure Anki is running
2. Ensure AnkiConnect add-on is installed (code: 2055492159)
3. Have at least one deck with cards
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.integrations.anki_service import AnkiService, AnkiConnectError


def test_connection():
    """Test connection to AnkiConnect."""
    print("Testing connection to AnkiConnect...")
    if AnkiService.test_connection():
        print("✓ Connection successful")
        return True
    else:
        print("✗ Connection failed")
        print("\nMake sure:")
        print("1. Anki is running")
        print("2. AnkiConnect add-on is installed (Tools → Add-ons → Get Add-ons... → code: 2055492159)")
        return False


def test_get_decks():
    """Test retrieving deck names."""
    print("\nTesting deck retrieval...")
    try:
        decks = AnkiService.get_deck_names()
        print(f"✓ Found {len(decks)} deck(s):")
        for deck in decks:
            print(f"  - {deck}")
        return decks
    except AnkiConnectError as e:
        print(f"✗ Error: {e}")
        return []


def test_get_random_card(deck_name):
    """Test getting a random card from a deck."""
    print(f"\nTesting card retrieval from deck '{deck_name}'...")
    try:
        card = AnkiService.get_card(deck_name, reminder_id=999)
        print("✓ Card retrieved successfully:")
        print(f"  Card ID: {card.card_id}")
        print(f"  Deck: {card.deck_name}")
        print(f"  Front: {card.front[:100]}..." if len(card.front) > 100 else f"  Front: {card.front}")
        print(f"  Back: {card.back[:100]}..." if len(card.back) > 100 else f"  Back: {card.back}")
        return card
    except AnkiConnectError as e:
        print(f"✗ Error: {e}")
        return None


def test_cache():
    """Test card caching."""
    print("\nTesting card cache...")
    cached_card = AnkiService.get_cached_card(999)
    if cached_card:
        print(f"✓ Card cached successfully (ID: {cached_card.card_id})")
        AnkiService.clear_cache(999)
        print("✓ Cache cleared successfully")
        return True
    else:
        print("✗ Card not found in cache")
        return False


def test_submit_rating(card):
    """Test submitting a rating (dry run - won't actually submit)."""
    print(f"\nTesting rating submission for card {card.card_id}...")
    print("Note: This will actually answer the card in Anki!")
    response = input("Do you want to proceed? (y/n): ")

    if response.lower() != 'y':
        print("Skipping rating test")
        return False

    try:
        # Submit "Good" rating (ease=3)
        success = AnkiService.submit_rating(card.card_id, ease=3)
        if success:
            print("✓ Rating submitted successfully (Good)")
            return True
        else:
            print("✗ Rating submission failed")
            return False
    except AnkiConnectError as e:
        print(f"✗ Error: {e}")
        return False
    except ValueError as e:
        print(f"✗ Invalid ease value: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("AnkiConnect Integration Test")
    print("=" * 60)

    # Test connection
    if not test_connection():
        return 1

    # Test getting decks
    decks = test_get_decks()
    if not decks:
        return 1

    # Test getting a random card from first deck
    deck_name = decks[0]
    card = test_get_random_card(deck_name)
    if not card:
        return 1

    # Test cache
    test_cache()

    # Test rating submission (optional)
    test_submit_rating(card)

    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
