"""Кликает на compose-кнопку и дампит что появилось + скриншот."""
import asyncio, sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))

async def main():
    from playwright.async_api import async_playwright
    from pathlib import Path

    profile_dir = Path("browser_profile")
    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            str(profile_dir), headless=False,
            viewport={"width": 1366, "height": 768},
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )
        page = await ctx.new_page()
        await page.goto("https://www.threads.net", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        # Кликаем на compose (inline поле в ленте)
        print("Кликаем compose-поле...")
        compose = page.locator('[aria-label*="Empty text field"]').first
        await compose.scroll_into_view_if_needed()
        await asyncio.sleep(1)
        await compose.click()
        await asyncio.sleep(2)

        await page.screenshot(path="debug_after_click.png")
        print("Скриншот: debug_after_click.png")

        # Дамп contenteditable
        print("\n=== CONTENTEDITABLE после клика ===")
        for el in await page.locator('[contenteditable]').all():
            try:
                val  = await el.get_attribute("contenteditable", timeout=300)
                role = await el.get_attribute("role", timeout=300) or ""
                ph   = await el.get_attribute("placeholder", timeout=300) or ""
                print(f"  contenteditable='{val}' role='{role}' placeholder='{ph}'")
            except Exception:
                pass

        # Дамп кнопок — ищем Post
        print("\n=== КНОПКИ после клика ===")
        seen = set()
        for el in await page.locator('[aria-label], [role="button"], button').all():
            try:
                label = await el.get_attribute("aria-label", timeout=300) or ""
                tag   = await el.evaluate("el => el.tagName.toLowerCase()")
                role  = await el.get_attribute("role", timeout=300) or ""
                txt   = (await el.inner_text())[:40] if tag in ("button","div","span") else ""
                key = label or txt
                if key and key not in seen:
                    seen.add(key)
                    print(f"  <{tag} role='{role}'> label='{label}' text='{txt}'")
            except Exception:
                pass

        await ctx.close()

asyncio.run(main())
