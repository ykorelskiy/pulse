"""Unit tests for Gemini LLM Curator module."""

from unittest.mock import MagicMock, patch

from pulse.digest.llm import LLMCurator


def test_llm_curator_fallback_curation():
    curator = LLMCurator(api_key=None)

    raw_categorized = [
        {
            "code": "ru_hot",
            "title": "Б. RU скандалы",
            "weight": "30%",
            "icon": "🔥",
            "items": [
                {
                    "headline": "Скандал в шоу-бизнесе",
                    "source_name": "StarHit",
                    "url": "https://starhit.ru",
                },
                {
                    "headline": "Кенгуру замечен в швейцарском лесу",
                    "source_name": "Reddit",
                    "url": "https://reddit.com",
                },
            ],
        }
    ]

    top_10, _ = curator.curate_and_translate_news(raw_categorized, top_k=10)
    headlines = [item["headline"] for item in top_10]
    assert len(top_10) == 2
    assert "Кенгуру замечен в швейцарском лесу" in headlines


@patch("httpx.post")
def test_llm_curator_gemini_api_success(mock_post):
    mock_resp_phase1 = MagicMock()
    mock_resp_phase1.status_code = 200
    mock_resp_phase1.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": '[{"id": 1, "sentiment": "positive", "ru_title": "Переведенный заголовок"}]'
                        }
                    ]
                }
            }
        ]
    }

    mock_resp_phase2 = MagicMock()
    mock_resp_phase2.status_code = 200
    mock_resp_phase2.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": '[{"id": 1, "virality": 8, "relevance": 5, "significance": 4}]'
                        }
                    ]
                }
            }
        ]
    }

    mock_post.side_effect = [mock_resp_phase1, mock_resp_phase2]

    curator = LLMCurator(api_key="test_api_key")
    raw_categorized = [
        {
            "code": "tech",
            "title": "Е. Технологии",
            "weight": "5%",
            "icon": "💻",
            "items": [
                {
                    "id": 1,
                    "headline": "Test foreign headline",
                    "source_name": "TechCrunch",
                    "url": "https://tc.com",
                }
            ],
        }
    ]


    top_10, _ = curator.curate_and_translate_news(raw_categorized, top_k=10)

    assert len(top_10) == 1
    assert top_10[0]["headline"] == "Переведенный заголовок"

