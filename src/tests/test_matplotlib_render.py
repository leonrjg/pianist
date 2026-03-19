#!/usr/bin/env python3
"""
Test matplotlib LaTeX rendering directly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.integrations.anki_service import AnkiService

# Test rendering a simple formula
latex_code = "Var(aX+bY)"

print(f"Testing matplotlib rendering for: {latex_code}")
print("=" * 80)

try:
    result = AnkiService._render_latex_to_base64(latex_code, fontsize=14)

    if result:
        print(f"✓ Rendering successful!")
        print(f"\nData URI length: {len(result)} characters")
        print(f"Preview: {result[:100]}...")
    else:
        print(f"✗ Rendering failed (returned None)")

except Exception as e:
    print(f"✗ Error during rendering: {e}")
    import traceback
    traceback.print_exc()
