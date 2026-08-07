# ЗАДАНИЕ ДЛЯ ANTIGRAVITY — Спринт 3: валидация стиля Pulse

## Роль и цель

Ты — инженер, который должен построить и выполнить эксперимент по проверке
стилевой консистентности генератора изображений для проекта Pulse
(ежедневный сатирический плакат-дайджест).

**Цель:** выяснить, способен ли Nano Banana Pro удерживать единую
«руку художника» на 5 разных содержательных темах, и корректно ли он
рендерит кириллицу.

**Что нужно сделать:**
1. Написать Python-скрипт генерации: 5 брифов × 10 вариантов = 50 изображений.
2. Разложить результат по папкам.
3. Автоматически оценить каждое изображение vision-моделью по 8 критериям.
4. Собрать contact sheet (сводный лист превью) по каждому брифу.
5. Выдать итоговый отчёт с вердиктом «стиль стабилен / не стабилен».

Человек смотрит только на contact sheets и итоговый отчёт. Всю рутину
и оценку делаешь ты.

---

## Входные данные

**Референсы:** 3 файла в `assets/references/`:
    ref_natasha.jpg
    ref_shipbuilder.jpg
    ref_navy.jpg
Все три передаются в **каждую** генерацию как reference images.

**Модель генерации:** `gemini-3-pro-image-preview` (Nano Banana Pro)
через `google-genai` SDK. Ключ — из переменной окружения `GOOGLE_API_KEY`.

**Модель оценки:** `gemini-flash-latest` (vision), тот же ключ.

**Параметры генерации:**
    aspect_ratio: "3:4"
    resolution: "2K"
    seed: не фиксировать (нужен разброс для оценки стабильности)

---

## Структура вывода

    experiments/sprint3_style/
    ├── brief_1_technosatire/
    │   ├── 01.png ... 10.png
    │   ├── scores.csv
    │   └── contact_sheet.jpg
    ├── brief_2_news_allegory/
    ├── brief_3_prof_holiday/
    ├── brief_4_birthday/
    ├── brief_5_absurd_domestic/
    ├── prompts/
    │   └── brief_N.txt          # финальный промпт каждого брифа
    ├── all_scores.csv
    └── REPORT.md

---

## Общая часть промпта (STYLE — идентична во всех 50 генерациях)

Вставляй этот блок дословно в начало каждого промпта. Это носитель
«руки художника» — не перефразировать, не сокращать.

    STYLE (must be preserved exactly, this is a recurring series
    by one illustrator):
    Dense hand-painted illustrated poster, gouache and watercolor
    on aged warm cream paper with visible paper grain and slightly
    darkened edges. Thin dark-brown ink contour of varying weight.
    Characters drawn in the tradition of 1970s-80s Soviet hand-drawn
    animation: big noses, expressive brows, lively readable poses.
    Machinery, tools and objects rendered detailed and believable —
    the deliberate contrast between cartoon characters and serious
    technical accuracy is essential.
    Palette: parchment cream base, terracotta, ochre, warm brown,
    muted red accents, naval blue and grey-blue. Warm soft light.
    Composition: banner headline across the top, main scene in the
    centre, a vertical stack of wooden signboards along one side,
    small side-gags and animal commentators in the corners,
    a moral line at the bottom.
    Highly detailed, many small readable props with tags and labels,
    rewarding close inspection.
    NEGATIVE: photorealism, 3D render, glossy CGI, flat vector
    infographic style, neon colours, pure white background,
    empty sterile background, Latin letters, invented glyphs,
    recognisable real politicians.

    RECURRING MASCOT "ПУЛЬС": a small tin robot, lamp-head glowing
    warm, brass rivets, a pulse dial on his chest. Present in every
    image, always holding something.

    TEXT RENDERING RULES (critical):
    Render every string below EXACTLY as given, in Cyrillic script.
    Do not transliterate. Do not invent letters. Do not add any text
    that is not on the list. Place text on wooden signboards, ribbons,
    chalk boards, spiral notebooks, tags and speech bubbles.

