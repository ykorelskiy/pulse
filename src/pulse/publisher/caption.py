"""Post caption builder for Telegram channel."""

from datetime import datetime
import zoneinfo

MSK_TZ = zoneinfo.ZoneInfo("Europe/Moscow")


class CaptionBuilder:
    """Builds channel post captions including daily top news and site links."""

    def build_caption(
        self,
        date_str: str,
        title: str | None = None,
        news_items: list[dict] | None = None,
        site_url: str = "http://192.109.206.42:8081",
    ) -> str:
        """Build formatted Telegram channel post caption.

        Args:
            date_str: Date string YYYY-MM-DD.
            title: Title of issue.
            news_items: List of news item dicts.
            site_url: Public showcase website URL.

        Returns:
            str: Telegram post caption text.
        """
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = dt.strftime("%d.%m.%Y")
        [year, month, day] = date_str.split("-")

        lines = []
        lines.append(f"🖼 **ПУЛЬС ДНЯ — {formatted_date}**")
        lines.append("")
        lines.append("📌 **Главные позитивные новости дня:**")

        if news_items:
            # Format top 15 news items for channel post
            for idx, item in enumerate(news_items[:15], 1):
                text = item.get("text", "")
                url = item.get("url", "")
                if url:
                    lines.append(f"{idx}. [{text}]({url})")
                else:
                    lines.append(f"{idx}. {text}")
        else:
            lines.append("Ежедневный выпуск отрывного календаря.")

        lines.append("")
        lines.append(f"📅 Смотреть интерактивный отрывной календарь [тут]({site_url}/{year}/{month}/{day})")
        lines.append("")
        lines.append("💬 Подписаться на ежедневные позитивные новости [тут](https://t.me/a_daily_pulse)")

        return "\n".join(lines)
