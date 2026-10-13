#!/usr/bin/env python3
"""Build fonts, editor thumbnails and previews from the actual WFF layout.

Requires Pillow and fontTools on the development machine, never in the APK.
The preview's reference values are illustrative; no demo data enters the WFF.
"""

from pathlib import Path
import xml.etree.ElementTree as ET

from fontTools.fontBuilder import FontBuilder
from fontTools import subset
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
from labels import LABELS, LABEL_TEXT

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "watchface/src/main/res"

# Original 5x7 glyphs. Lowercase characters use their uppercase counterparts.
PATTERNS = {
    "0": "01110/10001/10011/10101/11001/10001/01110",
    "1": "00100/01100/00100/00100/00100/00100/01110",
    "2": "01110/10001/00001/00010/00100/01000/11111",
    "3": "11110/00001/00001/01110/00001/00001/11110",
    "4": "00010/00110/01010/10010/11111/00010/00010",
    "5": "11111/10000/10000/11110/00001/00001/11110",
    "6": "01110/10000/10000/11110/10001/10001/01110",
    "7": "11111/00001/00010/00100/01000/01000/01000",
    "8": "01110/10001/10001/01110/10001/10001/01110",
    "9": "01110/10001/10001/01111/00001/00001/01110",
    "A": "01110/10001/10001/11111/10001/10001/10001",
    "B": "11110/10001/10001/11110/10001/10001/11110",
    "C": "01111/10000/10000/10000/10000/10000/01111",
    "D": "11110/10001/10001/10001/10001/10001/11110",
    "E": "11111/10000/10000/11110/10000/10000/11111",
    "F": "11111/10000/10000/11110/10000/10000/10000",
    "G": "01111/10000/10000/10111/10001/10001/01111",
    "H": "10001/10001/10001/11111/10001/10001/10001",
    "I": "11111/00100/00100/00100/00100/00100/11111",
    "J": "00111/00010/00010/00010/00010/10010/01100",
    "K": "10001/10010/10100/11000/10100/10010/10001",
    "L": "10000/10000/10000/10000/10000/10000/11111",
    "M": "10001/11011/10101/10101/10001/10001/10001",
    "N": "10001/11001/10101/10011/10001/10001/10001",
    "O": "01110/10001/10001/10001/10001/10001/01110",
    "P": "11110/10001/10001/11110/10000/10000/10000",
    "Q": "01110/10001/10001/10001/10101/10010/01101",
    "R": "11110/10001/10001/11110/10100/10010/10001",
    "S": "01111/10000/10000/01110/00001/00001/11110",
    "T": "11111/00100/00100/00100/00100/00100/00100",
    "U": "10001/10001/10001/10001/10001/10001/01110",
    "V": "10001/10001/10001/10001/10001/01010/00100",
    "W": "10001/10001/10001/10101/10101/10101/01010",
    "X": "10001/10001/01010/00100/01010/10001/10001",
    "Y": "10001/10001/01010/00100/00100/00100/00100",
    "Z": "11111/00001/00010/00100/01000/10000/11111",
    " ": "00000/00000/00000/00000/00000/00000/00000",
    ":": "00000/00100/00100/00000/00100/00100/00000",
    ".": "00000/00000/00000/00000/00000/00100/00100",
    ",": "00000/00000/00000/00000/00100/00100/01000",
    "/": "00001/00001/00010/00100/01000/10000/10000",
    "-": "00000/00000/00000/11111/00000/00000/00000",
    "+": "00000/00100/00100/11111/00100/00100/00000",
    "%": "11001/11010/00010/00100/01000/01011/10011",
    "°": "01100/10010/10010/01100/00000/00000/00000",
    "?": "01110/10001/00001/00010/00100/00000/00100",
    "!": "00100/00100/00100/00100/00100/00000/00100",
    "_": "00000/00000/00000/00000/00000/00000/11111",
    "(": "00010/00100/01000/01000/01000/00100/00010",
    ")": "01000/00100/00010/00010/00010/00100/01000",
    "А": "01110/10001/10001/11111/10001/10001/10001",
    "Б": "11111/10000/10000/11110/10001/10001/11110",
    "В": "11110/10001/10001/11110/10001/10001/11110",
    "Г": "11111/10000/10000/10000/10000/10000/10000",
    "Д": "00110/01010/01010/01010/01010/11111/10001",
    "Е": "11111/10000/10000/11110/10000/10000/11111",
    "Ё": "01010/00000/11111/10000/11110/10000/11111",
    "Ж": "10101/10101/01110/00100/01110/10101/10101",
    "З": "11110/00001/00001/01110/00001/00001/11110",
    "И": "10001/10001/10011/10101/11001/10001/10001",
    "Й": "01010/00100/10001/10011/10101/11001/10001",
    "К": "10001/10010/10100/11000/10100/10010/10001",
    "Л": "00111/01001/01001/01001/01001/01001/10001",
    "М": "10001/11011/10101/10101/10001/10001/10001",
    "Н": "10001/10001/10001/11111/10001/10001/10001",
    "О": "01110/10001/10001/10001/10001/10001/01110",
    "П": "11111/10001/10001/10001/10001/10001/10001",
    "Р": "11110/10001/10001/11110/10000/10000/10000",
    "С": "01111/10000/10000/10000/10000/10000/01111",
    "Т": "11111/00100/00100/00100/00100/00100/00100",
    "У": "10001/10001/10001/01111/00001/00001/11110",
    "Ф": "00100/01110/10101/10101/10101/01110/00100",
    "Х": "10001/10001/01010/00100/01010/10001/10001",
    "Ц": "10010/10010/10010/10010/10010/11111/00001",
    "Ч": "10001/10001/10001/01111/00001/00001/00001",
    "Ш": "10101/10101/10101/10101/10101/10101/11111",
    "Щ": "10101/10101/10101/10101/10101/11111/00001",
    "Ъ": "11000/01000/01000/01110/01001/01001/01110",
    "Ы": "10001/10001/10001/11101/10101/10101/11101",
    "Ь": "10000/10000/10000/11110/10001/10001/11110",
    "Э": "11110/00001/00001/01111/00001/00001/11110",
    "Ю": "10010/10101/10101/11101/10101/10101/10010",
    "Я": "01111/10001/10001/01111/00101/01001/10001",
}


