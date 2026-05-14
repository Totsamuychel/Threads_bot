"""Telegram notifier — alerts about post failures via Bot API."""

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class Notifier:
    """Sends Telegram notifications when posts fail or are exhausted.

    Disabled silently if TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID are not set.
    """

    def __init__(self) -> None:
        self._ready: Optional[bool] = None  # None = not yet initialised
        self._token: Optional[str] = None
        self._chat_id: Optional[str] = None

    # ------------------------------------------------------------------

    def _setup(self) -> None:
        if self._ready is not None:
            return
        from app.config import settings
        self._token = settings.telegram_bot_token
        self._chat_id = settings.telegram_chat_id
        self._ready = bool(self._token and self._chat_id)
        if not self._ready:
            logger.debug(
                "Notifier disabled — set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to enable"
            )

    async def send(self, text: str) -> bool:
        """Send a plain HTML message. Returns True on success."""
        self._setup()
        if not self._ready:
            return False
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    f"https://api.telegram.org/bot{self._token}/sendMessage",
                    json={"chat_id": self._chat_id, "text": text, "parse_mode": "HTML"},
                )
                if r.status_code != 200:
                    logger.warning("Telegram API returned %s: %s", r.status_code, r.text[:200])
                return r.status_code == 200
        except Exception as exc:
            logger.error("Notifier send error: %s", exc)
            return False

    async def notify_post_failed(
        self,
        account_id: int,
        post_id: int,
        error: Optional[str],
        retry_count: int,
    ) -> None:
        msg = (
            f"⚠️ <b>Post failed</b>\n"
            f"Account: <code>{account_id}</code> | Post: <code>{post_id}</code>\n"
            f"Attempt: {retry_count}\n"
            f"Error: {error or 'unknown'}"
        )
        await self.send(msg)

    async def notify_post_exhausted(
        self,
        account_id: int,
        post_id: int,
        error: Optional[str],
    ) -> None:
        msg = (
            f"🚨 <b>Post permanently failed</b>\n"
            f"Account: <code>{account_id}</code> | Post: <code>{post_id}</code>\n"
            f"Max retries reached — manual action required.\n"
            f"Last error: {error or 'unknown'}"
        )
        await self.send(msg)


# Module-level singleton — import and use directly
notifier = Notifier()
