"""Inline and reply keyboards for Pulse Telegram Bot."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_top_selection_keyboard(
    issue_date: str,
    total_count: int,
    selected_indices: list[int] | set[int] | None = None,
    show_confirm_button: bool = False,
) -> InlineKeyboardMarkup:
    """Build interactive checkbox grid keyboard for news item selection.

    Args:
        issue_date: Date string YYYY-MM-DD.
        total_count: Total number of news items in current list.
        selected_indices: Set/list of 1-based indices currently selected for removal.
        show_confirm_button: Whether to include the confirm publish button (True when cover photo is uploaded).

    Returns:
        InlineKeyboardMarkup: Formatted inline keyboard.
    """
    selected_set = set(selected_indices) if selected_indices else set()
    csv_selected = ",".join(str(i) for i in sorted(selected_set)) if selected_set else "none"

    inline_keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    for idx in range(1, total_count + 1):
        is_selected = idx in selected_set
        icon = "☑️" if is_selected else "⬛️"
        label = f"{icon} {idx}"

        # Toggle callback data: top_t:{date}:{idx}:{current_csv}
        cb_data = f"top_t:{issue_date}:{idx}:{csv_selected}"
        if len(cb_data) > 64:
            cb_data = f"top_t:{issue_date}:{idx}"

        row.append(InlineKeyboardButton(text=label, callback_data=cb_data))

        if len(row) == 5:
            inline_keyboard.append(row)
            row = []

    if row:
        inline_keyboard.append(row)

    # Action buttons row
    action_row: list[InlineKeyboardButton] = []
    if selected_set:
        remove_cb = f"top_rm:{issue_date}:{csv_selected}"
        if len(remove_cb) > 64:
            remove_cb = f"top_rm:{issue_date}"
        action_row.append(
            InlineKeyboardButton(
                text=f"🗑 Убрать выбранные ({len(selected_set)})",
                callback_data=remove_cb,
            )
        )

    if show_confirm_button:
        action_row.append(
            InlineKeyboardButton(
                text="✅ Подтвердить в 20:00",
                callback_data=f"confirm_publish_{issue_date}",
            )
        )

    if action_row:
        inline_keyboard.append(action_row)

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

