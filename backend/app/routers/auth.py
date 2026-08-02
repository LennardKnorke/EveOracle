# backend/app/routers/auth.py


from datetime import datetime
import secrets

from fastapi import APIRouter, Depends, HTTPException, Header, Response, Cookie
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, UserAccount
from app.services.esi_api_interface import redirect_to_sso, request_token, verify_account, refresh_token
from app.core.config import settings


def generate_session_token():
    """Generate a simple session token"""
    return secrets.token_urlsafe(32)


router = APIRouter(
    tags=["Authentication"]
)

@router.get("/auth/me")
async def get_current_user(
    response: Response,
    session: str = Cookie(None, alias="session"),  # reads the HttpOnly cookie
    db: AsyncSession = Depends(get_db)
):
    if not session:
        raise HTTPException(status_code=401, detail="No session cookie")

    # Look up user by session_key
    stmt = select(UserAccount).where(UserAccount.session_key == session)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Check if EVE token needs refresh
    today = datetime.today()
    new_session_key = None

    if user.expires_at <= today:
        try:
            new_tokens = refresh_token(user.refresh_token)
            user.access_token = new_tokens["access_token"]
            user.refresh_token = new_tokens["refresh_token"]
            user.expires_at = new_tokens["ExpiresOn"]
            # Rotate session key
            new_session_key = generate_session_token()
            user.session_key = new_session_key
            await db.commit()
        except Exception:
            # Refresh failed – invalidate session
            user.session_key = None
            await db.commit()
            raise HTTPException(status_code=401, detail="Token refresh failed")

    # If we rotated the session key, set a new cookie
    if new_session_key:
        response.set_cookie(
            key="session",
            value=new_session_key,
            httponly=True,
            secure=settings.ENV == "production",  # use config
            samesite="lax",
            path="/",
        )

    # Return user info (no session key!)
    return {
        "char_name": user.char_name,
        "id": user.id,
        "authenticated": True
    }




@router.get("/auth/sso_login")
def sso_login():
    url, _ = redirect_to_sso()
    return RedirectResponse(url)



@router.get("/auth/callback")
async def callback(code: str, db : AsyncSession = Depends(get_db)):
    auth = request_token(code)
    char = verify_account(auth)

    id = char["CharacterID"]
    char_name = char["CharacterName"]
    char_hash = char["CharacterOwnerHash"]
    scopes = char['Scopes']

    access_token = auth["access_token"]
    refresh_token = auth["refresh_token"]
    expires_at = char["ExpiresOn"]


    stmt = select(UserAccount).where(UserAccount.id == id)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    session_key = generate_session_token()
    if existing_user:
        print(f"UPDATED USER:{char_name} - {id}")
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
        print(f"NEW USER CREATED:{char_name} - {id}")
        user = UserAccount(
            id=id,
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


@router.post("/auth/logout")
async def logout(response: Response, session: str = Cookie(None, alias="session"), db: AsyncSession = Depends(get_db)):
    if session:
        stmt = select(UserAccount).where(UserAccount.session_key == session)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            user.session_key = None
            await db.commit()
    
    # Delete the cookie
    response.delete_cookie("session", path="/")
    return {"message": "Logged out"}