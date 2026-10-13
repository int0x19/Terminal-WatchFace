# Font source

`DejaVuSansMono.ttf` is the unmodified DejaVu Sans Mono development input.
Its license is in `LICENSE-DejaVu.txt` and in the packaged
`watchface/src/main/res/raw/dejavu_license.txt`.

`tools/rebuild_assets.py` subsets Latin and Cyrillic, removes hinting, scales
glyphs and advances horizontally by 0.8, and renames the result Terminal Mono.
All printing characters remain monospaced. The source font is not packaged;
the generated `res/font/terminal_mono.ttf` is used for the small text.

`res/font/clock_mono.ttf` is a separately renamed derivative, Terminal Clock Mono.
It centers each outline in a 0.6-em fixed-width cell and normalizes vertical
metrics for the large clock. Copyright and license records are retained in both
generated fonts. Original block/dot fonts now also center ink in their cells.
