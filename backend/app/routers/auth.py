# backend/app/routers/auth.py
from datetime import datetime, date
import secrets

from fastapi import APIRouter, Depends, HTTPException, Header, Response, Cookie
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.database import get_db, UserAccount
from app.services.esi_api_interface import (
    redirect_to_sso, request_token, verify_account, refresh_token
)


def generate_session_token():
    """Generate a simple session token"""
    return secrets.token_urlsafe(32)


async def refresh_user_token(user: UserAccount, db: AsyncSession) -> tuple[str|None, str|None]:
    if user.expires_at > datetime.now():
        return None, None  # still valid

    try:
        # Refresh Tokens + session key
        new_tokens = refresh_token(user.refresh_token)
        new_access_token = new_tokens["access_token"]
        new_refresh_token = new_tokens["refresh_token"]
        new_expires_at = new_tokens["ExpiresOn"]
        new_session_key = generate_session_token()

        # Update user record
        user.access_token = new_access_token
        user.refresh_token = new_refresh_token
        user.expires_at = new_expires_at
        user.session_key = new_session_key
        await db.commit()
        return new_access_token, new_session_key

    except Exception as e:
        # If refresh fails, invalidate the session
        user.session_key = None
        await db.commit()
        raise HTTPException(status_code=401, detail="Token refresh failed") from e


async def get_valid_access_token(response: Response,session: str = Cookie(None, alias="session"),db: AsyncSession = Depends(get_db),) -> str:
    if not session:
        raise HTTPException(status_code=401, detail="No session cookie")

    # Fetch User
    stmt = select(UserAccount).where(UserAccount.session_key == session)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Update Token?
    new_access_token, new_session_key = await refresh_user_token(user, db)

    if new_session_key:
        # Update session cookie
        response.set_cookie(
            key="session",
            value=new_session_key,
            httponly=True,
            secure=settings.ENV == "production",
            samesite="lax",
            path="/",
        )

    # Return the current access token (new or existing)
    return new_access_token if new_access_token else user.access_token




async def get_current_user_dep(
    response: Response,
    session: str = Cookie(None, alias="session"),
    db: AsyncSession = Depends(get_db),
) -> UserAccount:
    if not session:
        raise HTTPException(status_code=401, detail="No session cookie")

    stmt = select(UserAccount).where(UserAccount.session_key == session)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")

    _, new_session_key = await refresh_user_token(user, db)
    if new_session_key:
        response.set_cookie(
            key="session",
            value=new_session_key,
            httponly=True,
            secure=settings.ENV == "production",
            samesite="lax",
            path="/",
        )

    return user


# --- Routes ---
router = APIRouter(
    tags=["Authentication"]
)


@router.get("/auth/me")
async def get_current_user(user: UserAccount = Depends(get_current_user_dep)):
    return {
        "char_name": user.char_name,
        "id": user.id,
        "authenticated": True
    }


@router.post("/auth/logout")
async def logout(response: Response,session: str = Cookie(None, alias="session"),db: AsyncSession = Depends(get_db),):
    if session:
        stmt = select(UserAccount).where(UserAccount.session_key == session)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            user.session_key = None
            await db.commit()
    response.delete_cookie("session", path="/")
    return {"message": "Logged out"}



@router.get("/auth/sso_login")
def sso_login():
    url, _ = redirect_to_sso()
    return RedirectResponse(url)



@router.get("/auth/callback")
async def callback(code: str, db : AsyncSession = Depends(get_db)):
    auth = request_token(code)
    char = verify_account(auth)

    char_id = char["CharacterID"]
    char_name = char["CharacterName"]
    char_hash = char["CharacterOwnerHash"]
    scopes = char['Scopes']

    access_token = auth["access_token"]
    refresh_token = auth["refresh_token"]
    expires_at = char["ExpiresOn"]


    stmt = select(UserAccount).where(UserAccount.id == char_id )
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    session_key = generate_session_token()
    if existing_user:
        # Update existing user
        existing_user.char_name = char_name
        existing_user.char_hash = char_hash
        existing_user.access_token = access_token
        existing_user.refresh_token = refresh_token
        existing_user.expires_at = expires_at
        existing_user.scopes = scopes
        existing_user.session_key = session_key
        user = existing_user
    else:
        user = UserAccount(
            id=char_id,
            char_hash=char_hash,
            char_name=char_name,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scopes=scopes,
            session_key=session_key
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)
    
    #react_app_url = f"http://{settings.FRONTEND_URL}:{settings.FRONTEND_PORT}/?session_key={session_key}"
    react_app_url = f"http://{settings.FRONTEND_URL}:{settings.FRONTEND_PORT}"

    response = RedirectResponse(react_app_url)
    response.set_cookie(
        key="session",
        value=session_key,
        httponly=True,
        secure=settings.ENV == "production",
        samesite="lax",
        path="/",
    )
    return response