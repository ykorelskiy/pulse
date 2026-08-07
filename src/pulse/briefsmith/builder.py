"""Author brief builder module for Assisted Mode."""


class BriefBuilder:
    """Constructs the daily concise brief for author @anta9onist."""

    def build_daily_brief(
        self,
        date_str: str,
        top_news: list[str],
        top_words: list[str],
        previous_winner_text: str | None = None,
    ) -> str:
        """Build short author brief containing context, words, and yesterday's winner.

        Args:
            date_str: Target date string (YYYY-MM-DD).
            top_news: 5 key news phrases.
            top_words: 5 reader words.
            previous_winner_text: Optional text of yesterday's winner guess.

        Returns:
            str: Formatted markdown brief for author @anta9onist.
        """
        news_block = "\n".join([f"  • {phrase}" for phrase in top_news[:5]])
        words_block = ", ".join(top_words[:5])

        winner_block = (
            f"«{previous_winner_text}»"
            if previous_winner_text
            else "Первый выпуск (пасхалка на усмотрение автора)"
        )

        brief = (
            f"🎨 **БРИФ ПЛАКАТА ДНЯ ДЛЯ АВТОРА (@anta9onist)**\n"
            f"📅 **Дата:** {date_str}\n\n"
            f"1️⃣ **5 ключевых событий/фраз дня:**\n"
            f"{news_block}\n\n"
            f"2️⃣ **5 главных слов от читателей:**\n"
            f"  • {words_block}\n\n"
            f"3️⃣ **Отсылка к вчерашней разгадке дня:**\n"
            f"  • {winner_block}\n\n"
            f"4️⃣ **Инструкция для генерации в ChatGPT:**\n"
            f"Создай плакат-сатиру в эстетике плаката 70–80-х годов. "
            f"Обязательно включи персонажа — жестяного робота ПУЛЬС. "
            f"Объедини ключевые фразы дня ({words_block}) и детали событий."
        )
        return brief
