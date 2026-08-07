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
