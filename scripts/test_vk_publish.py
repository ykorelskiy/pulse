import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pulse.publisher.vk import VKPublisher

TEST_TOKEN = "vk1.a.f_K4vBnPCJKBlZHNC1RXGjaN5XUUzq4s8GSFcY-5sZz2oQye8LHZP-EMe-7UMahFK2e5_ic4cOjd6990Dpq4MZaGqnQboNHzEj2PdqSZLyGfmUQyvvjLXktwe84ScgoyBS1oh7C8NtkYbMQyNA7WInSM58r7NeufZ3nViJ4PburhaEAcG_lhLPXO-YMJREsph2VlCglJGFPTx8C_1dlCsg"
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
