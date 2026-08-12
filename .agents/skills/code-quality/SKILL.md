---
name: code-quality
description: |
  Universal Code Quality, Security & Architecture Auditor for Python, TypeScript, and Supabase projects.
  Enforces zero-secret leaks, mandatory Supabase RLS security, runtime import validation, and anti-swallowing error logging.
  Portable across all project workspaces by copying the `.agents/skills/code-quality` folder.

  Triggers: "quality check", "verify code", "check security", "проверь качество", "аудит кода", "качество кода"
---

# Code Quality & Security Skill

Универсальный переносимый скилл качества и безопасности кода для проектов на **Python, React/TypeScript и Supabase**.

Этот скилл предназначен для предотвращения развертывания нестабильного или уязвимого кода. Его директорию (`.agents/skills/code-quality/`) можно скопировать в любой другой проект Antigravity / Claude Code.

---

## 5 Слоев проверки качества

### 1. Безопасность баз данных (Supabase RLS & Keys)
- **RLS по умолчанию:** Любой `CREATE TABLE` в SQL-миграциях или DDL обязан сопровождаться `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`.
- **Изоляция ключей:**
  - На клиенте (фронтенд) — только `anon` / publishable key с ограниченными RLS-политиками.
  - На сервере (бэкенд) — использовать `service_role` key (обходит RLS). `service_role` ключ **запрещено** отдавать клиенту.

### 2. Runtime-импорты и типы (Python / TypeScript)
- **Синтаксис != Валидность:** Проверка `py_compile` недостаточна (она не выявляет `NameError` или незаимпортированные символы).
- **Runtime Import Check:** Перед каждым деплоем выполнять запуск `python -c "import <module>"` для всех ключевых точек входа (`main.py`, `client.py`, `handlers`).
- **Строгая типизация:** Использовать explicit аннотации типов (`dict[str, Any]`, `Optional`, `Union`) и проверку `mypy` / `tsc --noEmit`.

### 3. Запрет скрытия ошибок (Anti-Swallowing)
- **Запрещено:** Неиспользуемый блок `except Exception: pass` или `except: pass` без логирования.
- **Разрешено:** Если ошибка действительно ожидаема и должна игнорироваться — использовать `with contextlib.suppress(Exception):` либо обязательный `logger.warning(...)` / `logger.exception(...)`.

### 4. Контроль секретов (Secret Leak Prevention)
- **Отсутствие хардкода:** Запрещено коммитить настоящие API-ключи (Telegram Bot Token, VK Token, R2 Secrets, JWT Tokens).
- Все ключи должны загружаться строго из `.env` через `pydantic-settings` или `process.env`.
- Шаблон `.env.example` должен поддерживаться в актуальном состоянии без секретных значений.

### 5. Безопасность деплоя и процессов (Deploy Rules)
- **Управление процессом:** Использование только PM2 (`pm2 restart <name>`) на сервере для фоновых процессов. Запрещено использовать `nohup` или `kill -9`, приводящие к созданию процессов-зомби.
- **Проверка логов после перезапуска:** Обязательный просмотр `pm2 logs --lines 20 --nostream` на предмет ошибок при старте.

---

## Автоматическая проверка (Запуск скрипта)

Для запуска автоматической автопроверки выполните:

```bash
python3 .agents/skills/code-quality/scripts/verify_quality.py
```

Скрипт вернёт статус `0` при успешном прохождении всех проверок или список `CRITICAL` / `WARNING` замечаний с указанием строк кода.
