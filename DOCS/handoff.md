# 📋 Передаточный документ проекта Pulse («Пульс Дня») — Handoff Document

**Версия:** 4.1  
**Дата обновления:** 9 августа 2026 г.  
**Цель проекта:** Ежедневный генеративный сатирико-позитивный дайджест-плакат в Telegram (`@a_daily_pulse`), ВКонтакте (`a_daily_pulse`) и на интерактивном веб-сайте отрывного календаря (`http://192.109.206.42:8081`).

---

## 1. 🚀 Что полностью сделано и работает

### 1.1 Бэкенд и Сбор новостей
- **24-часовое плавающее окно (18:00 ➔ 18:00 МСК):** новости собираются круглосуточно каждый час из 6 категорий RSS/Telegram-лент.
- **Единый источник праздников (`calend_ru`):**
  - **Адаптер `CalendRuAdapter` (`src/pulse/sources/rss.py`):** извлекает RSS-ленту `calend.ru`, строго фильтрует её по текущему дню (МСК, UTC+3) и объединяет все праздники за день в **одну единственную новость** со структурированным заголовком (*«Праздники сегодня: [Праздник 1], [Праздник 2]...»*).
  - **Замена старой записи (`src/pulse/jobs/intake.py`):** при каждом запуске `run_fetch_job()` для источника `calend_ru` перед сохранением удаляется предыдущая запись. Это гарантирует, что в БД находится **ровно 1 актуальная новость о праздниках**.
  - **Байпасс LLM-оценки (`src/pulse/digest/llm.py`):** для `calend_ru` нейросетевая оценка не вызывается, а сразу выставляются максимальные значения (`virality = 10, relevance = 4, significance = 3`), защищая от ошибок модели (например, от ложного отсечения из-за слов вроде "памяти", "битвы").
- **Двухфазный нейроскоринг через Groq API (PRIMARY):**
  - **Фаза 1**: Классификация сентимента (`positive`/`negative`/`neutral`) + перевод заголовков на русский для ВСЕХ новостей.
  - **Фаза 2**: Оценка виральности/релевантности/значимости ТОЛЬКО для положительных и нейтральных новостей (экономия 30-50% токенов).
  - **Каскад fallback**: Groq (`llama-3.1-8b-instant`) → Gemini (`gemini-2.0-flash`) → Heuristic (ключевые слова).
- **Динамический SQL-выбор ТОП-15 новостей:** динамический отбор лучших позитивных новостей за 24 часа за 0.1 секунды.

### 1.2 LLM-провайдеры и API ключи

| Роль | Провайдер | Модель | Переменная `.env` |
|---|---|---|---|
| **PRIMARY** | Groq | `llama-3.1-8b-instant` | `GROQ_API_KEY=gsk_ptO...eG6` |
| **FALLBACK** | Google Gemini | `gemini-2.0-flash` | `GEMINI_API_KEY=AIza...dis` |

