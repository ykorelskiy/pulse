"""Author brief builder module with categorized news presentation."""

from typing import Any


class BriefBuilder:
    """Builds formatted Markdown daily brief for author (@anta9onist)."""

    def build_daily_brief(
        self,
        date_str: str,
        categorized_news: list[dict[str, Any]] | list[str] | None = None,
        top_words: list[str] | None = None,
        previous_winner_text: str | None = None,
        top_news: list[Any] | None = None,
    ) -> str:
        """Construct structured daily brief for poster creation.

        Args:
            date_str: Target issue date string (YYYY-MM-DD).
            categorized_news: List of category dicts ('title', 'weight', 'icon', 'items').
            top_words: Top 5 reader submitted words.
            previous_winner_text: Yesterday's decoded guess text if available.
            top_news: Alias for categorized_news for backward compatibility.

        Returns:
            str: Markdown formatted brief text.
        """
        news_data = categorized_news if categorized_news is not None else top_news
        news_list = news_data or []
        words_list = top_words or []

        lines = [
            "🎨 **БРИФ ПЛАКАТА ДНЯ ДЛЯ АВТОРА (@anta9onist)**",
            f"📅 **Дата:** {date_str}\n",
            "1️⃣ **Ключевые новости дня по категориям (с весовыми долями):**",
        ]

        is_categorized = (
            news_list
            and isinstance(news_list, list)
            and len(news_list) > 0
            and isinstance(news_list[0], dict)
            and "items" in news_list[0]
        )
        if is_categorized:
            for cat in news_list:
                icon = cat.get("icon", "📌")
                title = cat.get("title", "")
                weight = cat.get("weight", "")
                items = cat.get("items", [])

                lines.append(f"\n{icon} **{title} ({weight}):**")
                for idx, item in enumerate(items, 1):
                    headline = item.get("headline", "")
                    src = item.get("source_name", "новости")
                    url = item.get("url", "#")
                    lines.append(f"  {idx}. [{src}] **«{headline}»** — [источник]({url})")
        else:
            for item in news_list:
                if isinstance(item, dict):
                    headline = item.get("headline", item.get("phrase", ""))
                    src = item.get("source_id", "новости")
                    url = item.get("url", "#")
                    lines.append(f"  • [{src}] **«{headline}»** — [источник]({url})")
                else:
                    lines.append(f"  • **«{item}»**")

        lines.append("\n2️⃣ **5 главных слов от читателей:**")
        words_str = ", ".join(words_list) if words_list else "пока нет слов"
        lines.append(f"  • {words_str}\n")

        lines.append("3️⃣ **Отсылка к вчерашней разгадке дня:**")
        winner = previous_winner_text or "Первый выпуск (пасхалка на усмотрение автора)"
        lines.append(f"  • «{winner}»\n")

        lines.append("4️⃣ **Инструкция для генерации в ChatGPT:**")
        lines.append(
            "Создай плакат-сатиру в эстетике плаката 70–80-х годов. Обязательно "
            "включи персонажа — жестяного робота ПУЛЬС. Объедини главные сюжеты "
            f"дня ({words_str}) и детали событий."
        )

        return "\n".join(lines)
