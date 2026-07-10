#backend/app/routers/auth.py

from datetime import datetime
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database_models.useraccount import UserAccount
from database import get_db
from esi import redirect_to_sso, request_token, verify_account, refresh_token
from config import SCOPES, FRONTEND_PORT, FRONTEND_URL


def generate_session_token():
    """Generate a simple session token"""
    return secrets.token_urlsafe(32)


router = APIRouter(
    tags=["Authentication"]
)

@router.get("/auth/validate_session")
async def validate_session(authorization : str = Header(...), db : AsyncSession = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    session_key = authorization.replace("Bearer ", "")

    stmt = select(UserAccount).where(UserAccount.session_key == session_key)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        today = datetime.today()
        if existing_user.expires_at > today:
            new_token = refresh_token(existing_user.refresh_token)
            existing_user.access_token = new_token["access_token"]
            existing_user.refresh_token = new_token["refresh_token"]
            existing_user.expires_at = new_token["ExpiresOn"]
            session_key = generate_session_token()
            existing_user.session_key = session_key
            await db.commit()
            await db.refresh(existing_user)


        return {
            "session_key" : session_key,
            "char_name" : existing_user.char_name
        }
    else:
        return {
            "session_key" : None,
            "char_name" : None
        }




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


    stmt = select(UserAccount).where(UserAccount.char_id == char_id)
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
        # Create new user
        print(f"NEW USER CREATED:{char_name} - {char_id}")
        user = UserAccount(
            char_id=char_id,
            char_hash=char_hash,
            char_name=char_name,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            scopes=scopes,
            session_key=session_key
        )
        db.add(user)
    
    # Commit to database
    await db.commit()
    await db.refresh(user)
    
    # Store user info in session or create JWT token for frontend
    # For now, we'll return success
    react_app_url = f"http://{FRONTEND_URL}:{FRONTEND_PORT}/?session_key={session_key}"
    return RedirectResponse(react_app_url)