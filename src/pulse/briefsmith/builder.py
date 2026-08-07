"""Author brief builder module."""

from typing import Any


class BriefBuilder:
    """Builds formatted Markdown daily brief for author (@anta9onist)."""

    def build_daily_brief(
        self,
        date_str: str,
        top_news: list[Any],
        top_words: list[str],
        previous_winner_text: str | None = None,
    ) -> str:
        """Construct structured daily brief for poster creation.

        Args:
            date_str: Target issue date string (YYYY-MM-DD).
            top_news: List of news headline strings or dicts with 'headline', 'source_id', 'url'.
            top_words: Top 5 reader submitted words.
            previous_winner_text: Yesterday's decoded guess text if available.

        Returns:
            str: Markdown formatted brief text.
        """
        lines = [
            "🎨 **БРИФ ПЛАКАТА ДНЯ ДЛЯ АВТОРА (@anta9onist)**",
            f"📅 **Дата:** {date_str}\n",
            "1️⃣ **Ключевые новости дня (заголовки и источники):**",
        ]

        for item in top_news:
            if isinstance(item, dict):
                headline = item.get("headline", item.get("phrase", ""))
                source_id = item.get("source_id", "новости")
                url = item.get("url", "#")
                lines.append(f"  • [{source_id}] **«{headline}»** — [источник]({url})")
            else:
                lines.append(f"  • **«{item}»**")

        lines.append("\n2️⃣ **5 главных слов от читателей:**")
        words_str = ", ".join(top_words) if top_words else "пока нет слов"
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
