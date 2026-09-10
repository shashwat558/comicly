from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import create_token, get_current_user, hash_password, verify_password
from app.models.user import User
from app.schemas.v1.auth import LoginRequest, SignupRequest, TokenResponse, UserOut

router = APIRouter()


@router.post("/signup", response_model=UserOut, status_code=201)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    existing = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.strip().lower()
    user = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    # same response for unknown email and wrong password, don't leak which
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password.")
    return TokenResponse(access_token=create_token(user.id))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
