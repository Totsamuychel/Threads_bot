"""Тест BrowserPublisher — запускает браузер и публикует тестовый пост."""

import asyncio
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))


async def main():
    # 1. Проверяем health_check
    from app.publishers.browser_publisher import BrowserPublisher
    publisher = BrowserPublisher()

    ok = await publisher.health_check()
    print(f"[health_check] playwright доступен: {ok}")
    if not ok:
        print("ОШИБКА: установи playwright:  python -m playwright install chromium")
        return

    # 2. Инициализация — откроет браузер
    print("\n[init] Запускаем браузер...")
    print("       Если не залогинен — залогинься вручную в течение 60 сек.")
    await publisher.initialize()
    print("[init] Браузер готов")

    # 3. Тестовый пост
    test_text = "Тестирую автопостинг"
    test_hashtags = ["тест", "автоматизация"]

    print(f"\n[publish] Отправляем пост:")
    print(f"          Текст: {test_text}")
    print(f"          Хэштеги: {test_hashtags}")

    result = await publisher.publish(
        account_id=1,
        text=test_text,
        hashtags=test_hashtags,
    )

    # 4. Результат
    print("\n--- РЕЗУЛЬТАТ ---")
    if result.success:
        print(f"✓ Пост опубликован!")
        print(f"  Время: {result.published_at}")
        if result.post_url:
            print(f"  URL: {result.post_url}")
    else:
        print(f"✗ Ошибка: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
