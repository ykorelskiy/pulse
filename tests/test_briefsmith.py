"""Unit tests for briefsmith policy and builder."""

from pulse.briefsmith.builder import BriefBuilder
from pulse.briefsmith.policy import EditorialPolicyEnforcer


def test_policy_enforcer_passes_direct_content():
    policy = EditorialPolicyEnforcer()
    news = ["перемога Зеленского", "возвращение Маска"]
    words = ["сатира", "нейросеть"]

    c_news, c_words = policy.sanitize_input(news, words)

    assert c_news == news
    assert c_words == words


def test_brief_builder_structure():
    builder = BriefBuilder()
    brief = builder.build_daily_brief(
        date_str="2026-08-07",
        top_news=["Новость 1", "Новость 2", "Новость 3", "Новость 4", "Новость 5"],
        top_words=["Слово 1", "Слово 2", "Слово 3", "Слово 4", "Слово 5"],
        previous_winner_text="Вчерашняя победа",
    )

    assert "@anta9onist" in brief
    assert "2026-08-07" in brief
    assert "Новость 1" in brief
    assert "Слово 1" in brief
    assert "Вчерашняя победа" in brief
