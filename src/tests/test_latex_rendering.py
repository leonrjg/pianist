#!/usr/bin/env python3
"""
Test LaTeX rendering in Anki cards.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.integrations.anki_service import AnkiService, AnkiConnectError


def test_latex_card(search_text):
    """Test LaTeX rendering on a specific card."""
    print(f"Testing LaTeX rendering for card: '{search_text}'")
    print("=" * 80)

    try:
        # Search for the card
        query = f'"{search_text}"'
        card_ids = AnkiService._invoke("findCards", {"query": query})

        if not card_ids:
            print(f"No cards found with text: {search_text}")
            return

        print(f"Found {len(card_ids)} card(s)")

        # Get card info
        card_id = card_ids[0]
        cards_info = AnkiService._invoke("cardsInfo", {"cards": [card_id]})
        card_info = cards_info[0]

        # Extract fields
        model_name = card_info.get("modelName", "")
        card_ord = card_info.get("ord", 0)
        fields = card_info.get("fields", {})

        front_fields, back_fields = AnkiService._get_field_extraction_strategy(model_name, card_ord)
        front = AnkiService._extract_field_values(fields, front_fields)
        back = AnkiService._extract_field_values(fields, back_fields)

        print("\n" + "=" * 80)
        print("BEFORE LaTeX PROCESSING:")
        print("=" * 80)
        print(f"\nFront (raw):\n{front[:200]}...")
        print(f"\nBack (raw):\n{back[:200]}...")

        # Process LaTeX
        front_processed = AnkiService._process_latex(front)
        back_processed = AnkiService._process_latex(back)

        print("\n" + "=" * 80)
        print("AFTER LaTeX PROCESSING:")
        print("=" * 80)
        print(f"\nFront (processed):\n{front_processed[:300]}...")
        print(f"\nBack (processed):\n{back_processed[:300]}...")

        # Check for LaTeX conversion
        print("\n" + "=" * 80)
        print("CONVERSION ANALYSIS:")
        print("=" * 80)

        def count_latex(text):
            import re
            patterns = [r'\\\[', r'\\\(', r'\$\$', r'(?<!\$)\$(?!\$)']
            count = sum(len(re.findall(p, text)) for p in patterns)
            return count

        def count_images(text):
            import re
            return len(re.findall(r'<img src="data:image/png', text))

        front_latex = count_latex(front)
        back_latex = count_latex(back)
        front_images = count_images(front_processed)
        back_images = count_images(back_processed)

        print(f"\nFront:")
        print(f"  LaTeX expressions found: {front_latex}")
        print(f"  Images created: {front_images}")
        print(f"  {'✓ Converted' if front_images > 0 else '- No LaTeX found'}")

        print(f"\nBack:")
        print(f"  LaTeX expressions found: {back_latex}")
        print(f"  Images created: {back_images}")
        print(f"  {'✓ Converted' if back_images > 0 else '- No LaTeX found'}")

        if front_images + back_images > 0:
            print(f"\n✓ LaTeX rendering successful!")
            print(f"  Total formulas rendered: {front_images + back_images}")
        else:
            print(f"\n⚠️  No LaTeX found or conversion failed")

    except AnkiConnectError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run LaTeX rendering test."""
    print("=" * 80)
    print("LATEX RENDERING TEST")
    print("=" * 80)

    if not AnkiService.test_connection():
        print("\n✗ Cannot connect to Anki. Make sure Anki is running.")
        return 1

    print("\n✓ Connected to AnkiConnect")

    # Test with user's card
    if len(sys.argv) > 1:
        search_text = " ".join(sys.argv[1:])
    else:
        search_text = "If X and Y are not independent"

    test_latex_card(search_text)

    print("\n" + "=" * 80)
    print("Note: The processed HTML contains base64-encoded images.")
    print("These will render in the notification toast as visual formulas.")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
