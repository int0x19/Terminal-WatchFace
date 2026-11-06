#!/usr/bin/env python3
"""Promote the approved first-layout refinement, without rebuilding archived sketches."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPROVED = ROOT / "docs/large-type-sketches/2026-11-06-r2/familiar-refined.xml"
CLOCK_FONTS = {"block": "terminal_block", "dot": "terminal_dot", "mono": "clock_mono"}
ROWS = (250, 300, 350)
SLOTS = (2, 3, 4, 6, 7)
DATE_SIZE = 38


def build():
    """Use the exact WFF approved by the user; fixtures exist only in PNG previews."""
    return APPROVED.read_text()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(build())
    print(f"Generated approved five-field large-type WFF: {args.output}")
