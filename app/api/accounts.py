"""Account management API endpoints."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.models import Account
from app.schemas import AccountCreate, AccountUpdate, AccountResponse, SuccessResponse
from app.publishers.threads_api import ThreadsAPIPublisher

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.post("", response_model=AccountResponse, status_code=201)
async def create_account(account: AccountCreate, db: AsyncSession = Depends(get_db)):
    """Create a new account configuration."""
    # Check if username already exists
    result = await db.execute(select(Account).where(Account.username == account.username))
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Create account
    db_account = Account(**account.model_dump())
    db.add(db_account)
    await db.commit()
    await db.refresh(db_account)
    
    return db_account


@router.get("", response_model=List[AccountResponse])
async def list_accounts(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """List all accounts."""
    result = await db.execute(select(Account).offset(skip).limit(limit))
    accounts = result.scalars().all()
    return accounts


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """Get account by ID."""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return account


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(account_id: int, account_update: AccountUpdate, db: AsyncSession = Depends(get_db)):
    """Update account configuration."""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Update fields
    update_data = account_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)
    
    await db.commit()
    await db.refresh(account)
    
    return account


@router.delete("/{account_id}", response_model=SuccessResponse)
async def delete_account(account_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an account."""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    await db.delete(account)
    await db.commit()

    return SuccessResponse(message=f"Account {account_id} deleted successfully")


# ------------------------------------------------------------------
# OAuth endpoints
# ------------------------------------------------------------------

@router.get("/{account_id}/oauth/url")
async def get_oauth_url(account_id: int, db: AsyncSession = Depends(get_db)):
    """Return the Threads OAuth authorization URL for the given account."""
    from app.config import settings
    if not settings.threads_app_id:
        raise HTTPException(status_code=400, detail="threads_app_id is not configured")

    result = await db.execute(select(Account).where(Account.id == account_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")

    publisher = ThreadsAPIPublisher()
    url = publisher.generate_auth_url(account_id)
    return {"auth_url": url}


@router.get("/oauth/callback", response_class=HTMLResponse, include_in_schema=False)
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth redirect handler. Threads redirects here after the user grants access.
    The `state` parameter contains the account ID.
    This endpoint is excluded from the auth requirement so the browser redirect works.
    """
    try:
        account_id = int(state)
    except ValueError:
        return HTMLResponse("<h1>Invalid state parameter</h1>", status_code=400)

    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        return HTMLResponse(f"<h1>Account {account_id} not found</h1>", status_code=404)

    publisher = ThreadsAPIPublisher(db=db)
    try:
        token_data = await publisher.exchange_code(code)
    except Exception as e:
        return HTMLResponse(f"<h1>Token exchange failed</h1><p>{e}</p>", status_code=500)

    account.api_token = token_data["access_token"]
    account.threads_user_id = token_data["user_id"]
    account.token_expires_at = token_data["expires_at"]
    await db.commit()

    return HTMLResponse(
        f"<h1>Authorization successful</h1>"
        f"<p>Account <strong>{account.username}</strong> connected to Threads.</p>"
        f"<p>Token expires: {token_data['expires_at'].strftime('%Y-%m-%d %H:%M UTC')}</p>"
        f"<p>You can close this window.</p>"
    )


@router.post("/{account_id}/oauth/refresh", response_model=SuccessResponse)
async def refresh_oauth_token(account_id: int, db: AsyncSession = Depends(get_db)):
    """Refresh the long-lived access token for an account (valid for 60 days)."""
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if not account.api_token:
        raise HTTPException(status_code=400, detail="Account has no access token to refresh")

    publisher = ThreadsAPIPublisher(db=db)
    try:
        token_data = await publisher.refresh_token(account.api_token)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Token refresh failed: {e}")

    account.api_token = token_data["access_token"]
    account.token_expires_at = token_data["expires_at"]
    await db.commit()

    return SuccessResponse(
        message=f"Token refreshed, new expiry: {token_data['expires_at'].strftime('%Y-%m-%d %H:%M UTC')}"
    )


@router.get("/{account_id}/threads/info")
async def get_threads_info(account_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch the Threads profile for the given account."""
    result = await db.execute(select(Account).where(Account.id == account_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")

    publisher = ThreadsAPIPublisher(db=db)
    info = await publisher.get_account_info(account_id)
    if not info:
        raise HTTPException(status_code=502, detail="Failed to fetch Threads profile")
    return info