> 📖 Подробная документация по LLM-паттерну: [`DOCS/llm_scoring_pattern.md`](file:///Users/yuri/Projects/pulse/DOCS/llm_scoring_pattern.md)

### 1.3 Авторский процесс и Форматирование
- **18:00 МСК — Рассылка дайджеста автору (`pulse.jobs.daily`):** в 18:00 МСК (15:00 UTC) автору (`@anta9onist`) в личку Telegram присылается готовый текст 15 новостей с **полными кликабельными заголовками** со ссылками на первоисточники для рисования плаката.
- **Загрузка обложки в 3 размерах (`admin.py` + `site_publisher.py`):** при отправке картинки автору мгновенно генерируются 3 WebP-версии (`cover.webp` 2K, `thumb-480.webp`, `thumb-128.webp`), загружаются в Supabase Storage `pulse-covers` и формируется мгновенный предпросмотр с кнопкой `[ ✅ Подтвердить публикацию в 20:00 ]`.
- **Адаптивная команда `/post`:** при наличии обложки показывает предпросмотр с кнопкой подтверждения, при отсутствии — высылает самый свежий текст 15 новостей с названиями и ссылками.

### 1.4 Мультиплатформенная автопубликация в 20:00 МСК
- **Изолированный оркестратор (`MultiPublisherOrchestrator`):** публикации в Telegram-канал (`@a_daily_pulse`), ВКонтакте (`a_daily_pulse`) и на Веб-сайт изолированы через `asyncio.gather(..., return_exceptions=True)`.
- **ВКонтакте интеграция (`VKPublisher`):** конверсия в 1600px JPEG (`quality=88`), прикрепление нативной 2K-картинки через `photo{owner_id}_{id}_{access_key}` и явные URL-ссылки источников.
- **Отложенная публикация в 20:00 МСК (`pulse.jobs.auto_publish`):** cron-задача в 20:00 МСК (17:00 UTC) публикует готовый выпуск во все каналы.
- **Напоминание в 19:30 МСК (`pulse.jobs.remind_publish`):** cron-задача в 19:30 МСК (16:30 UTC) присылает напоминание, если обложка загружена, но кнопка подтверждения не нажата.
- **Защита от дублирования (Идемпотентность):** статус `status = 'published'` гарантирует, что выпуск выйдет строго 1 раз.

### 1.5 Серверное окружение (`Etc/UTC`) и Cron
```cron
30 * * * *  — pulse.jobs.intake fetch   (Каждый час в XX:30: сбор новостей)
45 * * * *  — pulse.jobs.intake score   (Каждый час в XX:45: двухфазный Groq-скоринг)
0 15 * * *  — pulse.jobs.daily          (18:00 МСК / 15:00 UTC: авто-рассылка 15 новостей автору)
30 16 * * * — pulse.jobs.remind_publish (19:30 МСК / 16:30 UTC: авто-напоминание)
0 17 * * *  — pulse.jobs.auto_publish   (20:00 МСК / 17:00 UTC: автопубликация в TG + VK + Сайт)
```
> 💡 *Правило:* Сервер работает в UTC. Любое расписание по МСК вычисляется как `MSK_HOUR - 3`.

### 1.6 Эксперимент: Отключение свежести новостей (Freshness Score)
- **Текущий статус**: В [`src/pulse/digest/ranker.py`](file:///Users/yuri/Projects/pulse/src/pulse/digest/ranker.py) временное начисление баллов за свежесть (`freshness_score` +0..+6) **отключено** (`freshness_score = 0`). Итоговый `total_score` формируется исключительно из чистой оценки качества `quality_score`.
- 📌 **НАПОМИНАНИЕ (12 августа 2026 г.)**:
  - Оценить качество ранжирования за последние несколько дней.
  - Если ранжирование без свежести устроит — вычистить из кода и базы все неиспользуемые механизмы вычисления свежести для снижения нагрузки на сервер.
  - Если качество ухудшится — вернуть начисление `freshness_score`.

---

## 2. 📁 Размещение ключевых файлов проекта

| Компонент | Путь к файлу |
|---|---|
| **Двухфазный LLM-скоринг** | [`src/pulse/digest/llm.py`](file:///Users/yuri/Projects/pulse/src/pulse/digest/llm.py) |
| **Конфигурация (Groq/Gemini ключи)** | [`src/pulse/config.py`](file:///Users/yuri/Projects/pulse/src/pulse/config.py) |
| **Telegram-бот** | [`src/pulse/bot/main.py`](file:///Users/yuri/Projects/pulse/src/pulse/bot/main.py) |
| **Хендлеры администратора** | [`src/pulse/bot/handlers/admin.py`](file:///Users/yuri/Projects/pulse/src/pulse/bot/handlers/admin.py) |
| **Формирование текста новостей** | [`src/pulse/publisher/caption.py`](file:///Users/yuri/Projects/pulse/src/pulse/publisher/caption.py) |
| **Мультиплатформенный публикатор** | [`src/pulse/publisher/orchestrator.py`](file:///Users/yuri/Projects/pulse/src/pulse/publisher/orchestrator.py) |
| **Публикатор ВКонтакте** | [`src/pulse/publisher/vk.py`](file:///Users/yuri/Projects/pulse/src/pulse/publisher/vk.py) |
| **Публикация на сайте & 3 размера** | [`src/pulse/publisher/site_publisher.py`](file:///Users/yuri/Projects/pulse/src/pulse/publisher/site_publisher.py) |
| **Автопубликация 20:00 МСК** | [`src/pulse/jobs/auto_publish.py`](file:///Users/yuri/Projects/pulse/src/pulse/jobs/auto_publish.py) |
| **Напоминание 19:30 МСК** | [`src/pulse/jobs/remind_publish.py`](file:///Users/yuri/Projects/pulse/src/pulse/jobs/remind_publish.py) |
| **Рассылка 18:00 МСК** | [`src/pulse/jobs/daily.py`](file:///Users/yuri/Projects/pulse/src/pulse/jobs/daily.py) |
| **Паттерн LLM-скоринга (документация)** | [`DOCS/llm_scoring_pattern.md`](file:///Users/yuri/Projects/pulse/DOCS/llm_scoring_pattern.md) |
| **Правила деплоя и часовых поясов** | [`.agents/DEPLOY_RULES.md`](file:///Users/yuri/Projects/pulse/.agents/DEPLOY_RULES.md) |

