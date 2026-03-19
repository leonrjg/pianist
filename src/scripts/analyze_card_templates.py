#!/usr/bin/env python3
"""
Analyze Anki card templates to determine deterministic field extraction.

This script examines the template structure to understand how to properly
extract front/back fields for any card type.
"""

import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.integrations.anki_service import AnkiService, AnkiConnectError


def extract_field_references(template_text):
    """Extract all {{FieldName}} references from a template."""
    # Match {{...}} but exclude special Anki variables
    pattern = r'\{\{([^{}]+)\}\}'
    matches = re.findall(pattern, template_text)

    # Filter out Anki special variables and conditionals
    special_vars = ['FrontSide', 'Tags', 'Type', 'Deck', 'Subdeck', 'Card', 'CardFlag'}

    fields = []
    for match in matches:
        # Remove modifiers like {{Field:hint}} -> Field
        field_name = match.split(':')[0].strip()
        # Remove # prefix for conditionals
        field_name = field_name.lstrip('#/')

        if field_name not in special_vars and field_name not in fields:
            fields.append(field_name)

    return fields


def analyze_model_templates(model_name):
    """Analyze templates for a specific model."""
    print(f"\n{'=' * 80}")
    print(f"Analyzing model: {model_name}")
    print('=' * 80)

    try:
        # Get templates
        templates = AnkiService._invoke("modelTemplates", {"modelName": model_name})

        # Get field names for reference
        field_names = AnkiService._invoke("modelFieldNames", {"modelName": model_name})
        print(f"\nAvailable fields: {field_names}")

        # Analyze each card template
        for card_name, card_template in templates.items():
            print(f"\n{'-' * 80}")
            print(f"Card: {card_name}")
            print('-' * 80)

            front_template = card_template.get('Front', '')
            back_template = card_template.get('Back', '')

            print(f"\nFront template:\n{front_template}")
            print(f"\nBack template:\n{back_template}")

            # Extract field references
            front_fields = extract_field_references(front_template)
            back_fields = extract_field_references(back_template)

            # Identify back-only fields (answer fields)
            answer_fields = [f for f in back_fields if f not in front_fields]

            print(f"\n📋 Field Analysis:")
            print(f"  Front fields: {front_fields}")
            print(f"  Back fields: {back_fields}")
            print(f"  Answer-only fields: {answer_fields}")

            print(f"\n💡 Extraction Strategy:")
            if front_fields:
                print(f"  Front: Use field(s) {front_fields}")
            else:
                print(f"  Front: Use 'question' from cardsInfo")

            if answer_fields:
                print(f"  Back: Use field(s) {answer_fields}")
            else:
                print(f"  Back: Use 'answer' from cardsInfo (includes front)")

    except AnkiConnectError as e:
        print(f"Error: {e}")


def analyze_all_models():
    """Analyze all available models."""
    print("=" * 80)
    print("ANKI TEMPLATE ANALYSIS")
    print("=" * 80)

    try:
        # Get all model names
        model_names = AnkiService._invoke("modelNames")
        print(f"\nFound {len(model_names)} note type(s)")

        # Analyze each model
        for model_name in model_names:
            analyze_model_templates(model_name)

        print(f"\n{'=' * 80}")
        print("DETERMINISTIC EXTRACTION STRATEGY")
        print('=' * 80)
        print("""
For deterministic field extraction:

1. Get card info from cardsInfo (includes modelName, ord, fields)
2. Get model templates using modelTemplates(modelName)
3. Select the template based on card ordinal (ord)
4. Parse template to extract field references:
   - Front template fields = question fields
   - Back template fields (excluding FrontSide) = all back fields
   - Answer fields = back fields NOT in front fields
5. Extract those specific field values from card.fields

Implementation approach:
- Cache model templates to avoid repeated API calls
- Use regex to extract {{FieldName}} from templates
- Handle edge cases: cloze cards, multiple answer fields, etc.
- Fallback to 'question'/'answer' fields if parsing fails

Benefits:
- Works with ANY card type (Basic, Cloze, custom)
- No hardcoded field name guessing
- Properly separates question from answer
- Future-proof for new card types
        """)

    except AnkiConnectError as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    if not AnkiService.test_connection():
        print("Error: Cannot connect to Anki. Make sure Anki is running.")
        sys.exit(1)

    analyze_all_models()