---

## Пять содержательных брифов

Каждый бриф = SCENE-блок, который добавляется после STYLE-блока.
Текстовый бюджет соблюдён: ≤ 7 блоков, ≤ 5 слов в блоке.

### БРИФ 1 — Техно-сатира (ядровой сценарий канала)

    SCENE: A cluttered old-fashioned office where AI assistants have
    taken over the paperwork. Three tin robots sit at wooden desks
    buried in paper, one is confidently stamping a document upside
    down. A tired human clerk in a knitted vest watches from behind
    a potted plant, holding a mug. The mascot ПУЛЬС stands on the
    desk holding a spiral notebook. A striped cat sits on top of the
    filing cabinet next to a mug. Wooden signboard column on the
    right. Chalk board on the left wall with a checklist.

    TEXT (render exactly):
    banner: "НЕЙРОСЕТЬ ВСЁ РЕШИЛА"
    sign 1: "ОШИБСЯ? НЕ ПОМЕХА!"
    sign 2: "СОГЛАСОВАНО. КЕМ - НЕЯСНО"
    chalkboard: "ПЛАН: 1. ДУМАТЬ 2. НЕ НАДО"
    cat bubble: "Я ЭТО НЕ ПОДПИСЫВАЛ"
    tag on stamp: "ПОЧТИ ТОЧНО"
    footer: "ЧЕЛОВЕК ЕЩЁ НУЖЕН. НАВЕРНОЕ."

### БРИФ 2 — Новостная аллегория через символы (тест редполитики)

    SCENE: A grand marble hall of an institution, but flooded
    ankle-deep with water. No human faces of officials — instead,
    tall empty ceremonial coats with medals stand upright on their
    own around a long table, conducting a meeting. A double-headed
    weathervane bird sits on the chandelier looking in two directions
    at once. A seagull stands on the table next to a stack of papers.
    The mascot ПУЛЬС wades through the water with a plunger over his
    shoulder. Wooden signboard column on the left. A spiral notebook
    lies on the table.

    TEXT (render exactly):
    banner: "ЗАСЕДАНИЕ ПРОДОЛЖАЕТСЯ"
    sign 1: "ВОДА? НЕ ПОМЕХА!"
    sign 2: "РЕШЕНИЕ ПРИНЯТО ЕДИНОГЛАСНО"
    notebook: "ВОПРОСЫ: 1. ЧЬЯ ВОДА 2. СНЯТО"
    seagull bubble: "ВСЁ ПО ПЛАНУ"
    tag: "ГЛУБИНА - В НОРМЕ"
    footer: "ГЛАВНОЕ - НЕ ТЕРЯТЬ ЛИЦО. ЕСЛИ ЕСТЬ."

### БРИФ 3 — Профессиональный праздник (продукт «плакаты на заказ», B2B)

    SCENE: A warm cluttered server room turned into a celebration.
    Three programmers in hoodies sit on office chairs among racks
    with blinking lights and tangled cables; one raises a mug like
    a toast, another sleeps with his head on the keyboard. A pizza
    box balances on a server rack. A striped cat lies across a warm
    server, a dog looks up at a signboard with total trust. The
    mascot ПУЛЬС hangs from a cable holding a wrench. Wooden
    signboard column on the right, chalk board on the left.

    TEXT (render exactly):
    banner: "С ДНЁМ ПРОГРАММИСТА!"
    sign 1: "УПАЛО? НЕ ПОМЕХА!"
    sign 2: "РАБОТАЕТ - НЕ ТРОГАЙ"
    chalkboard: "ГОТОВО: КОД, КОФЕ, ТЕРПЕНИЕ"
    cat bubble: "ГРЕЮ ПРОДАКШЕН"
    tag on cable: "НЕ ДЁРГАТЬ"
    footer: "256 ДЕНЬ ГОДА. НАШ ДЕНЬ."

