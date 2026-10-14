"""Shared terminal palette metadata; WFF indices 0–2 keep their original roles."""
import json
from pathlib import Path

PALETTES = json.loads(Path(__file__).with_name("palettes.json").read_text())
PALETTE_ROLES = ("label", "value", "foreground", "background")


def palette_colors(palette):
    return [palette[role] for role in PALETTE_ROLES]


def wff_colors(palette):
    return " ".join("#FF" + color[1:] for color in palette_colors(palette))
