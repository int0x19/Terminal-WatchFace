# Font source

`DejaVuSansMono.ttf` is the unmodified DejaVu Sans Mono development input.
`DejaVuSansMono-Bold.ttf` is the unmodified bold face from the installed DejaVu package.
Its license is in `LICENSE-DejaVu.txt` and in the packaged
`watchface/src/main/res/raw/dejavu_license.txt`.

`tools/rebuild_assets.py` subsets Latin and Cyrillic, removes hinting, scales
glyphs and advances horizontally by 0.8, and renames the result Terminal Mono.
All printing characters remain monospaced. The source font is not packaged;
the generated `res/font/terminal_mono.ttf` is used for the small text.
The same generator produces the real `res/font/terminal_mono_bold.ttf` face
with identical advances. It is applied only to the date and complication captions.

`res/font/clock_mono.ttf` is a separately renamed derivative, Terminal Clock Mono.
It centers each outline in a 0.6-em fixed-width cell and normalizes vertical
metrics for the large clock. Copyright records and packaged license are retained for all
generated fonts. Original block/dot fonts now also center ink in their cells.
