"""WFF 2 caption formatting: real font faces, native case formatters and substrings."""
from copy import deepcopy
import json
import xml.etree.ElementTree as ET

WEIGHTS = {"normal": "terminal_mono", "bold": "terminal_mono_bold"}
CASES = ("upper", "initial", "lower", "source")
LANGUAGES = {"ru": "ru_RU", "en": "en_US", "system": None}
DATE_PATTERNS = {"full": "EEE dd MMMM yyyy", "short": "EEE dd MMM", "iso": "yyyy-MM-dd"}
PREVIEW_STYLES = (
    ("en-normal-upper", "en", "normal", "upper", "EN / ОБЫЧНЫЙ / ABC"),
    ("en-bold-upper", "en", "bold", "upper", "EN / ЖИРНЫЙ / ABC"),
    ("ru-normal-upper", "ru", "normal", "upper", "RU / ОБЫЧНЫЙ / АБВ"),
    ("ru-normal-initial", "ru", "normal", "initial", "RU / ОБЫЧНЫЙ / Абв"),
    ("ru-bold-initial", "ru", "bold", "initial", "RU / ЖИРНЫЙ / Абв"),
    ("ru-bold-lower", "ru", "bold", "lower", "RU / ЖИРНЫЙ / абв"),
)


def template(expression):
    node = ET.Element("Template")
    node.text = "%s"
    ET.SubElement(node, "Parameter", expression=expression)
    return node


def caption_fonts(original, weight, case):
    """Return one or two styled Font runs; keep value/space/icon runs separate."""
    font = deepcopy(original)
    font.set("family", WEIGHTS[weight])
    if font.find("InlineImage") is not None:
        return [font]
    value = font.find(".//Template")
    expression = (value.find("Parameter").attrib["expression"] if value is not None
                  else json.dumps((font.text or "").strip(), ensure_ascii=False))
    if value is not None:
        assert (value.text or "").strip() == "%s" and len(value.findall("Parameter")) == 1
    for child in list(font):
        font.remove(child)
    font.text = None
    if expression == '" "':
        font.append(template(expression))
        return [font]
    if case == "initial":
        # Reachable captions are nonempty: TITLE is guarded, manual labels and dates aren't empty.
        first, rest = deepcopy(font), deepcopy(font)
        ET.SubElement(first, "Upper").append(template(f"subText(({expression}), 0, 1)"))
        ET.SubElement(rest, "Lower").append(template(f"subText(({expression}), 1, textLength(({expression})))"))
        return [first, rest]
    target = ET.SubElement(font, "Upper" if case == "upper" else "Lower") if case != "source" else font
    target.append(template(expression))
    return [font]


def style_variants(part, rich=False):
    """Only eligible captions change; a rich bottom line's amber value is copied exactly."""
    choices = ET.Element("Condition")
    expressions = ET.SubElement(choices, "Expressions")
    for weight in WEIGHTS:
        for case in CASES:
            name = f"caption_{weight}_{case}"
            ET.SubElement(expressions, "Expression", name=name).text = (
                f'[CONFIGURATION.captionWeight] == "{weight}" && [CONFIGURATION.captionCase] == "{case}"')
            styled = deepcopy(part)
            if "name" in styled.attrib:
                styled.set("name", styled.attrib["name"] + f"_{weight}_{case}")
            text = styled.find("Text")
            originals = list(text)
            for child in originals:
                text.remove(child)
                if child.tag == "Font" and (not rich or child.attrib.get("color") == "[CONFIGURATION.palette.0]"):
                    text.extend(caption_fonts(child, weight, case))
                else:
                    text.append(child)
            ET.SubElement(choices, "Compare", expression=name).append(styled)
    return choices


def style_labels(group, rich=False):
    """Wrap the label branches, not the six grid values or provider-policy nodes."""
    labels = group.find("Condition")
    def wrap(parent):
        for index, child in enumerate(list(parent)):
            if child.tag == "PartText":
                parent.remove(child)
                parent.insert(index, style_variants(child, rich=rich))
            else:
                wrap(child)
    wrap(labels)


def configurations():
    specs = (
        ("captionWeight", "caption_weight_name", "bold", WEIGHTS),
        ("captionCase", "caption_case_name", "initial", CASES),
        ("dateLanguage", "date_language_name", "ru", LANGUAGES),
    )
    nodes = []
    for key, display, default, options in specs:
        config = ET.Element("ListConfiguration", id=key, displayName=display, defaultValue=default)
        prefix = {"captionWeight": "weight", "captionCase": "case", "dateLanguage": "language"}[key]
        for option in options:
            ET.SubElement(config, "ListOption", id=option, displayName=f"{prefix}_{option}_name", icon=f"{prefix}_{option}_icon")
        nodes.append(config)
    return nodes