def build_font(name, gap):
    patterns = dict(PATTERNS)
    patterns.update({c.lower(): p for c, p in PATTERNS.items() if c.isalpha()})
    names = {c: f"u{ord(c):04X}" for c in patterns}
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder([".notdef", *names.values()])
    builder.setupCharacterMap({ord(c): n for c, n in names.items()})
    glyphs = {}
    for char, pattern in {".notdef": PATTERNS["?"], **patterns}.items():
        pen = TTGlyphPen(None)
        for row, line in enumerate(pattern.split("/")):
            for col, cell in enumerate(line):
                if cell == "1":
                    x, y = col * 100 + gap // 2, (6 - row) * 100 + gap // 2
                    edge = 100 - gap
                    pen.moveTo((x, y))
                    pen.lineTo((x, y + edge))
                    pen.lineTo((x + edge, y + edge))
                    pen.lineTo((x + edge, y))
                    pen.closePath()
        glyphs[".notdef" if char == ".notdef" else names[char]] = pen.glyph()
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics({n: (600, 0) for n in glyphs})
    builder.setupHorizontalHeader(ascent=750, descent=-100)
    builder.setupNameTable({
        "familyName": name, "styleName": "Regular", "uniqueFontIdentifier": name,
        "fullName": name, "psName": name.replace("_", "-"), "version": "Version 1.0",
        "copyright": "Original Terminal Face glyphs, int0x19, 2026",
    })
    builder.setupOS2(sTypoAscender=750, sTypoDescender=-100, usWinAscent=750, usWinDescent=100)
    builder.setupPost()
    builder.setupMaxp()
    builder.font["head"].created = 3782844800
    builder.font["head"].modified = 3782844800
    builder.font.recalcTimestamp = False
    (RES / "font").mkdir(exist_ok=True)
    builder.save(RES / "font" / f"{name}.ttf")


def build_mono_font():
    """Readable outline monospace: larger caps in the unchanged two-column grid."""
    font = TTFont(ROOT / "tools/assets/DejaVuSansMono.ttf", recalcTimestamp=False)
    options = subset.Options()
    options.hinting = False
    options.recalc_timestamp = False
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=[*range(0x20, 0x100), *range(0x400, 0x500),
                                0x2013, 0x2014, 0x2018, 0x2019, 0x2026, 0x2212])
    subsetter.subset(font)
    glyph_set = font.getGlyphSet()
    glyphs = {}
    for name in font.getGlyphOrder():
        recording = DecomposingRecordingPen(glyph_set)
        glyph_set[name].draw(recording)
        pen = TTGlyphPen(None)
        recording.replay(TransformPen(pen, (0.8, 0, 0, 1, 0, 0)))
        glyphs[name] = pen.glyph()
    for name, glyph in glyphs.items():
        font["glyf"][name] = glyph
        advance, bearing = font["hmtx"][name]
        font["hmtx"][name] = (round(advance * 0.8), round(bearing * 0.8))
    font["hhea"].advanceWidthMax = round(font["hhea"].advanceWidthMax * 0.8)
    font["OS/2"].xAvgCharWidth = round(font["OS/2"].xAvgCharWidth * 0.8)
    font["post"].isFixedPitch = 1
    # Retain copyright/license records; give the modified font its own names.
    renamed = {1: "Terminal Mono", 2: "Regular", 3: "TerminalMono-Regular-1.0",
               4: "Terminal Mono Regular", 6: "TerminalMono-Regular",
               16: "Terminal Mono", 17: "Regular"}
    for record in font["name"].names:
        if record.nameID in renamed:
            record.string = renamed[record.nameID].encode(record.getEncoding())
    font["head"].created = font["head"].modified = 3782844800
    font.save(RES / "font/terminal_mono.ttf")


