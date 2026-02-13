"""Authentication middleware for Firebase Auth token verification."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from jose import jwt, JWTError
from config import settings
from services.supabase_db import supabase_service

security = HTTPBearer()


async def verify_supabase_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify Supabase ID token and return user info.
    """
    token = credentials.credentials
    
    try:
        # 1. Try local verification if secret is available
        if settings.supabase_jwt_secret:
            try:
                payload = jwt.decode(
                    token, 
                    settings.supabase_jwt_secret, 
                    algorithms=["HS256"],
                    options={"verify_aud": False}
                )
                return {
                    "user_id": payload.get("sub"),
                    "email": payload.get("email"),
                    "name": payload.get("user_metadata", {}).get("name"),
                    "claims": payload
                }
            except JWTError as e:
                print(f"[AUTH] Local JWT verification failed: {e}")
                # Fallback to Supabase API check

        # 2. Fallback to Supabase API verification
        # This is slower but works even without JWT_SECRET
        try:
            # We set the current session to verify token
            user_response = supabase_service.client.auth.get_user(token)
            if user_response.user:
                user = user_response.user
                return {
                    "user_id": user.id,
                    "email": user.email,
                    "name": user.user_metadata.get("name"),
                    "claims": user.dict()
                }
        except Exception as e:
            print(f"[AUTH] Supabase API verification failed: {e}")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Dependency for getting current user
async def get_current_user(user: dict = Depends(verify_supabase_token)) -> dict:
    """
    Get current authenticated user from Firebase token.
    
    This is the main dependency to use in route handlers.
    
    Example:
        @router.get("/endpoint")
        async def my_endpoint(current_user: dict = Depends(get_current_user)):
            user_id = current_user["user_id"]
            ...
    """
    return user


# Dependency for optional authentication (for public endpoints)
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    """
    Get current user if token is provided, otherwise return None.
    
    Useful for endpoints that work both with and without authentication.
    """
    if not credentials:
        return None
    
    try:
        return await verify_supabase_token(credentials)
    except HTTPException:
        return None
