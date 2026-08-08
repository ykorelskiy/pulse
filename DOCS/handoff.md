# 📋 Передаточный документ проекта Pulse («Пульс Дня») — Handoff Document

**Версия:** 3.0  
**Дата обновления:** 8 августа 2026 г.  
**Цель проекта:** Ежедневный генеративный сатирико-позитивный дайджест-плакат в Telegram (`@a_daily_pulse`), ВКонтакте (`a_daily_pulse`) и на интерактивном веб-сайте отрывного календаря (`http://192.109.206.42:8081`).

---

## 1. 🚀 Что полностью сделано и работает

### 1.1 Бэкенд и Сбор новостей
- **24-часовое плавающее окно (18:00 ➔ 18:00 МСК):** новости собираются круглосуточно каждый час из 6 категорий RSS/Telegram-лент.
- **Нейроскоринг и фильтрация Gemini:** дедупликация по хэшу `headline_hash`, жесткая отбраковка новостей с жертвами (`has_victims = true`), перевод зарубежных новостей.
- **Динамический SQL-выбор ТОП-15 новостей:** динамический отбор лучших позитивных новостей за 24 часа за 0.1 секунды.

### 1.2 Авторский процесс и Форматирование
- **18:00 МСК — Рассылка дайджеста автору (`pulse.jobs.daily`):** в 18:00 МСК автору (`@anta9onist`) в личку Telegram присылается готовый текст 15 новостей со ссылками на первоисточники для рисования плаката.
- **Загрузка обложки в 3 размерах (`admin.py` + `site_publisher.py`):** при отправке картинки автору мгновенно генерируются 3 WebP-версии (`cover.webp` 2K, `thumb-480.webp`, `thumb-128.webp`), загружаются в Supabase Storage `pulse-covers` и формируется мгновенный предпросмотр с кнопкой `[ ✅ Подтвердить публикацию в 20:00 ]`.
- **Адаптивная команда `/post`:** при наличии обложки показывает предпросмотр с кнопкой подтверждения, при отсутствии — высылает самый свежий текст 15 новостей.

### 1.3 Мультиплатформенная автопубликация в 20:00 МСК
- **Изолированный оркестратор (`MultiPublisherOrchestrator`):** публикации в Telegram-канал (`@a_daily_pulse`), ВКонтакте (`a_daily_pulse`) и на Веб-сайт изолированы через `asyncio.gather(..., return_exceptions=True)`. Сбой на одной площадке не блокирует остальные.
- **ВКонтакте интеграция (`VKPublisher`):** автоматическая конверсия в 1600px JPEG (`quality=88`) через Pillow для устранения таймаутов VK API, прикрепление нативной 2K-картинки через `photo{owner_id}_{id}_{access_key}` и явные URL-ссылки источников.
- **Отложенная публикация в 20:00 МСК (`pulse.jobs.auto_publish`):** cron-задача в 20:00 МСК публикует готовый выпуск во все каналы.
- **Напоминание в 19:30 МСК (`pulse.jobs.remind_publish`):** если обложка загружена, но кнопка подтверждения не нажата, бот присылает напоминание.
- **Защита от дублирования (Идемпотентность):** статус `status = 'published'` и отметка `published_at` гарантируют, что выпуск выйдет строго 1 раз даже при повторном вызове скрипта.

### 1.4 Веб-витрина «Интерактивный отрывной календарь» (Port 8081)
- **Скеоморфный дизайн:** деревянный стол, советская газетная бумага, рукописные шрифты (`Neucha`, `Caveat`).
- **Фирменный фавикон:** подмигивающий робот ПУЛЬС с загнутым уголком календаря (`favicon.png`, `favicon.ico`), чётко читаемый в мелких вкладках браузера.
- **Новостная панель:** пропорциональное уменьшение листа (`scale(0.68)`), 15 новостей в 1 колонку без скроллинга на 720px.

### 1.5 Серверное окружение и Строгие правила деплоя
- **Бот управляется через PM2 (`pulse-bot`):** перезапуск строго через `pm2 restart pulse-bot`.
- **Строгий чек-лист деплоя (`.agents/DEPLOY_RULES.md`):** обязательный runtime-импорт (`python -c "import module"`) перед зашивкой, предрелизное согласование `implementation_plan.md` с автором.
- **Cron-задачи на сервере (`192.109.206.42`):**
  ```cron
  0 * * * *   — intake (сбор новостей, скоринг)
  0 18 * * *  — daily (рассылка 15 новостей автору в 18:00 МСК)
  30 16 * * * — remind_publish (напоминание в 19:30 МСК)
  0 17 * * *  — auto_publish (автопубликация во все каналы в 20:00 МСК)
  ```

---

## 2. 📁 Размещение ключевых файлов проекта

| Компонент | Путь к файлу |
|---|---|
| **Telegram-бот** | [`src/pulse/bot/main.py`](file:///Users/yuri/Projects/pulse/src/pulse/bot/main.py) |
| **Хендлеры администратора** | [`src/pulse/bot/handlers/admin.py`](file:///Users/yuri/Projects/pulse/src/pulse/bot/handlers/admin.py) |
| **Мультиплатформенный публикатор** | [`src/pulse/publisher/orchestrator.py`](file:///Users/yuri/Projects/pulse/src/pulse/publisher/orchestrator.py) |
| **Публикатор ВКонтакте** | [`src/pulse/publisher/vk.py`](file:///Users/yuri/Projects/pulse/src/pulse/publisher/vk.py) |
| **Публикация на сайте & 3 размера** | [`src/pulse/publisher/site_publisher.py`](file:///Users/yuri/Projects/pulse/src/pulse/publisher/site_publisher.py) |
| **Автопубликация 20:00 МСК** | [`src/pulse/jobs/auto_publish.py`](file:///Users/yuri/Projects/pulse/src/pulse/jobs/auto_publish.py) |
| **Напоминание 19:30 МСК** | [`src/pulse/jobs/remind_publish.py`](file:///Users/yuri/Projects/pulse/src/pulse/jobs/remind_publish.py) |
| **Рассылка 18:00 МСК** | [`src/pulse/jobs/daily.py`](file:///Users/yuri/Projects/pulse/src/pulse/jobs/daily.py) |
| **Веб-витрина (React/Vite)** | [`site/`](file:///Users/yuri/Projects/pulse/site/) |
| **Правила деплоя и проверки** | [`.agents/DEPLOY_RULES.md`](file:///Users/yuri/Projects/pulse/.agents/DEPLOY_RULES.md) |

---

## 3. ⚙️ Команды управления на сервере

```bash
# Проверить статус процессов PM2
ssh root@192.109.206.42 "pm2 list"

# Перезапустить бота после правок
ssh root@192.109.206.42 "cd /var/www/pulse && git pull && pm2 restart pulse-bot"

# Пересборка веб-витрины
ssh root@192.109.206.42 "cd /var/www/pulse && git pull && cd site && npm run build && systemctl restart pulse-site"

# Проверить логи автопубликации 20:00
ssh root@192.109.206.42 "cat /var/log/pulse-publish.log"
```
