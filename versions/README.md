# Сохранённые версии Terminal Face

Готовые версии хранятся раздельно и добавляются в Git вместе с исходниками.
Оба новых приложения имеют свои версии в `watchface/variants.properties`.
Для выпуска увеличить versionCode и versionName нужного варианта, затем:

```sh
sh tools/check.sh
python3 tools/archive_version.py
git add README.md docs tools watchface versions build.gradle.kts gradle .gitignore
git commit -m "Release Terminal Face VERSION"
git tag -a vCOMPACT_VERSION -m "Terminal Face Compact COMPACT_VERSION"
git tag -a vLARGE_VERSION -m "Terminal Face Large LARGE_VERSION"
```

Вместо COMPACT_VERSION/LARGE_VERSION подставить фактические версии.
По умолчанию скрипт архивирует оба варианта; `--flavor compact` или `--flavor large`
выбирает один. Он проверяет applicationId, версию APK,
соответствие WFF исходникам в APK/AAB и сохраняет SHA-256. Повторный запуск
с неизменными файлами ничего не записывает; перезапись другой сборкой запрещена.

| Версия | Что сохранено |
|---|---|
| Шаблон | Полные исходники: ветка main, коммит 931c71e |
| 0.1.0 | Только фактический скриншот; оригинальные APK/AAB и точный снимок исходников не сохранились |
| 0.2.0 | Только фактические скриншоты; оригинальные APK/AAB и точный снимок исходников не сохранились |
| 0.3.0 | APK, AAB, WFF XML, active/ambient превью, контрольные суммы; полные исходники по тегу v0.3.0 |
| 0.4.0-test | Один APK с A/B/C, AAB, WFF, превью всех разметок и сравнение; исходники по тегу v0.4.0-test |
| 0.5.0-test | Совмещённая шапка A+B, компактная таблица, три шрифта; APK, AAB, WFF, все превью и сравнение; тег v0.5.0-test |
| 0.6.0-test | Дата +29%, одно широкое нижнее поле, семь источников; APK, AAB, WFF, все превью и сравнение; тег v0.6.0-test |
| 0.7.0-test | Жирность/регистр даты и подписей, язык даты; APK, AAB, WFF, все превью и сравнения; тег v0.7.0-test |
| 0.6.1-rollback | Точное оформление и ресурсы 0.6.0-test, versionCode=8 для установки поверх 0.7.0-test; APK, AAB, WFF, превью; тег v0.6.1-rollback |
| 0.6.2-fixed-labels-test | Только AUTO-подписи без ручного выбора; дизайн и семь источников из 0.6 rollback; APK, AAB, WFF, превью; ветка test/fixed-complication-labels, тег v0.6.2-fixed-labels-test |
| 0.8.0-test | Быстрая AUTO-версия стала основной, десять терминальных тем, чёрный ambient-фон; APK, AAB, WFF, превью всех тем/шрифтов, сравнение; тег v0.8.0-test |
| 0.8.1-test | Независимый выбор «Фон темы» / «AMOLED — чёрный» для всех десяти палитр, versionCode=11; APK, AAB, WFF, превью обоих фонов и ambient, сравнения; тег v0.8.1-test |
| 0.9.0-large-type-test | Одобренный первый крупный вариант: пять полей, шрифты 38/42, часы 106, ровные интервалы; versionCode=12, прежние темы/AMOLED/AUTO; APK, AAB, WFF, все превью и сравнения; ветка feat/large-type-sketches, тег v0.9.0-large-type-test |
| 0.9.1-large-type-test | Иерархия R3: подписи 34, дата и значения 40, UTC-смещение над UTC-временем; versionCode=13, прежние пять источников/темы/AMOLED/AUTO; APK, AAB, WFF, все превью и сравнения; тег v0.9.1-large-type-test |
| 0.8.1-compact | Независимый Terminal Face Compact, applicationId с .compact, code=14, точная разметка 0.8.1; APK/AAB, WFF, все превью, SHA-256; тег v0.8.1-compact |
| 0.9.1-large | Независимый Terminal Face Large, applicationId с .large, code=14, точная разметка 0.9.1; APK/AAB, WFF, все превью, SHA-256; тег v0.9.1-large |

У версий 0.1.0 и 0.2.0 нет тегов релиза: скриншоты не выдаются за полноценные
архивы сборок. Старые сборки не воссоздавались. Начиная с 0.3.0 сохраняется
полный набор артефактов. Все архивы пока локальные; внешняя резервная копия
или публикация не выполнялась. AAB без production-подписи, APK подписан ключом разработки.
