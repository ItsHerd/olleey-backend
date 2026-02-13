"""Authentication router for Supabase Auth."""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from typing import Optional
import httpx

from config import settings
from schemas.auth import UserInfo, UserRegisterRequest, UserLoginRequest, TokenResponse, RefreshTokenRequest, GoogleOAuthRequest
from services.supabase_db import supabase_service
from middleware.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=TokenResponse)
async def register_user(request: UserRegisterRequest):
    """
    Deprecated: Users should register via Supabase client-side.
    """
    raise HTTPException(
        status_code=400,
        detail="Registration should be handled via Supabase client-side."
    )


@router.post("/login", response_model=TokenResponse)
async def login_user(request: UserLoginRequest):
    """
    Deprecated: Users should login via Supabase client-side.
    """
    raise HTTPException(
        status_code=400,
        detail="Login should be handled via Supabase client-side."
    )


@router.post("/google", response_model=TokenResponse)
async def google_sign_in(request: GoogleOAuthRequest):
    """
    Deprecated: Google sign-in should be handled via Supabase client-side.
    """
    raise HTTPException(
        status_code=400,
        detail="Google sign-in should be handled via Supabase client-side."
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
) -> UserInfo:
    """
    Get current authenticated user information from Supabase.
    """
    try:
        # User info is already extracted in middleware
        return UserInfo(
            user_id=current_user["user_id"],
            email=current_user.get("email"),
            name=current_user.get("name") or "User",
            auth_provider=current_user.get("claims", {}).get("app_metadata", {}).get("provider", "email"),
            created_at=datetime.utcnow() # Can be improved by parsing from claims if needed
        )
    except Exception as e:
        print(f"[AUTH] Error in /me: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Deprecated: Token refresh should be handled via Supabase client-side.
    """
    raise HTTPException(
        status_code=400,
        detail="Token refresh should be handled via Supabase client-side."
    )


@router.post("/logout")
async def logout(
    current_user: dict = Depends(get_current_user)
):
    """
    Logout confirmation.
    """
    return {
        "success": True,
        "message": "Logged out successfully"
    }
