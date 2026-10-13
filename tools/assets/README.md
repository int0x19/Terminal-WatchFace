# Font source

`DejaVuSansMono.ttf` is the unmodified DejaVu Sans Mono development input.
Its license is in `LICENSE-DejaVu.txt` and in the packaged
`watchface/src/main/res/raw/dejavu_license.txt`.

`tools/rebuild_assets.py` subsets Latin and Cyrillic, removes hinting, scales
glyphs and advances horizontally by 0.8, and renames the result Terminal Mono.
All printing characters remain monospaced. The source font is not packaged;
only the generated `res/font/terminal_mono.ttf` is used by the watch face.
