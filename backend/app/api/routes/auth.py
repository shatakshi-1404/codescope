from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.ratelimit import enforce_ip_limit
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(user, access: str, refresh: str) -> TokenResponse:
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(enforce_ip_limit)])
def register(body: RegisterRequest, db: DbSession):
    user, access, refresh = auth_service.register_user(
        db, name=body.name, email=body.email, password=body.password
    )
    return _token_response(user, access, refresh)


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(enforce_ip_limit)])
def login(body: LoginRequest, db: DbSession):
    user, access, refresh = auth_service.login_user(
        db, email=body.email, password=body.password
    )
    return _token_response(user, access, refresh)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: DbSession):
    user, access, new_refresh = auth_service.refresh_tokens(db, refresh_token=body.refresh_token)
    return _token_response(user, access, new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: LogoutRequest, db: DbSession):
    auth_service.logout_user(db, refresh_token=body.refresh_token)


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser):
    return user


@router.post("/forgot-password", response_model=ForgotPasswordResponse, dependencies=[Depends(enforce_ip_limit)])
def forgot_password(body: ForgotPasswordRequest, db: DbSession):
    token = auth_service.request_password_reset(db, email=body.email)
    # TODO(production): email the reset link here. No email provider is configured,
    # so outside development the token is simply not delivered.
    dev_token = token if (token and settings.app_env == "development") else None
    return ForgotPasswordResponse(
        message="If an account exists for that email, a password reset link has been created.",
        dev_reset_token=dev_token,
    )


@router.post("/reset-password", response_model=MessageResponse, dependencies=[Depends(enforce_ip_limit)])
def reset_password(body: ResetPasswordRequest, db: DbSession):
    auth_service.reset_password(db, token=body.token, new_password=body.new_password)
    return MessageResponse(message="Your password has been updated. Please sign in.")
