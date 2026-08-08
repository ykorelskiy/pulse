"""Author brief builder module with 5-section layout."""

from typing import Any


class BriefBuilder:
    """Builds formatted Markdown daily brief for author (@anta9onist)."""

    def build_daily_brief(
        self,
        date_str: str,
        top_10_curated: list[dict[str, str]] | None = None,
        top_50_flat: list[dict[str, Any]] | None = None,
        source_stats: list[dict[str, Any]] | None = None,
        top_words: list[str] | None = None,
        previous_winner_text: str | None = None,
        # Legacy/fallback keyword args
        all_30_categorized: list[dict[str, Any]] | None = None,
        categorized_news: list[dict[str, Any]] | list[str] | None = None,
        top_news: list[Any] | None = None,
    ) -> str:
        """Construct 5-section author brief.

        Args:
            date_str: Target issue date string (YYYY-MM-DD).
            top_10_curated: List of 10 AI-curated news dicts.
            top_50_flat: Flat list of top 50 news candidate items for the day.
            source_stats: List of dicts with source audit statistics.
            top_words: Top 5 reader submitted words.
            previous_winner_text: Yesterday's decoded guess text if available.
            all_30_categorized: Fallback alias.
            categorized_news: Fallback alias.
            top_news: Fallback alias.

        Returns:
            str: Formatted Markdown brief text.
        """
        words_list = top_words or []
        lines = [
            "🎨 **БРИФ ПЛАКАТА ДНЯ ДЛЯ АВТОРА (@anta9onist)**",
            f"📅 **Дата:** {date_str}\n",
        ]

        # -------------------------------------------------------------
        # Section 1: Top 10 Curated News (Selected by AI)
        # -------------------------------------------------------------
        lines.append("1️⃣ **10 отборных новостей (ИИ-отбор):**")
        if top_10_curated and isinstance(top_10_curated, list):
            for idx, item in enumerate(top_10_curated, 1):
                headline = item.get("headline", "")
                url = item.get("url", "#")
                src = item.get("source_name", "источник")
                score_val = item.get("total_score")
                score_str = f" [⭐ {score_val} б.]" if score_val is not None else ""
                lines.append(f"  {idx}.{score_str} **«{headline}»** — [{src}]({url})")
        lines.append("")

        # -------------------------------------------------------------
        # Section 2: Top 50 News Candidate Pool (Flat list, no % tags)
        # -------------------------------------------------------------
        lines.append("2️⃣ **ТОП-50 всех проанализированных новостей дня:**")
        candidates = top_50_flat or []
        if not candidates:
            if all_30_categorized:
                flat_from_cats = []
                for cat in all_30_categorized:
                    if isinstance(cat, dict) and "items" in cat:
                        flat_from_cats.extend(cat.get("items", []))
                candidates = flat_from_cats
            elif categorized_news or top_news:
                raw_c = categorized_news or top_news
                if isinstance(raw_c, list):
                    candidates = raw_c

        if candidates:
            for idx, item in enumerate(candidates, 1):
                if isinstance(item, dict):
                    headline = item.get("headline", "")
                    url = item.get("url", "#")
                    src = item.get("source_name", "источник")
                    score_val = item.get("total_score")
                    score_str = f" [⭐ {score_val} б.]" if score_val is not None else ""
                    lines.append(f"  {idx}.{score_str} **«{headline}»** — [{src}]({url})")
                else:
                    lines.append(f"  {idx}. **«{item}»**")
        lines.append("")

        # -------------------------------------------------------------
        # Section 3: Sources Audit Statistics
        # -------------------------------------------------------------
        lines.append("3️⃣ **Перечень источников и статистика сбора:**")
        if source_stats:
            for stat in source_stats:
                sname = stat.get("name", "Источник")
                analyzed = stat.get("analyzed", 0)
                in_50 = stat.get("in_top_50", 0)
                in_10 = stat.get("in_top_10", 0)
                lines.append(
                    f"  • **{sname}** — всего проанализировано: {analyzed} | "
                    f"вошло в ТОП-50: {in_50} | вошло в ТОП-10: {in_10}"
                )
        else:
            lines.append("  • *Статистика обновляется при следующем сборе*")
        lines.append("")

        # -------------------------------------------------------------
        # Section 4: 5 Main Words from Readers
        # -------------------------------------------------------------
        lines.append("4️⃣ **5 главных слов от читателей:**")
        if words_list:
            formatted_words = ", ".join(words_list)
            lines.append(f"  • {formatted_words}")
        else:
            lines.append("  • сатира, технологии, юмор, будущее, пульс")
        lines.append("")

        # -------------------------------------------------------------
        # Section 5: Reference to Yesterday's Solution
        # -------------------------------------------------------------
        lines.append("5️⃣ **Отсылка к вчерашней разгадке дня:**")
        if previous_winner_text:
            lines.append(f"  • «{previous_winner_text}»")
        else:
            lines.append("  • «Первый выпуск (пасхалка на усмотрение автора)»")

        return "\n".join(lines)
