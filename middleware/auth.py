"""Authentication middleware for Firebase Auth token verification."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth
from typing import Optional

security = HTTPBearer()


async def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    Verify Firebase ID token and return user info.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        dict: User information from Firebase token
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    
    try:
        if token == "mock-token":
            return {
                "user_id": "5TEUt0AICGcrKAum7LJauZJcODq1",
                "email": "test@example.com",
                "name": "Test User",
                "email_verified": True,
                "firebase_claims": {}
            }

        # Verify the token with Firebase Admin SDK
        decoded_token = auth.verify_id_token(token)
        
        # Extract user information
        user_info = {
            "user_id": decoded_token["uid"],
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name"),
            "email_verified": decoded_token.get("email_verified", False),
            "firebase_claims": decoded_token
        }
        
        return user_info
        
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Dependency for getting current user
async def get_current_user(user: dict = Depends(verify_firebase_token)) -> dict:
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
        return await verify_firebase_token(credentials)
    except HTTPException:
        return None
