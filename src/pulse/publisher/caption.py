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
                raw_text = item.get("headline") or item.get("title") or item.get("text") or ""
                text = raw_text.strip()
                url = item.get("url", "")
                if url and text:
                    lines.append(f"{idx}. [{text}]({url})")
                elif text:
                    lines.append(f"{idx}. {text}")
                elif url:
                    lines.append(f"{idx}. [{url}]({url})")
        else:
            lines.append("Ежедневный выпуск отрывного календаря.")

        lines.append("")
        lines.append(f"📅 Смотреть интерактивный отрывной календарь [тут]({site_url}/{year}/{month}/{day})")
        lines.append("")
        lines.append("💬 Подписаться на ежедневные позитивные новости [тут](https://t.me/a_daily_pulse)")

        return "\n".join(lines)

    def build_html_caption(
        self,
        date_str: str,
        image_url: str,
        title: str | None = None,
        news_items: list[dict] | None = None,
        site_url: str = "http://192.109.206.42:8081",
    ) -> str:
        """Build single unified HTML Telegram post text with top image preview link.

        Args:
            date_str: Date string YYYY-MM-DD.
            image_url: Public image URL.
            title: Title of issue.
            news_items: List of news item dicts.
            site_url: Public showcase website URL.

        Returns:
            str: Single unified Telegram post HTML text.
        """
        import html
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = dt.strftime("%d.%m.%Y")
        [year, month, day] = date_str.split("-")

        lines = []
        # Zero-width space link to image forces Telegram to render photo preview card on top
        lines.append(f'<a href="{image_url}">&#8203;</a><b>🖼 ПУЛЬС ДНЯ — {formatted_date}</b>')
        lines.append("")
        lines.append("📌 <b>Главные позитивные новости дня:</b>")

        if news_items:
            for idx, item in enumerate(news_items[:15], 1):
                raw_text = item.get("headline") or item.get("title") or item.get("text") or ""
                text = html.escape(raw_text.strip())
                url = item.get("url", "")
                if url and text:
                    lines.append(f'{idx}. <a href="{url}">{text}</a>')
                elif text:
                    lines.append(f"{idx}. {text}")
                elif url:
                    lines.append(f'{idx}. <a href="{url}">{url}</a>')
        else:
            lines.append("Ежедневный выпуск отрывного календаря.")

        lines.append("")
        lines.append(f'📅 Смотреть интерактивный отрывной календарь <a href="{site_url}/{year}/{month}/{day}">тут</a>')
        lines.append("")
        lines.append('💬 Подписаться на новости <a href="https://t.me/a_daily_pulse">тут</a>')

        return "\n".join(lines)
