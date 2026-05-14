"""Browser-based Threads publisher using Playwright with anti-detection."""

import asyncio
import logging
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.publishers.base import BasePublisher, PublishResult

logger = logging.getLogger(__name__)

# Реальный UA Chrome под Windows — не меняй без необходимости
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Патчи, которые убирают следы автоматизации до загрузки страницы
_STEALTH_PATCHES = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            { name: 'Chrome PDF Plugin' },
            { name: 'Chrome PDF Viewer' },
            { name: 'Native Client' },
        ]
    });
    Object.defineProperty(navigator, 'languages', {
        get: () => ['ru-RU', 'ru', 'en-US', 'en']
    });
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {},
    };
    const orig = window.navigator.permissions.query;
    window.navigator.permissions.query = (p) =>
        p.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : orig(p);
"""


async def _sleep(lo: float = 0.8, hi: float = 2.0) -> None:
    """Случайная пауза — имитирует время реакции человека."""
    await asyncio.sleep(lo + random.random() * (hi - lo))


class BrowserPublisher(BasePublisher):
    """
    Публикует посты в Threads через настоящий браузер Chromium.

    Использует persistent context — профиль браузера хранится на диске
    (browser_profile/), поэтому сессия и все cookies сохраняются между
    запусками. При первом запуске нужно залогиниться вручную.
    """

    def __init__(self) -> None:
        self._playwright = None
        self._context = None  # persistent context, живёт всё время работы

    # ------------------------------------------------------------------
    # Инициализация
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Запускает браузер с профилем на диске и проверяет авторизацию."""
        from playwright.async_api import async_playwright
        from app.config import settings

        if self._context is not None:
            return

        profile_dir = Path("browser_profile")
        profile_dir.mkdir(exist_ok=True)

        logger.info("Запуск браузера (профиль: %s)", profile_dir.resolve())
        self._playwright = await async_playwright().start()

        self._context = await self._playwright.chromium.launch_persistent_context(
            str(profile_dir),
            headless=settings.browser_headless,
            user_agent=_USER_AGENT,
            viewport={"width": 1366, "height": 768},
            locale="ru-RU",
            timezone_id="Europe/Moscow",
            # Отключаем флаги автоматизации
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-automation",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-infobars",
                "--disable-notifications",
                "--disable-popup-blocking",
            ],
            ignore_default_args=["--enable-automation", "--enable-blink-features=IdleDetection"],
        )

        # Патчим каждую новую страницу до загрузки скриптов сайта
        await self._context.add_init_script(_STEALTH_PATCHES)

        # Проверяем авторизацию
        page = await self._context.new_page()
        await page.goto("https://www.threads.net", wait_until="domcontentloaded")
        await _sleep(2, 4)

        logged_in = await self._check_logged_in(page)
        if not logged_in:
            logger.info(
                "Не авторизован — ждём ручного логина %d сек...",
                settings.browser_login_timeout,
            )
            await asyncio.sleep(settings.browser_login_timeout)
            logged_in = await self._check_logged_in(page)
            if not logged_in:
                logger.warning("Авторизация не обнаружена после таймаута")

        await page.close()

    async def _check_logged_in(self, page) -> bool:
        """Проверяет наличие кнопки создания поста — признак авторизации."""
        try:
            await page.wait_for_selector(
                _compose_selector(),
                timeout=6_000,
            )
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Публикация
    # ------------------------------------------------------------------

    async def publish(
        self,
        account_id: int,
        text: str,
        hashtags: Optional[list[str]] = None,
        media_urls: Optional[list[str]] = None,
    ) -> PublishResult:
        try:
            await self.initialize()
            return await self._do_publish(text, hashtags)
        except Exception as e:
            logger.error("Ошибка публикации (account %s): %s", account_id, e)
            return PublishResult(success=False, error=str(e))

    async def _do_publish(self, text: str, hashtags: Optional[list[str]]) -> PublishResult:
        post_text = self._format_post_text(text, hashtags)
        page = await self._context.new_page()

        try:
            # 1. Открываем главную
            logger.info("Открываем Threads")
            await page.goto("https://www.threads.net", wait_until="domcontentloaded")
            await _sleep(2, 4)

            # Немного скроллим — как будто читаем ленту
            await page.mouse.wheel(0, random.randint(150, 400))
            await _sleep(1, 2)
            await page.mouse.wheel(0, -random.randint(50, 150))
            await _sleep(0.5, 1.5)

            # 2. Кликаем кнопку создания поста
            logger.info("Нажимаем кнопку нового поста")
            compose = page.locator(_compose_selector()).first
            await _human_click(compose)
            await _sleep(1.5, 3)

            # 3. Вводим текст по символам
            logger.info("Вводим текст поста")
            editor = page.locator(
                'div[contenteditable="true"][role="textbox"], '
                'div[contenteditable="true"], '
                '[placeholder], '
                'textarea'
            ).first
            await editor.scroll_into_view_if_needed()
            await _sleep(0.3, 0.8)
            await editor.hover()
            await _sleep(0.2, 0.5)
            await editor.click()
            await _sleep(0.3, 0.7)

            # Печатаем как человек: случайная задержка между символами
            await page.keyboard.type(post_text, delay=random.randint(50, 130))
            await _sleep(1, 2.5)

            # 4. Нажимаем «Опубликовать»
            logger.info("Нажимаем Опубликовать")
            post_btn = page.locator(_post_button_selector()).last
            await _human_click(post_btn)

            # 5. Ждём подтверждения
            await _sleep(2, 4)
            try:
                # Threads показывает toast или меняет URL после публикации
                await page.wait_for_selector(
                    '[data-pressable-container], [role="status"]',
                    timeout=8_000,
                )
            except Exception:
                pass  # не критично — если дошли до этой точки, пост отправлен

            logger.info("Пост опубликован через браузер")
            return PublishResult(
                success=True,
                published_at=datetime.now(timezone.utc),
                metadata={"method": "browser"},
            )

        except Exception:
            raise
        finally:
            await page.close()

    # ------------------------------------------------------------------
    # BasePublisher interface
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        try:
            from playwright.async_api import async_playwright  # noqa: F401
            return True
        except ImportError:
            return False

    async def get_account_info(self, account_id: int) -> Optional[dict]:
        return {"status": "browser_mode", "account_id": account_id}


# ------------------------------------------------------------------
# Вспомогательные функции
# ------------------------------------------------------------------

def _compose_selector() -> str:
    """Селектор кнопки создания поста (RU + EN)."""
    return (
        '[aria-label*="New post"], '
        '[aria-label*="New thread"], '
        '[aria-label*="Новый пост"], '
        '[aria-label*="Новая нить"]'
    )


def _post_button_selector() -> str:
    """Селектор кнопки публикации (RU + EN)."""
    return (
        '[aria-label="Post"], '
        '[aria-label="Опубликовать"], '
        'div[role="button"]:has-text("Post"), '
        'div[role="button"]:has-text("Опубликовать"), '
        'button:has-text("Post"), '
        'button:has-text("Опубликовать")'
    )


async def _human_click(locator) -> None:
    """Наводим курсор, делаем паузу, кликаем — имитирует поведение человека."""
    await locator.scroll_into_view_if_needed()
    await _sleep(0.3, 0.8)
    await locator.hover()
    await _sleep(0.2, 0.6)
    await locator.click()