### БРИФ 4 — Персональный день рождения (продукт «на заказ», портретность)

    SCENE: A sunny summer dacha garden. In the centre, a cheerful
    woman of about fifty in a straw hat and a light dress sits on a
    wooden bench holding an enormous bouquet of garden flowers, she
    is laughing. Around her: an overgrown vegetable bed, a wheelbarrow
    full of zucchini, a cat asleep in the wheelbarrow, a dog sitting
    at her feet, bumblebees over the flowers. The mascot ПУЛЬС stands
    on the bench arm holding a small cake with one candle. Wooden
    signboard column on the right, a spiral notebook on the bench.

    TEXT (render exactly):
    banner: "С ДНЁМ РОЖДЕНИЯ, НАТАША!"
    sign 1: "ГОДЫ? НЕ ПОМЕХА!"
    sign 2: "УРОЖАЙ ПРИНЯТ"
    notebook: "ПЛАНЫ: 1. КАБАЧКИ 2. ОТДЫХ"
    cat bubble: "ОХРАНЯЮ КАБАЧКИ"
    tag on wheelbarrow: "СНОВА КАБАЧКИ"
    footer: "ЦВЕТИ И НЕ ПЕРЕСАЖИВАЙСЯ!"

### БРИФ 5 — Бытовой абсурд (тест плотности и табличек)

    SCENE: A courtyard of an old apartment block during an endless
    repair. A trench crosses the yard with a plank thrown over it.
    Two workers in orange vests sit on the pipes drinking tea from
    a thermos, a third stands in the trench holding a shovel and a
    map upside down. An elderly resident in a cap leans out of a
    window shaking a fist. A fictional inspector in a peaked cap
    with a folder and a rubber stamp examines the plank. The mascot
    ПУЛЬС stands on the plank holding a lantern. A striped cat sits
    on the pipe, a seagull on the fence. Wooden signboard column on
    the left, chalk board leaning against the fence.

    TEXT (render exactly):
    banner: "РЕМОНТ ИДЁТ ПО ПЛАНУ"
    sign 1: "ЯМА? НЕ ПОМЕХА!"
    sign 2: "СРОК: ДО ЗИМЫ. КАКОЙ - НЕ УТОЧНЕНО"
    chalkboard: "СДЕЛАНО: ЯМА, ЧАЙ, ЗАБОР"
    cat bubble: "ТУТ БЫЛА КЛУМБА"
    tag on shovel: "ИНВЕНТАРЬ N7"
    footer: "КОПАЕМ ГЛУБЖЕ, ЧЕМ НАДО."

---

## Что реализовать: скрипт `generate.py`

Требования:
1. Загрузить 3 референса, передавать во все генерации.
2. Для каждого брифа: собрать промпт `STYLE + SCENE`, сохранить в
   `prompts/brief_N.txt`, сгенерировать 10 изображений в `NN.png`.
3. Параллелизм ≤ 2 запроса одновременно; retry 3 попытки
   с экспоненциальной паузой; таймаут 120 сек.
4. Логировать в консоль: бриф, номер, латентность, стоимость,
   накопленный итог. Ориентир стоимости: ~$0.134 за 2K-изображение,
   ожидаемый бюджет всего эксперимента ≈ $7.
5. Идемпотентность: если файл уже есть — не перегенерировать
   (флаг `--force` для перезаписи).
6. Флаг `--brief N` для прогона одного брифа, `--count M` для числа вариантов.

---

## Что реализовать: скрипт `evaluate.py`

