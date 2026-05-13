"""Threads API publisher — Meta Graph API v1.0 implementation."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.publishers.base import BasePublisher, PublishResult

logger = logging.getLogger(__name__)

_AUTH_BASE = "https://threads.net"
_GRAPH_BASE = "https://graph.threads.net/v1.0"
_SCOPES = "threads_basic,threads_content_publish"


class ThreadsAPIPublisher(BasePublisher):
    """Publisher that uses the official Meta Threads Graph API."""

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    # ------------------------------------------------------------------
    # OAuth helpers
    # ------------------------------------------------------------------

    def generate_auth_url(self, account_id: int) -> str:
        """Return the OAuth authorization URL for the given account."""
        from app.config import settings
        params = urlencode({
            "client_id": settings.threads_app_id,
            "redirect_uri": settings.threads_redirect_uri,
            "scope": _SCOPES,
            "response_type": "code",
            "state": str(account_id),
        })
        return f"{_AUTH_BASE}/oauth/authorize?{params}"

    async def exchange_code(self, code: str) -> dict:
        """
        Exchange an authorization code for a short-lived token, then upgrade
        to a long-lived token (60-day expiry).

        Returns dict with keys: access_token, user_id, expires_at (datetime).
        """
        from app.config import settings
        async with httpx.AsyncClient(timeout=30) as client:
            # Step 1 — short-lived token
            r = await client.post(
                f"{_GRAPH_BASE.rstrip('/v1.0')}/oauth/access_token",
                data={
                    "code": code,
                    "client_id": settings.threads_app_id,
                    "client_secret": settings.threads_app_secret,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.threads_redirect_uri,
                },
            )
            r.raise_for_status()
            short = r.json()
            short_token = short["access_token"]
            user_id = str(short["user_id"])

            # Step 2 — long-lived token
            r = await client.get(
                f"{_GRAPH_BASE.rstrip('/v1.0')}/access_token",
                params={
                    "grant_type": "th_exchange_token",
                    "client_secret": settings.threads_app_secret,
                    "access_token": short_token,
                },
            )
            r.raise_for_status()
            long = r.json()

        expires_in = long.get("expires_in", 5183944)  # ~60 days default
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        return {
            "access_token": long["access_token"],
            "user_id": user_id,
            "expires_at": expires_at,
        }

    async def refresh_token(self, access_token: str) -> dict:
        """
        Refresh a long-lived token before it expires.
        Returns dict with keys: access_token, expires_at.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                f"{_GRAPH_BASE.rstrip('/v1.0')}/refresh_access_token",
                params={
                    "grant_type": "th_refresh_token",
                    "access_token": access_token,
                },
            )
            r.raise_for_status()
            data = r.json()

        expires_in = data.get("expires_in", 5183944)
        return {
            "access_token": data["access_token"],
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_credentials(self, account_id: int) -> tuple[str, str]:
        """Return (access_token, threads_user_id) for the given account."""
        from app.models import Account
        result = await self.db.execute(select(Account).where(Account.id == account_id))
        account = result.scalar_one_or_none()

        if not account:
            raise ValueError(f"Account {account_id} not found")
        if not account.api_token:
            raise ValueError(
                f"Account {account_id} has no access token — complete OAuth first"
            )
        if not account.threads_user_id:
            raise ValueError(
                f"Account {account_id} has no Threads user ID — complete OAuth first"
            )
        if account.token_expires_at and account.token_expires_at < datetime.now(timezone.utc):
            raise ValueError(
                f"Access token for account {account_id} is expired — refresh or re-authorize"
            )

        return account.api_token, account.threads_user_id

    async def _create_container(
        self,
        user_id: str,
        access_token: str,
        text: str,
        image_url: Optional[str] = None,
        video_url: Optional[str] = None,
    ) -> str:
        """Create a media container and return its ID."""
        params: dict = {"access_token": access_token}

        if video_url:
            params.update({"media_type": "VIDEO", "video_url": video_url, "text": text})
        elif image_url:
            params.update({"media_type": "IMAGE", "image_url": image_url, "text": text})
        else:
            params.update({"media_type": "TEXT", "text": text})

        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(f"{_GRAPH_BASE}/{user_id}/threads", params=params)
            r.raise_for_status()
            return r.json()["id"]

    async def _publish_container(
        self, user_id: str, access_token: str, container_id: str
    ) -> dict:
        """Publish a previously created container and return the API response."""
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{_GRAPH_BASE}/{user_id}/threads_publish",
                params={"creation_id": container_id, "access_token": access_token},
            )
            r.raise_for_status()
            return r.json()

    async def _get_post_permalink(self, post_id: str, access_token: str) -> Optional[str]:
        """Fetch the permalink for a published post."""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(
                    f"{_GRAPH_BASE}/{post_id}",
                    params={"fields": "permalink", "access_token": access_token},
                )
                r.raise_for_status()
                return r.json().get("permalink")
        except Exception:
            return None

    @staticmethod
    def _format_text(text: str, hashtags: Optional[list[str]]) -> str:
        """Combine body text with hashtags, staying within the 500-char limit."""
        if not hashtags:
            return text[:500]
        tags = " ".join(f"#{t.lstrip('#')}" for t in hashtags)
        combined = f"{text}\n\n{tags}"
        if len(combined) <= 500:
            return combined
        # Truncate body to fit tags
        available = 500 - len(tags) - 2
        return f"{text[:available]}\n\n{tags}"

    # ------------------------------------------------------------------
    # BasePublisher interface
    # ------------------------------------------------------------------

    async def publish(
        self,
        account_id: int,
        text: str,
        hashtags: Optional[list[str]] = None,
        media_urls: Optional[list[str]] = None,
    ) -> PublishResult:
        """Publish a post to Threads via the official Graph API."""
        try:
            access_token, user_id = await self._get_credentials(account_id)
        except ValueError as e:
            return PublishResult(success=False, error=str(e))

        formatted_text = self._format_text(text, hashtags)
        image_url = media_urls[0] if media_urls else None

        try:
            container_id = await self._create_container(
                user_id, access_token, formatted_text, image_url=image_url
            )
            logger.debug(f"Created container {container_id} for account {account_id}")

            data = await self._publish_container(user_id, access_token, container_id)
            post_id = data["id"]

            permalink = await self._get_post_permalink(post_id, access_token)

            logger.info(f"Published post {post_id} for account {account_id}")
            return PublishResult(
                success=True,
                post_id=post_id,
                post_url=permalink,
                published_at=datetime.now(timezone.utc),
                metadata={"container_id": container_id, "threads_user_id": user_id},
            )

        except httpx.HTTPStatusError as e:
            body = e.response.text
            logger.error(f"Threads API error for account {account_id}: {e.response.status_code} {body}")
            return PublishResult(
                success=False,
                error=f"API {e.response.status_code}: {body}",
            )
        except httpx.TimeoutException:
            return PublishResult(success=False, error="Request timeout")
        except Exception as e:
            logger.error(f"Unexpected publish error for account {account_id}: {e}")
            return PublishResult(success=False, error=str(e))

    async def health_check(self) -> bool:
        """Verify the Graph API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{_GRAPH_BASE.rstrip('/v1.0')}/")
                return r.status_code < 500
        except Exception:
            return False

    async def get_account_info(self, account_id: int) -> Optional[dict]:
        """Return the Threads profile for the given account."""
        try:
            access_token, user_id = await self._get_credentials(account_id)
        except ValueError:
            return None

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(
                    f"{_GRAPH_BASE}/{user_id}",
                    params={
                        "fields": "id,username,name,threads_profile_picture_url,threads_biography",
                        "access_token": access_token,
                    },
                )
                r.raise_for_status()
                return r.json()
        except Exception as e:
            logger.error(f"Error fetching account info for {account_id}: {e}")
            return None
