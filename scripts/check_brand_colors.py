#!/usr/bin/env python3
"""
Brand Color Enforcement Script

This script checks for hardcoded brand hex colors in the codebase.
Run as part of pre-commit hooks or CI to prevent brand color drift.

USAGE:
    python scripts/check_brand_colors.py
    python scripts/check_brand_colors.py --fix  # Show how to fix violations

EXIT CODES:
    0 - No violations found
    1 - Violations found (hardcoded brand colors detected)

BRAND COLORS (defined in nicegui_app/components/theme.py):
    #C9A227 (gold) - Use PTO_GOLD constant
    #5a6a72 (gray) - Use PTO_GRAY constant
    #2196F3 (blue) - Use PTO_BLUE constant

WHITELISTED FILES:
    - nicegui_app/components/theme.py (source of truth)
    - *.backup files (excluded from checks)
"""

import re
import sys
from pathlib import Path

# Brand hex patterns (case-insensitive)
BRAND_PATTERNS = [
    (re.compile(r'#[Cc]9[Aa]227', re.IGNORECASE), 'PTO_GOLD'),
    (re.compile(r'#5[Aa]6[Aa]72', re.IGNORECASE), 'PTO_GRAY'),
    (re.compile(r'#2196[Ff]3', re.IGNORECASE), 'PTO_BLUE'),
]

# Files to skip (source of truth and generated files)
WHITELIST_PATTERNS = [
    'theme.py',            # Source of truth
    '.backup',             # Backup files
    '__pycache__',         # Python cache
    '.pyc',                # Compiled Python
    'check_brand_colors.py',  # This script
    'playwright_engine.py',   # Automation - needs inline JS colors
    'video_producer.py',      # Automation - needs RGB tuples for PIL
]

# Directories to scan
SCAN_DIRS = [
    'nicegui_app',
    'src',
    'services',
    'config',
]


def should_skip_file(filepath: Path) -> bool:
    """Check if file should be skipped."""
    filepath_str = str(filepath)
    return any(pattern in filepath_str for pattern in WHITELIST_PATTERNS)


def scan_file(filepath: Path) -> list:
    """Scan a single file for brand color violations."""
    violations = []

    try:
        content = filepath.read_text(encoding='utf-8')
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            for pattern, constant in BRAND_PATTERNS:
                if pattern.search(line):
                    violations.append({
                        'file': str(filepath),
                        'line': line_num,
                        'content': line.strip()[:100],
                        'pattern': pattern.pattern,
                        'constant': constant,
                    })
    except Exception as e:
        print(f"Warning: Could not read {filepath}: {e}")

    return violations


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    show_fix = '--fix' in sys.argv

    all_violations = []

    for scan_dir in SCAN_DIRS:
        dir_path = project_root / scan_dir
        if not dir_path.exists():
            continue

        for filepath in dir_path.rglob('*.py'):
            if should_skip_file(filepath):
                continue

            violations = scan_file(filepath)
            all_violations.extend(violations)

    if not all_violations:
        print("No brand color violations found.")
        return 0

    print(f"\n{'='*70}")
    print(f"BRAND COLOR VIOLATIONS FOUND: {len(all_violations)}")
    print(f"{'='*70}\n")

    for v in all_violations:
        print(f"File: {v['file']}")
        print(f"Line {v['line']}: {v['content']}")
        if show_fix:
            print(f"  FIX: Replace {v['pattern']} with {v['constant']} constant")
            print(f"  Import: from nicegui_app.components.theme import {v['constant']}")
        print()

    print(f"{'='*70}")
    print("To fix: Import constants from nicegui_app.components.theme")
    print("  from nicegui_app.components.theme import PTO_GOLD, PTO_GRAY, PTO_BLUE")
    print(f"{'='*70}")

    return 1


if __name__ == '__main__':
    sys.exit(main())
