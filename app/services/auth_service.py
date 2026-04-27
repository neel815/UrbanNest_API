import uuid
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MeResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
)
from app.utils.security import create_access_token, hash_password, verify_password


def extract_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        )
    return token


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = extract_token(authorization)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exception
        parsed_user_id = uuid.UUID(user_id)
    except JWTError as exc:
        raise credentials_exception from exc
    except ValueError as exc:
        raise credentials_exception from exc

    user = db.query(User).filter(User.id == parsed_user_id).first()
    if not user:
        raise credentials_exception

    return user


def get_current_user_optional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    if not authorization:
        return None
    try:
        return get_current_user(authorization=authorization, db=db)
    except HTTPException:
        return None


def can_create_role(creator_role: UserRole, target_role: UserRole) -> bool:
    if target_role == UserRole.SYSTEM_ADMIN:
        return False
    if creator_role == UserRole.SYSTEM_ADMIN:
        return target_role == UserRole.ADMIN
    if creator_role == UserRole.ADMIN:
        return target_role in {UserRole.RESIDENT, UserRole.SECURITY}
    return False


def login_user(payload: LoginRequest, db: Session) -> AuthResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if user.must_reset_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password setup required. Please use the link sent to your email.",
        )

    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role.value, "email": user.email}
    )
    return AuthResponse(
        access_token=access_token,
        user_id=str(user.id),
        role=user.role,
    )


def reset_password_user(payload: ResetPasswordRequest, db: Session) -> dict:
    user = (
        db.query(User)
        .filter(
            User.reset_token == payload.token,
            User.reset_token_expires_at.is_not(None),
            User.reset_token_expires_at > datetime.now(timezone.utc),
        )
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.hashed_password = hash_password(payload.password)
    user.must_reset_password = False
    user.reset_token = None
    user.reset_token_expires_at = None
    db.commit()
    return {"message": "Password set successfully"}


def register_user(
    payload: RegisterRequest,
    current_user: User | None,
    db: Session,
) -> AuthResponse:
    if current_user is None:
        if payload.role != UserRole.RESIDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Public registration is only available for resident accounts",
            )
    elif not can_create_role(current_user.role, payload.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to create this role",
        )

    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(
        {"sub": str(user.id), "role": user.role.value, "email": user.email}
    )
    return AuthResponse(
        access_token=access_token,
        user_id=str(user.id),
        role=user.role,
    )


def build_me_response(current_user: User) -> MeResponse:
    return MeResponse(
        user_id=str(current_user.id),
        full_name=current_user.full_name,
        email=current_user.email,
        role=current_user.role,
        profile_image_url=current_user.profile_image_url,
    )


def update_current_user_profile(
    payload: UpdateProfileRequest,
    current_user: User,
    db: Session,
) -> MeResponse:
    current_user.full_name = payload.full_name
    current_user.profile_image_url = payload.profile_image_url
    db.commit()
    db.refresh(current_user)
    return build_me_response(current_user)