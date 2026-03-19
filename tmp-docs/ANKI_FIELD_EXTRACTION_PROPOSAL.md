# Deterministic Anki Field Extraction Strategy

## Problem

Current implementation uses "common field names" (`Front`, `Back`, `Question`, `Answer`, etc.) to guess which fields contain the question and answer. This is fragile and fails with custom card types.

## Root Cause

Anki cards can have arbitrary field names depending on the note type (model). Examples:
- Basic: `Front` / `Back`
- Language cards: `English` / `Spanish`
- Custom: `Term` / `Definition` / `Example`

Additionally, the `answer` field from `cardsInfo` includes the rendered back side, which often contains `{{FrontSide}}` (the question repeated) plus the answer.

## Deterministic Solution

### Available Information

From AnkiConnect API, we have:

1. **`cardsInfo` response** provides:
   - `modelName`: Note type name (e.g., "Basic")
   - `ord`: Card ordinal (which template, 0-indexed)
   - `fields`: Dictionary of all field names and values
   - `question`: Rendered HTML of front side
   - `answer`: Rendered HTML of back side (includes front + answer)

2. **`modelTemplates` response** provides template structure:
   ```json
   {
     "Card 1": {
       "Front": "{{Front}}",
       "Back": "{{FrontSide}}\n\n<hr id=answer>\n\n{{Back}}"
     }
   }
   ```

3. **`modelFieldNames` response** provides ordered list of field names

### Extraction Algorithm

```
1. Get card info (cardsInfo API call)
   - Extract: modelName, ord, fields

2. Get model templates (modelTemplates API call - cache this!)
   - Extract templates for the note type

3. Select template based on card ordinal
   - ord=0 -> first template, ord=1 -> second template, etc.

4. Parse Front template to identify front fields
   - Regex: {{FieldName}}
   - Exclude special vars: FrontSide, Tags, Type, Deck, etc.
   - Result: List of field names used on front

5. Parse Back template to identify back fields
   - Same regex extraction
   - Exclude: FrontSide and fields already on front
   - Result: List of answer-only field names

6. Extract field values
   - Front: Concatenate values of front fields
   - Back: Concatenate values of answer-only fields
   - Fallback: Use 'question'/'answer' if parsing fails
```

### Template Parsing Details

**Field Reference Patterns:**
- Simple: `{{FieldName}}`
- With hint: `{{FieldName:hint}}`
- Conditional: `{{#FieldName}}...{{/FieldName}}`

**Special Variables to Exclude:**
- `FrontSide` - Rendered front (used in back template)
- `Tags`, `Type`, `Deck`, `Subdeck`, `Card`, `CardFlag`

**Regex Pattern:**
```python
pattern = r'\{\{([^{}]+)\}\}'
# Then filter out special variables and extract base field name
```

### Edge Cases

1. **Multiple answer fields** (e.g., Definition + Example)
   - Concatenate all answer fields with separator
   - Or: Return as list for custom display

2. **Cloze cards** (e.g., `{{cloze:Text}}`)
   - Template field reference: `{{cloze:Text}}`
   - Extract base field name: `Text`
   - May need special handling for cloze cards

3. **No answer-only fields** (rare)
   - Back template might only show FrontSide in different format
   - Fallback: Use all fields, or use rendered 'answer'

4. **Complex templates with conditionals**
   - `{{#Field1}}Show this{{/Field1}}`
   - Still extract Field1 as a referenced field
   - Our regex handles this

### Performance Optimization

**Caching Strategy:**
- Cache model templates per session/reminder
- Key: modelName
- Reduces API calls (templates don't change during session)

**Implementation:**
```python
_template_cache = {}  # {modelName: templates}

def get_model_templates(model_name):
    if model_name not in _template_cache:
        _template_cache[model_name] = invoke("modelTemplates", {"modelName": model_name})
    return _template_cache[model_name]
```

### Testing Scripts Created

1. **`inspect_anki_card.py`** - View full card structure
   ```bash
   python inspect_anki_card.py "DeckName"
   ```
   Shows: Complete cardsInfo response, fields, templates

2. **`analyze_card_templates.py`** - Analyze all templates
   ```bash
   python analyze_card_templates.py
   ```
   Shows: Field extraction strategy for each note type

### Implementation Checklist

- [ ] Add template caching to AnkiService
- [ ] Implement template parsing function (regex-based)
- [ ] Update `get_random_card()` to use template-based extraction
- [ ] Handle multiple answer fields (concatenate vs. list)
- [ ] Add fallback for parsing failures
- [ ] Test with: Basic, Cloze, custom note types
- [ ] Update tests to verify correct field extraction
- [ ] Document the new approach in README

### Benefits

✅ **Deterministic** - No guessing field names
✅ **Universal** - Works with ANY card type
✅ **Future-proof** - Handles new/custom note types
✅ **Accurate** - Separates question from answer correctly
✅ **Maintainable** - Clear algorithm, easy to debug

### Alternatives Considered

1. **Strip HTML from 'answer' field**
   - ❌ Fragile - depends on HTML structure
   - ❌ Loses formatting
   - ❌ Hard to separate FrontSide from answer

2. **Use only first/last fields**
   - ❌ Doesn't work for multi-field cards
   - ❌ Arbitrary and unreliable

3. **Manual configuration per deck**
   - ❌ User burden
   - ❌ Not scalable
   - ❌ Breaks when card types change

### Next Steps

1. **Run analysis script** to verify approach with actual Anki data
   ```bash
   python analyze_card_templates.py
   ```

2. **Review output** - Confirm field extraction strategy works for your card types

3. **Implement** - Update `anki_service.py` with template-based extraction

4. **Test** - Verify with different note types

---

**Status**: Proposal - Ready for review and testing
**Scripts**: Created for investigation
**Implementation**: Waiting for approval