Для каждого изображения вызвать vision-модель со следующим запросом
и получить строгий JSON:

    Ты — арт-директор, проверяющий консистентность серии иллюстраций
    одного художника. Тебе даны эталонные работы серии (первые
    изображения) и одна проверяемая работа (последнее изображение).

    Оцени проверяемую работу по шкале 1-10 по каждому критерию:
    c1_technique   — похоже на гуашь/акварель по старой бумаге, не CG
    c2_palette     — тёплая пергаментная база, терракота, охра, синий
    c3_line        — тонкий контур, пластика советской анимации 70-80х
    c4_composition — баннер сверху, центр, колонка табличек, периферия
    c5_density     — много мелких подписанных предметов и деталей
    c6_cyrillic    — все надписи читаемы, без латиницы и выдуманных букв
    c7_checklist   — есть баннер, 2+ таблички, чек-лист, животное
                     с репликой, пасхалки, строка-мораль
    c8_tone        — тёплая ирония, не злая карикатура

    Дополнительно:
    mascot_present    — есть ли жестяной робот с лампой-головой (true/false)
    text_found        — список всех надписей, которые ты видишь, дословно
    anti_patterns     — список нарушений из: photorealism, 3d, glossy,
                        vector_flat, neon, white_background, latin_letters,
                        garbled_letters, empty_background
    verdict           — одна фраза: похоже ли, что это тот же художник

    Верни ТОЛЬКО JSON без пояснений.

Затем:
1. Сверить `text_found` с ожидаемым списком строк брифа: нормализация
   (верхний регистр, ё→е, схлопывание пробелов), затем нормализованное
   расстояние Левенштейна. Посчитать `text_match` = доля строк
   со score ≥ 0.9.
2. Записать `scores.csv` в папке брифа и общий `all_scores.csv`
   с колонками: brief, file, c1..c8, mascot_present, text_match,
   style_score, anti_patterns, verdict.
3. `style_score` = среднее(c1, c2, c3, c4, c5, c8).

---

## Что реализовать: `contact_sheet.py`

Для каждого брифа собрать сетку 5×2 из превью (Pillow), под каждым
превью подписать: номер, `style_score`, `text_match`, флаг
анти-паттернов. Сохранить `contact_sheet.jpg` (ширина 2400 px).
Плюс общий `contact_sheet_all.jpg` — по 3 лучших из каждого брифа.

---

## Итоговый отчёт `REPORT.md`

Сгенерировать автоматически, включить:
1. **Вердикт** по порогу приёмки: стиль считается стабильным, если
   **≥ 8 из 10 изображений в каждом брифе** имеют
   `style_score ≥ 7.5` И `text_match ≥ 0.8`.
2. Таблица по брифам: средний style_score, медиана, разброс
   (min/max), средний text_match, доля прошедших порог,
   доля с присутствующим маскотом.
3. Таблица по критериям C1–C8: средний балл по всем 50 работам.
   **Это главное диагностическое место** — показывает, что именно
   ломается: палитра, композиция или текст.
4. Топ-3 частых анти-паттерна с числом срабатываний.
5. Отдельный раздел «Проблемы с кириллицей»: список всех случаев,
   где `text_match < 0.8`, с указанием ожидалось/распознано.
6. Сравнение брифов между собой: на какой теме стиль держится хуже
   всего и гипотеза почему.
7. **Рекомендации по правке STYLE-блока** — какие формулировки усилить,
   исходя из самых низких критериев.

---

## Порядок выполнения

1. Создай структуру папок и скрипты.
2. Прогони `generate.py --brief 1 --count 2` как smoke-test,
   покажи результат и подтверждённую стоимость, останановись
   и дай мне взглянуть.
3. После моего «ок» — полный прогон всех 5 брифов по 10 вариантов.
4. Прогони `evaluate.py`, затем `contact_sheet.py`.
5. Сгенерируй `REPORT.md` и выведи вердикт в консоль.

## Требования к коду
- Python 3.12, type hints, `google-genai`, Pillow, pandas.
- Ключи только из переменных окружения, `.env` в `.gitignore`.
- Никаких хардкоженных путей — всё через `pathlib` от корня эксперимента.
- Скрипты переиспользуемы: брифы вынести в `briefs.yaml`, STYLE-блок
  в `style_block.txt`, чтобы правки не требовали изменения кода.
- Весь код и отчёт — в `experiments/sprint3_style/`.