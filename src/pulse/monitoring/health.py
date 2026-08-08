"""System health watchdog for monitoring Supabase DB, individual RSS/Telegram feeds silence, and LLM API errors."""

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from aiogram import Bot

from pulse.config import get_config
from pulse.db.client import get_supabase_client
from pulse.logging import get_logger
from pulse.sources.registry import SourceRegistry

logger = get_logger("pulse.monitoring.health")

STATE_FILE = Path("/tmp/pulse_watchdog_state.json")


def get_admin_chat_id() -> int | str | None:
    cfg = get_config().settings
    if cfg.ADMIN_CHAT_ID and cfg.ADMIN_CHAT_ID != 123456789:
        return cfg.ADMIN_CHAT_ID
    try:
        client = get_supabase_client()
        res = client.table("users").select("telegram_id, username").execute()
        for u in (res.data or []):
            if u.get("username") and str(u.get("username")).lower() == "anta9onist":
                return u.get("telegram_id")
            if u.get("telegram_id"):
                return u.get("telegram_id")
    except Exception:
        pass
    return None


class SystemWatchdog:
    """Monitors system health, per-feed silence (>3h), Supabase activity, and LLM API status."""

    def __init__(self, silence_hours: int = 3, cooldown_minutes: int = 15) -> None:
        self.silence_hours = silence_hours
        self.cooldown_seconds = cooldown_minutes * 60
        self.state: dict[str, Any] = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except Exception:
                pass
        return {"active_alerts": {}, "last_alert_times": {}}

    def _save_state(self) -> None:
        try:
            STATE_FILE.write_text(json.dumps(self.state, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error("failed_to_save_watchdog_state", error=str(e))

    def check_supabase_health(self) -> tuple[bool, str | None]:
        """Ping Supabase DB to ensure activity and prevent project pause."""
        try:
            client = get_supabase_client()
            res = client.table("news_items").select("id").limit(1).execute()
            if res.data is not None:
                return True, None
            return False, "Supabase вернул пустой ответ при проверке здоровья."
        except Exception as e:
            return False, f"Ошибка подключения к Supabase DB: {e}"

    def check_feed_silence(self) -> list[tuple[str, str, float]]:
        """Check all ENABLED feeds for silence > silence_hours.

        Returns:
            list[tuple[source_id, source_name, hours_silent]]
        """
        silent_feeds: list[tuple[str, str, float]] = []
        try:
            client = get_supabase_client()
            registry = SourceRegistry.load_from_config()
            enabled_adapters = registry.get_all()
            enabled_sources = {a.source_id: getattr(a, "name", a.source_id) for a in enabled_adapters}

            if not enabled_sources:
                return []

            res = client.table("news_items").select("source_id, collected_at").order("collected_at", desc=True).limit(500).execute()
            rows = res.data or []

            latest_by_source: dict[str, datetime] = {}
            for row in rows:
                sid = str(row.get("source_id"))
                if sid in enabled_sources and sid not in latest_by_source:
                    cat_str = row.get("collected_at")
                    if cat_str:
                        dt = datetime.fromisoformat(cat_str.replace("Z", "+00:00"))
                        latest_by_source[sid] = dt

            now = datetime.now(timezone.utc)
            for sid, sname in enabled_sources.items():
                last_dt = latest_by_source.get(sid)
                if last_dt is None:
                    silent_feeds.append((sid, sname, 99.0))
                else:
                    hours_silent = (now - last_dt).total_seconds() / 3600.0
                    if hours_silent >= self.silence_hours:
                        silent_feeds.append((sid, sname, hours_silent))

        except Exception as e:
            logger.error("feed_silence_check_failed", error=str(e))

        return silent_feeds

    async def run_health_checks(self) -> list[str]:
        """Run all watchdog checks and send throttled alerts/recovery messages to admin Telegram."""
        cfg = get_config().settings
        bot = Bot(token=cfg.TELEGRAM_BOT_TOKEN)
        admin_chat = get_admin_chat_id()

        notifications: list[str] = []
        now_ts = datetime.now(timezone.utc).timestamp()

        # 1. Supabase Check
        db_ok, db_err = self.check_supabase_health()
        alert_key_db = "supabase_db"
        if not db_ok:
            if self._should_send_alert(alert_key_db, now_ts):
                msg = f"⚠️ **Алерт системы:** {db_err}"
                notifications.append(msg)
                self.state["active_alerts"][alert_key_db] = db_err
                self.state["last_alert_times"][alert_key_db] = now_ts
        else:
            if alert_key_db in self.state["active_alerts"]:
                msg = "✅ **Проблема устранена:** Подключение к БД Supabase восстановлено!"
                notifications.append(msg)
                del self.state["active_alerts"][alert_key_db]

        # 2. Feed Silence Check per enabled feed
        silent_feeds = self.check_feed_silence()
        current_silent_sids = {sid for sid, _, _ in silent_feeds}

        for sid, sname, hrs in silent_feeds:
            alert_key_feed = f"feed_silence_{sid}"
            hrs_str = "более 24" if hrs > 24 else f"{hrs:.1f}"
            err_msg = f"С RSS-ленты **«{sname}»** (ID: `{sid}`) уже **{hrs_str} ч.** не поступают новости!"
            if self._should_send_alert(alert_key_feed, now_ts):
                msg = f"⚠️ **Алерт источника:** {err_msg}"
                notifications.append(msg)
                self.state["active_alerts"][alert_key_feed] = err_msg
                self.state["last_alert_times"][alert_key_feed] = now_ts

        # Check for recovered feeds
        prev_feed_alerts = [k for k in list(self.state["active_alerts"].keys()) if k.startswith("feed_silence_")]
        for k in prev_feed_alerts:
            sid = k.replace("feed_silence_", "")
            if sid not in current_silent_sids:
                msg = f"✅ **Проблема устранена:** Поступление новостей с ленты `{sid}` восстановлено!"
                notifications.append(msg)
                del self.state["active_alerts"][k]

        self._save_state()

        # Dispatch notifications to Admin Chat
        if notifications and admin_chat:
            for text in notifications:
                try:
                    await bot.send_message(chat_id=admin_chat, text=text, parse_mode="Markdown")
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.error("failed_to_send_alert", error=str(e))

        return notifications

    def _should_send_alert(self, key: str, now_ts: float) -> bool:
        last_time = self.state["last_alert_times"].get(key, 0)
        return (now_ts - last_time) >= self.cooldown_seconds