def build_editor_icons():
    """Phone editors may show icon-only options: every option needs visible text."""
    root = ET.parse(RES / "raw/watchface.xml").getroot()
    captions = {"TITLE": ("AUTO", "PROVIDER"), "NONE": ("NONE", "NO LABEL"),
                "full": ("FULL", "DATE"), "short": ("SHORT", "DATE"),
                "iso": ("ISO", "2026-09-08"), "hidden": ("NONE", "NO DATE")}
    captions.update({item["id"]: (item["text"], item["iconText"]) for item in LABELS})
    icons = {}
    font_path = RES / "font/terminal_mono.ttf"
    for option in root.findall("UserConfigurations/ListConfiguration/ListOption"):
        resource = option.attrib["icon"]
        if resource in icons:
            continue
        label, subtitle = captions.get(option.attrib["id"], (option.attrib["id"], "LABEL"))
        icon = Image.new("RGBA", (192, 192), (0, 0, 0, 0))
        draw = ImageDraw.Draw(icon)
        draw.ellipse((4, 4, 187, 187), fill="#101E19", outline="#80F5BA", width=3)
        for text, y, size, color in [(label, 75, 48, "#F2FFF1"),
                                     (subtitle, 125, 23, "#80F5BA")]:
            font = ImageFont.truetype(str(font_path), size)
            draw.text((96, y), text, fill=color, font=font, anchor="mm")
        icon.save(RES / "drawable" / f"{resource}.png")
        icons[resource] = icon
    sheet = Image.new("RGB", (5 * 192, ((len(icons) + 4) // 5) * 192), "#080D0B")
    for index, icon in enumerate(icons.values()):
        sheet.paste(icon, ((index % 5) * 192, (index // 5) * 192), icon)
    sheet.save(ROOT / "docs/label-options.png")


def render_preview(ambient=False):
    """A small layout renderer, not a substitute for the Wear OS renderer."""
    root = ET.parse(RES / "raw/watchface.xml").getroot()
    scale = 3
    image = Image.new("RGB", (450 * scale, 450 * scale), "black")
    draw = ImageDraw.Draw(image)
    config = {e.attrib["id"]: e.attrib["defaultValue"] for e in root.find("UserConfigurations")}
    palette = ["#80F5BA", "#FFC985", "#F2FFF1"]
    reference = ["33°C", "34° / 21°", "0.79 KM", "27 KCAL", "1190", "8000", "84 BPM", "NE 3.1 M/S"]
    titles = ["TEMP", "H/L", "DIST", "CAL", "STEP", "GOAL", "HR", "WIND"]
    sources = {"HOUR_0_23": 14, "HOUR_1_12": 2, "MINUTE": 34, "SECOND": 39,
               "DAY_OF_WEEK_S": "TUE", "DAY": 8, "MONTH_S": "SEP", "MONTH_F": "SEPTEMBER",
               "YEAR": 2026, "TIMEZONE_OFFSET_DST": "+5", "BATTERY_PERCENT": 96}

    def expression(expr, slot, utc=False):
        if expr == "[IS_24_HOUR_MODE] ? [HOUR_0_23] : [HOUR_1_12]":
            return 14
        if expr.startswith(f"[CONFIGURATION.label{slot}] =="):
            selected = config[f"label{slot}"]
            return LABEL_TEXT[selected]
        key = expr.strip("[]")
        if key.startswith("CONFIGURATION."):
            return config[key.split(".", 1)[1]]
        if key == "COMPLICATION.TEXT":
            return reference[slot - 1]
        if key == "COMPLICATION.TITLE":
            return titles[slot - 1]
        if utc and key == "HOUR_0_23":
            return 9
        return sources[key]

    def visit(element, offset=(0, 0), slot=0):
        alpha = int(element.attrib.get("alpha", 255))
        if ambient:
            for variant in element.findall("Variant"):
                if variant.attrib.get("mode") == "AMBIENT" and variant.attrib.get("target") == "alpha":
                    alpha = int(variant.attrib["value"])
        if alpha == 0:
            return
        tag = element.tag
        if tag == "Condition":
            if element.find("Expressions/Expression").attrib["name"] == "show_ampm":
                return  # Reference preview uses 24-hour time.
            # Reference data supplies titles; this is not a runtime/provider simulator.
            if element.find("Expressions/Expression").attrib["name"].startswith("label_"):
                choice = config[f"label{slot}"]
                branch = (f"label_title_{slot}" if choice == "TITLE"
                          else f"label_hidden_{slot}" if choice == "NONE" else None)
                visit(element.find(f"Compare[@expression='{branch}']") if branch
                      else element.find("Default"), offset, slot)
            else:
                visit(element.find("Compare"), offset, slot)
            return
        if tag == "ComplicationSlot":
            if ambient:
                return
            slot = int(element.attrib["slotId"])
            offset = (offset[0] + int(element.attrib["x"]), offset[1] + int(element.attrib["y"]))
            complication_type = "LONG_TEXT" if len(reference[slot - 1]) > 8 else "SHORT_TEXT"
            visit(element.find(f"Complication[@type='{complication_type}']"), offset, slot)
            return
        if tag == "Group":
            offset = (offset[0] + int(element.attrib.get("x", 0)), offset[1] + int(element.attrib.get("y", 0)))
        if tag == "PartText":
            text_element = element.find("Text")
            font_element = text_element.find("Font")
            template = font_element.find(".//Template")
            if template is None:
                text = (font_element.text or "").strip()
            else:
                localization = element.find("Localization")
                utc = localization is not None and localization.attrib.get("timeZone") == "UTC"
                values = tuple(expression(p.attrib["expression"], slot, utc) for p in template.findall("Parameter"))
                text = (template.text or "").strip() % values
            if font_element.find("Upper") is not None:
                text = text.upper()
            size = round(float(font_element.attrib["size"]) * scale)
            font_path = RES / "font" / (font_element.attrib["family"] + ".ttf")
            width, height = int(element.attrib["width"]) * scale, int(element.attrib["height"]) * scale
            font = ImageFont.truetype(str(font_path), size)
            spacing = float(font_element.attrib.get("letterSpacing", 0)) * size

            def text_width(value):
                return font.getlength(value) + max(0, len(value) - 1) * spacing

            while text_element.attrib.get("isAutoSize") == "TRUE" and text_width(text) > width and size > 12 * scale:
                size -= 1
                font = ImageFont.truetype(str(font_path), size)
                spacing = float(font_element.attrib.get("letterSpacing", 0)) * size
            if text_width(text) > width:
                while text and text_width(text + "...") > width:
                    text = text[:-1]
                text += "..."
            color = element.attrib.get("tintColor", "#FFFFFF")
            if color.startswith("[CONFIGURATION.palette."):
                color = palette[int(color[-2])]
            x, y = (offset[0] + int(element.attrib["x"])) * scale, (offset[1] + int(element.attrib["y"])) * scale
            if text_element.attrib.get("align") == "CENTER":
                x += (width - text_width(text)) / 2
            ascender, descender = font.getmetrics()
            baseline_y = y + (height - ascender - descender) / 2
            if spacing:
                for char in text:
                    draw.text((x, baseline_y), char, fill=color, font=font)
                    x += font.getlength(char) + spacing
            else:
                draw.text((x, baseline_y), text, fill=color, font=font)
            return
        for child in element:
            if child.tag not in {"UserConfigurations", "Metadata", "Expressions", "Variant"}:
                visit(child, offset, slot)

    visit(root.find("Scene"))
    image = image.resize((450, 450), Image.Resampling.LANCZOS)
    mask = Image.new("L", (450, 450), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 449, 449), fill=255)
    image = Image.composite(image, Image.new("RGB", (450, 450), "black"), mask)
    return image


if __name__ == "__main__":
    build_font("terminal_dot", 28)
    build_font("terminal_block", 0)
    build_mono_font()
    (ROOT / "docs").mkdir(exist_ok=True)
    build_editor_icons()
    active = render_preview()
    active.save(RES / "drawable/preview.png")
    active.save(ROOT / "docs/design-preview.png")
    render_preview(ambient=True).save(ROOT / "docs/ambient-preview.png")
    print("Generated fonts, editor thumbnails and previews. Preview values are illustrative only.")
