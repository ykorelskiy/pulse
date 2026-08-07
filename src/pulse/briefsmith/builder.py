"""Author brief builder module with neural curation and 4-section layout."""

from typing import Any


class BriefBuilder:
    """Builds formatted Markdown daily brief for author (@anta9onist)."""

    def build_daily_brief(
        self,
        date_str: str,
        top_10_curated: list[dict[str, str]] | None = None,
        all_30_categorized: list[dict[str, Any]] | None = None,
        top_words: list[str] | None = None,
        previous_winner_text: str | None = None,
        # Legacy/fallback keyword args
        categorized_news: list[dict[str, Any]] | list[str] | None = None,
        top_news: list[Any] | None = None,
    ) -> str:
        """Construct 4-section author brief.

        Args:
            date_str: Target issue date string (YYYY-MM-DD).
            top_10_curated: List of 10 AI-curated news dicts.
            all_30_categorized: List of 6 category dicts with 5 translated news items each.
            top_words: Top 5 reader submitted words.
            previous_winner_text: Yesterday's decoded guess text if available.
            categorized_news: Fallback alias.
            top_news: Fallback alias.

        Returns:
            str: Formatted Markdown brief text.
        """
        words_list = top_words or []
        cat_data = all_30_categorized or categorized_news or top_news or []

        lines = [
            "🎨 **БРИФ ПЛАКАТА ДНЯ ДЛЯ АВТОРА (@anta9onist)**",
            f"📅 **Дата:** {date_str}\n",
        ]

        # -------------------------------------------------------------
        # Section 1: Top 10 Curated News (selected by Gemini LLM)
        # -------------------------------------------------------------
        lines.append("1️⃣ **ТОП-10 главнейших новостей дня (ИИ-отбор):**")
        has_items = (
            cat_data
            and isinstance(cat_data, list)
            and len(cat_data) > 0
            and isinstance(cat_data[0], dict)
            and "items" in cat_data[0]
        )
        if top_10_curated and isinstance(top_10_curated, list):
            for idx, item in enumerate(top_10_curated, 1):
                headline = item.get("headline", "")
                url = item.get("url", "#")
                lines.append(f"  {idx}. **«{headline}»** — [источник]({url})")
        elif has_items:
            count = 1
            for cat in cat_data:
                for item in cat.get("items", []):
                    if count <= 10:
                        headline = item.get("headline", "")
                        url = item.get("url", "#")
                        lines.append(f"  {count}. **«{headline}»** — [источник]({url})")
                        count += 1
        lines.append("")

        # -------------------------------------------------------------
        # Section 2: All 30 candidate news grouped by 6 categories
        # -------------------------------------------------------------
        lines.append("2️⃣ **Все новости по 6 направлениям (для проверки фильтрации):**")
        is_categorized = (
            cat_data
            and isinstance(cat_data, list)
            and len(cat_data) > 0
            and isinstance(cat_data[0], dict)
            and "items" in cat_data[0]
        )
        if is_categorized:
            for cat in cat_data:
                icon = cat.get("icon", "📌")
                title = cat.get("title", "")
                weight = cat.get("weight", "")
                items = cat.get("items", [])

                lines.append(f"\n{icon} **{title} ({weight}):**")
                for idx, item in enumerate(items, 1):
                    headline = item.get("headline", "")
                    url = item.get("url", "#")
                    lines.append(f"  {idx}. **«{headline}»** — [источник]({url})")
        else:
            for item in cat_data:
                if isinstance(item, dict):
                    headline = item.get("headline", item.get("phrase", ""))
                    url = item.get("url", "#")
                    lines.append(f"  • **«{headline}»** — [источник]({url})")
                else:
                    lines.append(f"  • **«{item}»**")
        lines.append("")

        # -------------------------------------------------------------
        # Section 3: Reader Submitted Words
        # -------------------------------------------------------------
        lines.append("3️⃣ **5 главных слов от читателей:**")
        words_str = ", ".join(words_list) if words_list else "пока нет слов"
        lines.append(f"  • {words_str}\n")

        # -------------------------------------------------------------
        # Section 4: Yesterday's Decoded Winner Guess
        # -------------------------------------------------------------
        lines.append("4️⃣ **Отсылка к вчерашней разгадке дня:**")
        winner = previous_winner_text or "Первый выпуск (пасхалка на усмотрение автора)"
        lines.append(f"  • «{winner}»")

        return "\n".join(lines)
