"""
Открывает Threads, ждёт 120 сек для ручного логина,
затем сохраняет скриншот и все aria-label в debug_output.txt.
"""
import asyncio, sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))

LOGIN_TIMEOUT = 120  # секунд на ручной логин

async def main():
    from playwright.async_api import async_playwright
    from pathlib import Path

    profile_dir = Path("browser_profile")
    profile_dir.mkdir(exist_ok=True)

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            str(profile_dir),
            headless=False,
            viewport={"width": 1366, "height": 768},
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )
        page = await ctx.new_page()
        await page.goto("https://www.threads.net", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Проверяем залогинен ли уже
        already = False
        try:
            await page.wait_for_selector('[aria-label]', timeout=3000)
            labels = [await el.get_attribute("aria-label") for el in await page.locator('[aria-label]').all()[:5]]
            already = any(l for l in labels if l)
        except Exception:
            pass

        if not already:
            print(f"Браузер открыт. Залогинься на threads.net — есть {LOGIN_TIMEOUT} секунд...")
            for remaining in range(LOGIN_TIMEOUT, 0, -10):
                print(f"  Осталось {remaining} сек...")
                await asyncio.sleep(10)
        else:
            print("Уже залогинен, продолжаем...")
            await asyncio.sleep(2)

        print("\nСобираем селекторы...")
        await page.screenshot(path="debug_screenshot.png")
        print("Скриншот сохранён: debug_screenshot.png")

        lines = ["=== КНОПКИ И ЭЛЕМЕНТЫ С aria-label ===\n"]
        seen = set()
        for el in await page.locator('[aria-label]').all():
            try:
                label = await el.get_attribute("aria-label", timeout=300)
                tag   = await el.evaluate("el => el.tagName.toLowerCase()")
                role  = await el.get_attribute("role", timeout=300) or ""
                if label and label not in seen:
                    seen.add(label)
                    lines.append(f"<{tag} role='{role}'> aria-label='{label}'")
            except Exception:
                pass

        lines.append("\n=== CONTENTEDITABLE ===\n")
        for el in await page.locator('[contenteditable]').all():
            try:
                val  = await el.get_attribute("contenteditable", timeout=300)
                role = await el.get_attribute("role", timeout=300) or ""
                ph   = await el.get_attribute("placeholder", timeout=300) or ""
                lines.append(f"contenteditable='{val}' role='{role}' placeholder='{ph}'")
            except Exception:
                pass

        output = "\n".join(lines)
        Path("debug_output.txt").write_text(output, encoding="utf-8")
        print("\n--- Найденные элементы ---")
        print(output)
        print("\nРезультат сохранён в debug_output.txt")

        await ctx.close()

asyncio.run(main())
