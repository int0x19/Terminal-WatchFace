"""Shared short-label metadata for asset generation and WFF regression tests."""
import json
from pathlib import Path

LABELS = json.loads(Path(__file__).with_name("labels.json").read_text())
LABEL_TEXT = {item["id"]: item["text"] for item in LABELS}


def manual_label_expression(slot):
    """Preserve installed option IDs while shortening their displayed captions."""
    source = f"[CONFIGURATION.label{slot}]"
    expression = source
    aliases = [item for item in LABELS if item["id"] != item["text"]]
    for item in reversed(aliases):
        expression = f'{source} == "{item["id"]}" ? "{item["text"]}" : ({expression})'
    return expression
