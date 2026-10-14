# Терминальные темы и фон — 0.8.1-test

Удержать циферблат → редактирование → «Цветовая тема».
Добавлено семь схем к трём прежним. По умолчанию остаётся Terminal green.
Переключение темы не меняет источники данных, шрифт или геометрию.

В отдельной настройке «Фон» два варианта:

- «Фон темы» — исходная подложка выбранной темы, как в 0.8.0-test. По умолчанию.
- «AMOLED — чёрный» — чистый #000000 для любой темы без изменения цветов текста.

Выбор фона сохраняется независимо от темы: переключение палитры не отменяет AMOLED.
У Terminal green, Ice blue и Amber исходный фон уже чёрный, поэтому разницы нет.
В ambient/AOD фон чёрный при обоих вариантах. Настройка управляет только подложкой,
а не яркостью, режимом дисплея или системным энергосбережением.

Быстрый вариант 0.6.2-fixed-labels-test принят пользователем как основной после
сообщения о значительно более быстром открытии Wearable. Основная ветка циферблата
`feat/terminal-face` теперь включает этот вариант; `test/fixed-complication-labels`
и прежние теги сохранены. Ветка `main` по-прежнему содержит исходный шаблон.

## Цвета

Это адаптация терминальных схем к четырём ролям циферблата, а не перенос полной
16-цветной ANSI-палитры. Основной текст — часы, местное смещение и заряд;
дата, секунды и верхние подписи используют цвет подписей.

| Тема | Подписи | Значения | Основной текст | Фон |
|---|---|---|---|---|
| Terminal green | #80F5BA | #FFC985 | #F2FFF1 | #000000 |
| Ice blue | #7DCFFF | #BFDFFF | #FFFFFF | #000000 |
| Amber | #FFB858 | #FFDDA8 | #FFF3D8 | #000000 |
| Tango Dark | #8AE234 | #FCE94F | #EEEEEC | #2E3436 |
| Solarized Dark | #2AA198 | #B58900 | #93A1A1 | #002B36 |
| Dracula | #BD93F9 | #50FA7B | #F8F8F2 | #282A36 |
| Gruvbox Dark | #B8BB26 | #FABD2F | #EBDBB2 | #282828 |
| Nord | #88C0D0 | #EBCB8B | #ECEFF4 | #2E3440 |
| Monokai | #66D9EF | #A6E22E | #F8F8F2 | #272822 |
| Tokyo Night | #7AA2F7 | #BB9AF7 | #C0CAF5 | #1A1B26 |

[Фоны тем](palette-comparison.png), [темы на AMOLED-фоне](palette-amoled-comparison.png).
Отдельные файлы `palette-ID.png`, `palette-ID-amoled.png` и
`palette-ID-ambient.png` создаются из реального WFF. Данные иллюстративные;
локальное превью не заменяет проверку на часах.

Источники оттенков:

- Tango: [классическая палитра для iTerm2](https://github.com/mbadolato/iTerm2-Color-Schemes/blob/master/foot/Builtin%20Tango%20Dark.ini),
  [схемы GNOME Terminal](https://help.gnome.org/gnome-terminal/app-colors.html).
  Взяты яркие зелёный/жёлтый/белый; подложка адаптирована к тёмно-серому Tango.
- Solarized: [Ethan Schoonover](https://ethanschoonover.com/solarized/).
  Использованы cyan/yellow/base1/base03; основной текст выбран чуть светлее base0.
- Dracula: [палитра автора](https://draculatheme.com/contribute).
- Gruvbox: [исходные цвета morhetz](https://github.com/morhetz/gruvbox/blob/master/colors/gruvbox.vim).
- Nord: [официальные палитры](https://www.nordtheme.com/docs/colors-and-palettes/).
- Monokai: [базовая палитра в VS Code](https://github.com/microsoft/vscode/blob/main/extensions/theme-monokai/themes/monokai-color-theme.json).
  Cyan/green выбраны для читаемости небольшого текста вместо малоконтрастного magenta.
- Tokyo Night: [терминальная палитра Folke Lemaitre](https://github.com/folke/tokyonight.nvim/blob/main/extras/kitty/tokyonight_night.conf).

## Реализация и ограничения

Одна прежняя ColorConfiguration с тем же id=palette и defaultValue=terminal.
Идентификаторы terminal/ice/amber и первые три цвета не менялись; добавлен
четвёртый цвет фона. Добавлена независимая ListConfiguration backgroundMode
с двумя вариантами theme / amoled. Всего пять настроек, девять ListOption
и десять ColorOption. Ручные подписи не возвращались; для фона добавлены
только две PNG-миниатюры, прежние варианты не менялись;
шрифты и разметка не дублировались для каждой темы.

Цветной фон — один векторный Rectangle перед остальными элементами.
Condition показывает его только при backgroundMode=theme; в AMOLED остаётся
чёрный Scene.backgroundColor. В ambient Rectangle скрыт через Variant,
поэтому фон всегда чёрный. Это совместимо
с WFF 2, не требует динамического Transform цвета из WFF 4.
В активном режиме цветная подложка может расходовать больше энергии, чем чёрная;
расход батареи этой сборки на устройстве не измерялся.

Проверяется контраст каждого цвета текста с активным фоном и с чёрным ambient:
отношение не меньше 4.5:1. Это численная проверка палитры, не гарантия читаемости
на любом дисплее или измерение энергопотребления.

Источники и настройки семи полей сохранены; цвета задаёт циферблат,
а не поставщики данных. Новый APK имеет versionCode=11 и прежний ключ;
его можно устанавливать поверх 0.8.0-test без удаления.
Реальное переключение темы/фона, сохранение выбора после перезапуска и
время открытия редактора нужно проверить на устройстве.
