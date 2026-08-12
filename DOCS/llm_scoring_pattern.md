# 📚 Паттерн: Двухфазная LLM-классификация новостей (Groq + Gemini)

> **Переиспользуемый паттерн** для любого проекта, требующего массовой классификации текстов через бесплатные LLM API.

---

## Провайдеры и модели

| Роль | Провайдер | Модель | Лимиты (бесплатно) | Эндпоинт |
|---|---|---|---|---|
| **PRIMARY** | Groq | `llama-3.1-8b-instant` | 14 400 RPD / 30 RPM / 30K TPM | `https://api.groq.com/openai/v1/chat/completions` |
| **FALLBACK** | Google Gemini | `gemini-2.0-flash` | ~1500 RPD / 15 RPM / 1M TPM | `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` |
| **EMERGENCY** | Heuristic | — | ∞ | Локально, по ключевым словам |

### Получение API ключей

| Провайдер | URL | Время | Что нужно |
|---|---|---|---|
| **Groq** | [console.groq.com](https://console.groq.com) | 30 сек | Google-аккаунт |
| **Gemini** | [aistudio.google.com](https://aistudio.google.com/apikey) | 30 сек | Google-аккаунт |

---

## Архитектура двухфазной оценки

```
 ═══════════ ФАЗА 1: Сентимент + перевод (ВСЕ элементы) ═══════════

  N элементов ──► LLM: "sentiment + ru_title" (чанки по 30)
                    │
         negative (30-50%) ──► ОТСЕЧЬ (экономия на Фазе 2)
         positive/neutral  ──► передать в Фазу 2

 ═══════════ ФАЗА 2: Детальная оценка (ТОЛЬКО positive/neutral) ════

  ~50-70% элементов ──► LLM: "virality + relevance + significance"
```

### Почему 2 фазы, а не 1?
- **Экономия 30-50% токенов**: негативные элементы не проходят через детальную оценку
- **Чище разделение ответственности**: простой промпт = надёжнее ответ от дешёвой модели
### Специфические байпассы (Short-circuits)
- **Праздники (`calend_ru`)**: Объединённая запись о праздниках обходит обе фазы LLM-оценки. Ей превентивно присваивается `virality = 10, relevance = 4, significance = 3`, чтобы исключить ошибочное отсечение моделью из-за отдельных слов в названии праздников (например, "битвы", "памяти", "погибших").

---


## Промпты

### Фаза 1 — Сентимент с CoT-рассуждением (~250 токенов системный промпт)
```text
Ты строгий главный редактор позитивного журнала "ПУЛЬС ДНЯ".

Проанализируй заголовок каждой новости и строго определи ее эмоциональный сентимент (sentiment):
- "positive": радостные события, вдохновляющие истории (проснулся из комы, спасся, победил), научные рекорды, анонсы игр/фильмов, курьёзы.
- "negative": ЛЮБЫЕ трагедии, гибель людей, смертельные ДТП, поджоги, насилие, убийства, преступления — ДАЖЕ ЕСЛИ заголовок написан сухим языком.
- "neutral": только сухие финансово-статистические или официальные сводки.

Верни строго JSON-массив с обязательным полем "reasoning" (краткое пояснение 3-5 слов):
[{"id":"...","reasoning":"...","sentiment":"positive|negative|neutral","ru_title":"..."}]
```


### Фаза 2 — Виральность (~100 токенов системный промпт)
```
Оцени каждую новость по 3 критериям:
1. virality (-10..+10): желание поделиться с друзьями
2. relevance (1-5): интересность для массового читателя
3. significance (1-5): масштаб события

Верни строго JSON-массив: [{"id":"...","virality":...,"relevance":...,"significance":...}]
Не добавляй пояснений.
```

---

## Вызов Groq API (Python, httpx)

```python
import httpx

response = httpx.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.1,
        "max_tokens": 4000,
        "response_format": {"type": "json_object"},
    },
    timeout=30.0,
)
```

### Особенности Groq API:
- **OpenAI-совместимый формат** — тот же `chat/completions`
- **`response_format: {"type": "json_object"}`** — гарантирует JSON в ответе
- **Ответ может быть обёрнут в объект**: `{"news": [...]}` или `{"results": [...]}`
- **429 Rate Limit**: ждать `5 * (retry + 1)` секунд, до 3 попыток

---

## Каскад fallback

```python
def _call_llm(system_prompt, user_msg):
    # 1. Try Groq (PRIMARY)
    result = _call_groq(system_prompt, user_msg)
    if result: return result

    # 2. Try Gemini (FALLBACK)
    result = _call_gemini(system_prompt, user_msg)
    if result: return result

    # 3. Heuristic (EMERGENCY)
    return None  # caller uses keyword-based heuristic
```

---

## Результаты тестирования (8 августа 2026)

| Метрика | Groq `llama-3.1-8b-instant` |
|---|---|
| Точность сентимента | **92%** (12/13) |
| 100% трагедий верно | ✅ |
| Качество перевода EN→RU | 4/5 отлично |
| Время ответа (15 новостей) | **1.3 сек** |
| Токены (15 новостей) | 1232 |

---

## Переменные окружения

```env
# .env
GROQ_API_KEY=gsk_...          # Groq (PRIMARY)
GEMINI_API_KEY=AIzaSy...       # Gemini (FALLBACK)
```
