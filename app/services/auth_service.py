import uuid
from datetime import datetime, timezone, timedelta
import secrets
import logging

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.database import get_db
from app.models.security import SecurityProfile
from app.models.resident import ResidentProfile
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
from app.services.email_service import send_password_reset

logger = logging.getLogger(__name__)


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


def request_password_reset(email: str, db: Session) -> dict:
    """Generate a password reset token and send reset email."""
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # For security, don't reveal if email exists or not
        return {"message": "If an account with that email exists, a reset link has been sent."}
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    user.reset_token = reset_token
    user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()
    
    # Build reset link
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    
    # Send password reset email
    try:
        send_password_reset(
            to_email=user.email,
            to_name=user.full_name,
            reset_link=reset_link,
        )
    except Exception as e:
        logger.warning(f"Failed to send password reset email: {str(e)}")
    
    return {"message": "If an account with that email exists, a reset link has been sent."}


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
    db.flush()

    if payload.role == UserRole.RESIDENT:
        db.add(ResidentProfile(user_id=user.id))

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


def build_me_response(current_user: User, db: Session) -> MeResponse:
    security_profile = None
    if current_user.role == UserRole.SECURITY:
        security_profile = (
            db.query(SecurityProfile)
            .options(joinedload(SecurityProfile.assigned_building))
            .filter(SecurityProfile.user_id == current_user.id)
            .first()
        )
    return MeResponse(
        user_id=str(current_user.id),
        full_name=current_user.full_name,
        email=current_user.email,
        role=current_user.role,
        profile_image=current_user.profile_image,
        shift=security_profile.shift.value if security_profile and security_profile.shift else None,
        assigned_building_name=security_profile.assigned_building.name if security_profile and security_profile.assigned_building else None,
        badge_number=security_profile.badge_number if security_profile else None,
    )


def update_current_user_profile(
    payload: UpdateProfileRequest,
    current_user: User,
    db: Session,
) -> MeResponse:
    current_user.full_name = payload.full_name
    current_user.profile_image = payload.profile_image
    db.commit()
    db.refresh(current_user)
    return build_me_response(current_user, db)