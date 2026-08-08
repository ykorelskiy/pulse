import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pulse.publisher.vk import VKPublisher

TEST_TOKEN = "vk1.a.grjrIHF_mOj4uurpywibmXzfun43K5sJfMCDZR0jEvVuP8nn0bcMeD-Jef3wVmay_cuQRu6sZru78F4dBJZe8klAVYUfIt41L_AYYvE7NNgnGfTJ-W6LgT4rID35T0KDfutC_QIovrlqyQxjCTzl87z8LbBSs2yyTOPLEXHV4fnCwf3KYyWy_MVLMTEgTbSqB-8nZ-2mgw7jBM94jOZf9w"
TEST_GROUP_ID = 240745088


async def main():
    print("Testing VKPublisher...")
    publisher = VKPublisher(access_token=TEST_TOKEN, group_id=TEST_GROUP_ID)

    # Use existing sample texture/cover as test image
    sample_img = Path("DOCS/artifacts/vintage_newsprint_paper.png")
    if not sample_img.exists():
        print(f"Error: {sample_img} not found.")
        return

    text = (
        "🖼 ПУЛЬС ДНЯ — Тестовый запуск автопубликации\n\n"
        "📌 Главные позитивные новости дня:\n"
        "1. Проект «Пульс Дня» успешно подключил автопубликацию во ВКонтакте!\n"
        "2. Все выпуски отрывного календаря теперь выходят синхронно.\n\n"
        "📅 Смотреть веб-календарь: http://192.109.206.42:8081"
    )

    try:
        vk_url = await publisher.publish_issue(
            image_input=str(sample_img),
            text=text,
        )
        print(f"✅ SUCCESS! Post published to VK: {vk_url}")
    except Exception as e:
        print(f"❌ FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(main())
