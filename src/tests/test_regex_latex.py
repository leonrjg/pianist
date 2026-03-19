#!/usr/bin/env python3
"""
Test LaTeX regex matching.
"""

import re

test_text = r"<p>If X and Y are not independent, \(Var(aX+bY)\) =</p>"

patterns = [
    (r'\\\[(.+?)\\\]', 'display \\[...\\]'),
    (r'\$\$(.+?)\$\$', 'display $$...$$'),
    (r'\\\((.+?)\\\)', 'inline \\(...\\)'),
    (r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', 'inline $...$'),
]

print(f"Test text: {test_text}")
print()

for pattern, desc in patterns:
    matches = re.findall(pattern, test_text, flags=re.DOTALL)
    print(f"{desc}:")
    print(f"  Pattern: {pattern}")
    print(f"  Matches: {matches}")
    print()
