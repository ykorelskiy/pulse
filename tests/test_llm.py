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
                    "headline": "Kangaroo spotted in Swiss woodland",
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
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                '{"translated_all": [{"id": 1, '
                                '"ru_headline": "Переведенный заголовок"}], '
                                '"top_10_ids": [1]}'
                            )

                        }
                    ]
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    curator = LLMCurator(api_key="test_api_key")
    raw_categorized = [
        {
            "code": "tech",
            "title": "Е. Технологии",
            "weight": "5%",
            "icon": "💻",
            "items": [
                {
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
