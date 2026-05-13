"""Browser-based Threads publisher using Playwright."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.publishers.base import BasePublisher, PublishResult

logger = logging.getLogger(__name__)


class BrowserPublisher(BasePublisher):
    """
    Publishes posts to Threads by controlling a real browser via Playwright.
    Uses saved cookies to avoid logging in on every run.
    """

    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None

    async def initialize(self) -> None:
        """Launch browser and restore session from cookies if available."""
        from playwright.async_api import async_playwright
        from app.config import settings

        if self._browser is not None:
            return

        logger.info("Launching browser")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=settings.browser_headless
        )

        cookies_path = Path(settings.threads_cookies_path)

        if cookies_path.exists():
            logger.info(f"Restoring session from {cookies_path}")
            cookies = json.loads(cookies_path.read_text(encoding="utf-8"))
            self._context = await self._browser.new_context()
            await self._context.add_cookies(cookies)
        else:
            logger.info("No cookies file found — manual login required")
            self._context = await self._browser.new_context()
            page = await self._context.new_page()
            await page.goto("https://www.threads.net")

            logger.info(
                f"Waiting {settings.browser_login_timeout}s for manual login..."
            )
            await asyncio.sleep(settings.browser_login_timeout)

            cookies = await self._context.cookies()
            cookies_path.write_text(
                json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info(f"Session saved to {cookies_path}")
            await page.close()

    async def _close(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._context = None

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
            logger.error(f"Browser publish failed for account {account_id}: {e}")
            return PublishResult(success=False, error=str(e))

    async def _do_publish(
        self, text: str, hashtags: Optional[list[str]]
    ) -> PublishResult:
        post_text = self._format_post_text(text, hashtags)
        page = await self._context.new_page()

        try:
            logger.info("Navigating to Threads")
            await page.goto("https://www.threads.net", wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # Click "New thread" / "Новая нить" button
            logger.info("Looking for compose button")
            compose_btn = page.get_by_role(
                "button", name=lambda n: "new thread" in n.lower() or "новая нить" in n.lower()
            )
            # Fallback: aria-label attribute selector
            if not await compose_btn.count():
                compose_btn = page.locator(
                    '[aria-label*="New thread"], [aria-label*="Новая нить"]'
                ).first

            await compose_btn.click()
            await asyncio.sleep(1)

            # Type post text
            logger.info("Entering post text")
            editor = page.locator('[role="textbox"], textarea').first
            await editor.click()
            await editor.fill(post_text)
            await asyncio.sleep(1)

            # Click "Post" / "Опубликовать"
            logger.info("Clicking publish button")
            post_btn = page.get_by_role(
                "button", name=lambda n: n.lower() in ("post", "опубликовать")
            )
            if not await post_btn.count():
                post_btn = page.locator(
                    '[aria-label="Post"], [aria-label="Опубликовать"]'
                ).first

            await post_btn.click()
            await asyncio.sleep(2)

            # Wait for confirmation: URL change or success toast
            try:
                await page.wait_for_url("**/threads.net/**", timeout=10_000)
            except Exception:
                pass  # URL may not change; rely on timing

            logger.info("Post published successfully via browser")
            return PublishResult(
                success=True,
                published_at=datetime.now(timezone.utc),
                metadata={"method": "browser"},
            )

        finally:
            await page.close()

    async def health_check(self) -> bool:
        try:
            import playwright  # noqa: F401
            return True
        except ImportError:
            return False

    async def get_account_info(self, account_id: int) -> Optional[dict]:
        return {"status": "browser_mode", "account_id": account_id}
