#!/usr/bin/env python3
"""
Debug a specific card to understand why the answer is empty.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.integrations.anki_service import AnkiService, AnkiConnectError


def debug_card_by_front_text(search_text):
    """Find and debug a card by searching for text in the front."""
    print(f"Searching for card with front containing: '{search_text}'")
    print("=" * 80)

    try:
        # Search for cards with this text
        query = f'"{search_text}"'
        card_ids = AnkiService._invoke("findCards", {"query": query})

        if not card_ids:
            print(f"No cards found with text: {search_text}")
            return

        print(f"\nFound {len(card_ids)} card(s)")

        # Get info for first matching card
        card_id = card_ids[0]
        print(f"Analyzing card ID: {card_id}\n")

        cards_info = AnkiService._invoke("cardsInfo", {"cards": [card_id]})
        card_info = cards_info[0]

        # Display full card info
        print("=" * 80)
        print("FULL CARD INFO:")
        print("=" * 80)
        print(json.dumps(card_info, indent=2, ensure_ascii=False))

        # Extract key information
        model_name = card_info.get("modelName", "")
        card_ord = card_info.get("ord", 0)
        fields = card_info.get("fields", {})

        print("\n" + "=" * 80)
        print("FIELD ANALYSIS:")
        print("=" * 80)
        print(f"Model Name: {model_name}")
        print(f"Card Ordinal: {card_ord}")
        print(f"\nFields in card:")
        for field_name, field_data in fields.items():
            value = field_data.get('value', '')
            print(f"  {field_name}:")
            print(f"    Value: {repr(value)[:200]}")
            print(f"    Length: {len(value)} chars")
            print(f"    Stripped length: {len(value.strip())} chars")

        # Get template extraction strategy
        print("\n" + "=" * 80)
        print("TEMPLATE EXTRACTION STRATEGY:")
        print("=" * 80)

        front_fields, back_fields = AnkiService._get_field_extraction_strategy(model_name, card_ord)

        print(f"Front fields identified: {front_fields}")
        print(f"Back fields identified: {back_fields}")

        # Get the actual templates
        templates = AnkiService._invoke("modelTemplates", {"modelName": model_name})
        template_names = list(templates.keys())
        if card_ord < len(template_names):
            template_name = template_names[card_ord]
            card_template = templates[template_name]
            print(f"\nTemplate: {template_name}")
            print(f"  Front: {card_template.get('Front', '')}")
            print(f"  Back: {card_template.get('Back', '')}")

        # Extract values using our method
        print("\n" + "=" * 80)
        print("EXTRACTED VALUES:")
        print("=" * 80)

        front_value = AnkiService._extract_field_values(fields, front_fields)
        back_value = AnkiService._extract_field_values(fields, back_fields)

        print(f"Front extraction result:")
        print(f"  Value: {repr(front_value)[:200]}")
        print(f"  Length: {len(front_value)} chars")
        print(f"  Empty: {not front_value}")

        print(f"\nBack extraction result:")
        print(f"  Value: {repr(back_value)[:200]}")
        print(f"  Length: {len(back_value)} chars")
        print(f"  Empty: {not back_value}")

        # Check rendered HTML
        print("\n" + "=" * 80)
        print("RENDERED HTML (fallback):")
        print("=" * 80)
        question = card_info.get("question", "")
        answer = card_info.get("answer", "")
        print(f"Question length: {len(question)} chars")
        print(f"Answer length: {len(answer)} chars")

        # Diagnosis
        print("\n" + "=" * 80)
        print("DIAGNOSIS:")
        print("=" * 80)

        if not back_fields:
            print("⚠️  ISSUE: No back fields identified from template!")
            print("   This means the template parsing found no answer-only fields.")
            print("   The back template might only reference fields also in the front.")
        elif not back_value:
            print("⚠️  ISSUE: Back fields identified but extraction returned empty!")
            print(f"   Looking for fields: {back_fields}")
            print("   Possible causes:")
            for field_name in back_fields:
                if field_name not in fields:
                    print(f"   - Field '{field_name}' not found in card data")
                else:
                    field_val = fields[field_name].get('value', '')
                    if not field_val.strip():
                        print(f"   - Field '{field_name}' exists but is empty/whitespace")
                    else:
                        print(f"   - Field '{field_name}' has value but was filtered out")
        else:
            print("✓ No issues detected - back value extracted successfully")

    except AnkiConnectError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        search_text = "The Traveling Salesman Problem (TSP) seeks to"
    else:
        search_text = " ".join(sys.argv[1:])

    debug_card_by_front_text(search_text)
