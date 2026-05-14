"""Social actions service — likes, replies, follows via browser."""

import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, SocialAction

logger = logging.getLogger(__name__)


class SocialActionsService:
    """
    Performs social interactions (like, reply, follow) for an account.
    Uses BrowserPublisher's Playwright context — call after initialize().
    """

    def __init__(self, db: AsyncSession, account_id: int):
        self.db = db
        self.account_id = account_id

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self) -> dict:
        """Run a social interaction session. Returns action counts."""
        from app.publishers.browser_publisher import BrowserPublisher

        account = await self._get_account()
        if not account or not account.is_active or not account.social_actions_enabled:
            logger.debug("Social actions skipped for account %s", self.account_id)
            return {"skipped": True}

        counts = await self._today_counts()
        likes_left = max(0, account.likes_per_day - counts["likes"])
        replies_left = max(0, account.replies_per_day - counts["replies"])
        follows_left = max(0, account.follows_per_day - counts["follows"])

        if not any([likes_left, replies_left, follows_left]):
            logger.info("Daily social limits reached for account %s", self.account_id)
            return {"daily_limit_reached": True}

        publisher = BrowserPublisher()
        await publisher.initialize()

        results = {"likes": 0, "replies": 0, "follows": 0}
        page = await publisher._context.new_page()

        try:
            await page.goto("https://www.threads.net", wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(2.5, 4.5))

            # 1. Likes
            if likes_left > 0:
                to_like = min(likes_left, random.randint(2, 5))
                results["likes"] = await self._do_likes(page, publisher, to_like)
                await asyncio.sleep(random.uniform(3, 7))

            # 2. Replies
            if replies_left > 0:
                to_reply = min(replies_left, random.randint(1, 2))
                results["replies"] = await self._do_replies(page, publisher, account, to_reply)
                await asyncio.sleep(random.uniform(5, 10))

            # 3. Follows
            if follows_left > 0:
                to_follow = min(follows_left, random.randint(1, 3))
                results["follows"] = await self._do_follows(page, publisher, to_follow)

        except Exception as exc:
            logger.error("Social actions error for account %s: %s", self.account_id, exc)
        finally:
            await page.close()
            # Release browser resources
            try:
                if publisher._context:
                    await publisher._context.close()
                    publisher._context = None
                if publisher._playwright:
                    await publisher._playwright.stop()
                    publisher._playwright = None
            except Exception:
                pass

        logger.info(
            "Social actions done for account %s: likes=%d replies=%d follows=%d",
            self.account_id, results["likes"], results["replies"], results["follows"],
        )
        return results

    # ------------------------------------------------------------------
    # Likes
    # ------------------------------------------------------------------

    async def _do_likes(self, page, publisher, count: int) -> int:
        liked = 0
        like_svgs = page.locator('svg[aria-label="Like"]')

        # Scroll a bit to load more posts
        await page.mouse.wheel(0, random.randint(200, 500))
        await asyncio.sleep(random.uniform(1, 2))

        total = await like_svgs.count()
        if total == 0:
            logger.debug("No like buttons found in feed")
            return 0

        # Pick random subset so we don't always like the same posts
        indices = random.sample(range(total), min(total, count * 3))

        for idx in indices:
            if liked >= count:
                break
            btn = like_svgs.nth(idx)
            try:
                await btn.scroll_into_view_if_needed()
                await asyncio.sleep(random.uniform(0.8, 2.5))  # simulate reading

                # Click closest button ancestor
                await btn.evaluate("el => el.closest('[role=\"button\"]').click()")
                liked += 1
                await self._save_action("like")

                # Human-like pause between likes
                await asyncio.sleep(random.uniform(2.0, 6.0))
            except Exception as exc:
                logger.debug("Like skipped (idx %d): %s", idx, exc)

        return liked

    # ------------------------------------------------------------------
    # Replies
    # ------------------------------------------------------------------

    async def _do_replies(self, page, publisher, account, count: int) -> int:
        from app.publishers.browser_publisher import _human_type

        replied = 0
        reply_svgs = page.locator('svg[aria-label="Reply"]')
        total = await reply_svgs.count()
        if total == 0:
            return 0

        indices = random.sample(range(total), min(total, count * 4))

        for idx in indices:
            if replied >= count:
                break
            btn = reply_svgs.nth(idx)
            try:
                # Extract post text for LLM context
                post_text = await btn.evaluate("""el => {
                    const root = el.closest('article') ||
                                 el.closest('[data-pressable-container]') ||
                                 el.parentElement?.parentElement?.parentElement;
                    if (!root) return '';
                    const texts = root.querySelectorAll('div[dir="auto"], span[dir="auto"]');
                    return Array.from(texts).map(t => t.innerText).join(' ').substring(0, 400);
                }""")

                if not post_text or len(post_text.strip()) < 10:
                    continue

                reply_text = await self._generate_reply(account, post_text)
                if not reply_text:
                    continue

                # Click reply button
                await btn.scroll_into_view_if_needed()
                await asyncio.sleep(random.uniform(1, 2))
                await btn.evaluate("el => el.closest('[role=\"button\"]').click()")
                await asyncio.sleep(random.uniform(1.5, 3.0))

                # Find active text editor (appears after clicking Reply)
                editor = page.locator('[contenteditable="true"]').last
                try:
                    await editor.wait_for(state="visible", timeout=6000)
                except Exception:
                    continue
                await editor.click()
                await asyncio.sleep(random.uniform(0.3, 0.7))

                await _human_type(page, reply_text)
                await asyncio.sleep(random.uniform(0.8, 1.5))

                # Submit reply
                post_btn = page.locator(
                    'div[role="button"]:has-text("Post"), '
                    'div[role="button"]:has-text("Reply"), '
                    'button:has-text("Post")'
                ).last
                await post_btn.click()
                await asyncio.sleep(random.uniform(2, 4))

                replied += 1
                await self._save_action("reply", content=reply_text)

            except Exception as exc:
                logger.debug("Reply skipped (idx %d): %s", idx, exc)

        return replied

    # ------------------------------------------------------------------
    # Follows
    # ------------------------------------------------------------------

    async def _do_follows(self, page, publisher, count: int) -> int:
        followed = 0

        # Scroll to find Follow buttons (appear in post header or suggestions sidebar)
        for _ in range(3):
            await page.mouse.wheel(0, random.randint(300, 600))
            await asyncio.sleep(random.uniform(1, 2))

        follow_svgs = page.locator('svg[aria-label="Follow"]')
        total = await follow_svgs.count()

        if total == 0:
            logger.debug("No follow buttons found in feed")
            return 0

        indices = random.sample(range(total), min(total, count * 2))

        for idx in indices:
            if followed >= count:
                break
            btn = follow_svgs.nth(idx)
            try:
                await btn.scroll_into_view_if_needed()
                await asyncio.sleep(random.uniform(1.0, 3.0))
                await btn.evaluate("el => el.closest('[role=\"button\"]').click()")
                followed += 1
                await self._save_action("follow")
                await asyncio.sleep(random.uniform(3.0, 7.0))
            except Exception as exc:
                logger.debug("Follow skipped (idx %d): %s", idx, exc)

        return followed

    # ------------------------------------------------------------------
    # LLM reply generation
    # ------------------------------------------------------------------

    async def _generate_reply(self, account, post_text: str) -> Optional[str]:
        try:
            from app.llm import get_llm_client_for_account
            client = await get_llm_client_for_account(account)
            system = (
                f"You write very short, genuine social media replies in {account.language or 'en'}. "
                f"Tone: {account.tone or 'casual, friendly'}. "
                "Max 1-2 sentences. No hashtags. Sound human, not promotional."
            )
            response = await client.generate(
                prompt=f"Write a brief, natural reply to this post:\n\n{post_text}",
                system_prompt=system,
                max_tokens=80,
            )
            text = response.content.strip()
            # Strip surrounding quotes if LLM added them
            if text.startswith('"') and text.endswith('"'):
                text = text[1:-1]
            return text[:280] if text else None
        except Exception as exc:
            logger.warning("Reply generation failed: %s", exc)
            return None

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _get_account(self) -> Optional[Account]:
        result = await self.db.execute(
            select(Account).where(Account.id == self.account_id)
        )
        return result.scalar_one_or_none()

    async def _today_counts(self) -> dict:
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(SocialAction.action_type, func.count(SocialAction.id))
            .where(
                and_(
                    SocialAction.account_id == self.account_id,
                    SocialAction.success == True,
                    SocialAction.created_at >= start,
                )
            )
            .group_by(SocialAction.action_type)
        )
        rows = result.all()
        counts = {"likes": 0, "replies": 0, "follows": 0}
        for action_type, cnt in rows:
            if action_type in counts:
                counts[action_type] = cnt
        return counts

    async def _save_action(
        self,
        action_type: str,
        target_post_id: Optional[str] = None,
        target_user_id: Optional[str] = None,
        content: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        action = SocialAction(
            account_id=self.account_id,
            action_type=action_type,
            target_post_id=target_post_id,
            target_user_id=target_user_id,
            content=content,
            success=success,
            error=error,
        )
        self.db.add(action)
        await self.db.commit()
