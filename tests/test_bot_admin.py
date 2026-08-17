"""Unit tests for admin commands in Telegram bot."""

from unittest.mock import MagicMock

from pulse.bot.handlers.admin import is_admin


def test_is_admin_check():
    admin_user = MagicMock()
    admin_user.id = 123456789
    admin_user.username = "anta9onist"
    assert is_admin(admin_user) is True

    regular_user = MagicMock()
    regular_user.id = 99999999
    regular_user.username = "some_reader"
    assert is_admin(regular_user) is False


def test_build_top_selection_keyboard():
    from pulse.bot.keyboards import build_top_selection_keyboard

    kbd = build_top_selection_keyboard(issue_date="2026-08-17", total_count=15, selected_indices={2, 4})
    assert len(kbd.inline_keyboard) == 4  # 3 rows of 5 buttons + 1 action row
    # Row 1 buttons
    row0 = kbd.inline_keyboard[0]
    assert "⬛️ 1" in row0[0].text
    assert "☑️ 2" in row0[1].text
    assert "⬛️ 3" in row0[2].text
    assert "☑️ 4" in row0[3].text

    # Action row
    action_row = kbd.inline_keyboard[-1]
    assert len(action_row) == 2
    assert "🗑 Убрать выбранные (2)" in action_row[0].text
    assert "top_rm:2026-08-17:2,4" in action_row[0].callback_data

