#!/usr/bin/env python3
"""
Test rendering a specific LaTeX expression to see what fails.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.integrations.anki_service import AnkiService

# The problematic LaTeX from the card
latex_code = r"\huge F(x) = \int_{-\infty}^{x} f(t) \, dt"

print(f"Testing LaTeX: {latex_code}")
print("=" * 80)

# Try to render it
try:
    result = AnkiService._render_latex_to_base64(latex_code, fontsize=16)

    if result:
        print(f"✓ Rendering successful!")
        print(f"Data URI length: {len(result)} chars")
    else:
        print(f"✗ Rendering returned None")
        print(f"\nTrying without \\huge:")

        # Try without \huge
        latex_without_huge = latex_code.replace(r'\huge ', '')
        print(f"  LaTeX: {latex_without_huge}")

        result2 = AnkiService._render_latex_to_base64(latex_without_huge, fontsize=16)
        if result2:
            print(f"  ✓ Works without \\huge!")
            print(f"  Solution: Strip unsupported commands before rendering")
        else:
            print(f"  ✗ Still fails - different issue")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("ANALYSIS:")
print("=" * 80)
print("""
The \\huge command is a LaTeX size modifier not supported by matplotlib's mathtext.

Mathtext supports a subset of LaTeX:
  ✓ Basic math: \\frac, \\int, \\sum, ^, _
  ✓ Greek: \\alpha, \\beta, \\Sigma
  ✓ Operators: \\times, \\cdot
  ✗ Size commands: \\tiny, \\small, \\large, \\huge
  ✗ Custom packages
  ✗ Complex formatting

Solution options:
1. Strip unsupported commands (\\huge, \\large, etc.) before rendering
2. Use larger fontsize parameter instead of \\huge
3. Fall back to showing raw LaTeX when rendering fails
""")
