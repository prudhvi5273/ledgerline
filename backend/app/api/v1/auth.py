from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from app.api.deps import get_current_user, get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password
)
from app.models.user import User
from app.schemas.auth import (
    RefreshTokenRequest,
    Token,
    UserLogin,
    UserRegister,
    UserResponse
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user account with secure password hashing."""
    stmt = select(User).where(User.email == payload.email.lower())
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    # Hash password securely
    hashed_password = get_password_hash(payload.password)
    user = User(
        email=payload.email.lower(),
        password_hash=hashed_password,
        full_name=payload.full_name,
        role=payload.role or "ACCOUNT_HOLDER",
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await AuditService.log_event(
        db=db,
        actor_id=user.id,
        event_type="USER_REGISTERED",
        status="SUCCESS",
        metadata_info={"email": user.email, "role": user.role}
    )
    await db.commit()

    return user


@router.post("/login", response_model=Token)
async def login(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate credentials and issue cryptographically signed JWTs."""
    stmt = select(User).where(User.email == payload.email.lower())
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        await AuditService.log_refusal_isolated(
            event_type="LOGIN_FAILED",
            refusal_reason="INVALID_CREDENTIALS",
            metadata_info={"email_attempted": payload.email.lower()}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support."
        )

    access_token = create_access_token(subject=str(user.id), role=user.role)
    refresh_token = create_refresh_token(subject=str(user.id), role=user.role)

    await AuditService.log_event(
        db=db,
        actor_id=user.id,
        event_type="LOGIN_SUCCESS",
        status="SUCCESS",
        metadata_info={"role": user.role}
    )
    await db.commit()

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Exchange a valid refresh token for a fresh access token."""
    try:
        token_data = decode_token(payload.refresh_token)
        if token_data.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type for refresh endpoint"
            )
        user_id_str = token_data.get("sub")
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    stmt = select(User).where(User.id == user_id_str)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer active or exists"
        )

    new_access_token = create_access_token(subject=str(user.id), role=user.role)
    new_refresh_token = create_refresh_token(subject=str(user.id), role=user.role)

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """Return profile details for the authenticated user."""
    return current_user
