"""Authentication router for Firebase Auth."""
from fastapi import APIRouter, HTTPException, Depends
from firebase_admin import auth
from datetime import datetime
from typing import Optional
import httpx

from config import settings
from schemas.auth import UserInfo, UserRegisterRequest, UserLoginRequest, TokenResponse, RefreshTokenRequest, GoogleOAuthRequest
from services.firestore import firestore_service
from middleware.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    responses={
        200: {
            "description": "User registered successfully",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjA4MmU5NzVlMDdkZmE0OTYwYzdiN2I0ZmMxZDEwZjkxNmRjMmY1NWIiLCJ0eXAiOiJKV1QifQ...",
                        "refresh_token": "AMf-vBxAtBIKeMkKj0cZH79SHm3eQaH4kA2omfT2JV3f6h4aIvV1Mf89o6-ExkqWawmZ9kTpuxBtJ_w2dDjpZORRuXZ1CaqlViBst4ENA-hgp6QtjzKMzsKYNpcrEpAiflBMkPHRZc85eeomugbu2UJ5Pof8EXyb7yhIICqeQvV_2ctTYRwXVFLa49kRW6vL_K85nN1HR2zf9sEubsVqx6P0tl4-KOqnB6c_pNwmje6Wjz-hogjCu_8",
                        "token_type": "Bearer",
                        "expires_in": 3600
                    }
                }
            }
        },
        400: {
            "description": "Invalid registration data",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid registration data: Invalid email address"}
                }
            }
        },
        409: {
            "description": "User already exists",
            "content": {
                "application/json": {
                    "example": {"detail": "User with this email already exists"}
                }
            }
        }
    }
)
async def register_user(request: UserRegisterRequest):
    """
    Register a new user with email and password.
    
    Args:
        request: Registration request with email and password
        
    Returns:
        TokenResponse: Access token and refresh token
    """
    try:
        # Create user in Firebase Auth
        user_record = auth.create_user(
            email=request.email,
            password=request.password,
            display_name=request.name,
            email_verified=False
        )
        
        # Automatically create Default Project for new user
        try:
            firestore_service.create_project(user_record.uid, "Default Project")
        except Exception as e:
            # Log error but don't fail registration
            print(f"[AUTH] Failed to create Default Project for user {user_record.uid}: {e}")
        
        # After creating user, we need to get an ID token
        # We can use Firebase Auth REST API to sign in the newly created user
        api_key = settings.firebase_web_api_key
        
        if api_key:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}",
                        json={
                            "email": request.email,
                            "password": request.password,
                            "returnSecureToken": True
                        },
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return TokenResponse(
                            access_token=data["idToken"],
                            refresh_token=data["refreshToken"],
                            token_type="Bearer",
                            expires_in=int(data.get("expiresIn", 3600))
                        )
            except Exception:
                pass  # Fall back to custom token if REST API fails
        
        # Fallback: Return custom token (client exchanges for ID token)
        custom_token = auth.create_custom_token(user_record.uid)
        return TokenResponse(
            access_token=custom_token.decode('utf-8') if isinstance(custom_token, bytes) else custom_token,
            refresh_token="",  # Client will get refresh token when exchanging custom token
            token_type="Bearer",
            expires_in=3600
        )
        
    except ValueError as e:
        # Invalid email or password
        raise HTTPException(
            status_code=400,
            detail=f"Invalid registration data: {str(e)}"
        )
    except Exception as e:
        # User already exists or other error
        error_msg = str(e)
        if "email already exists" in error_msg.lower() or "already exists" in error_msg.lower():
            raise HTTPException(
                status_code=409,
                detail="User with this email already exists"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create user: {str(e)}"
        )


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjA4MmU5NzVlMDdkZmE0OTYwYzdiN2I0ZmMxZDEwZjkxNmRjMmY1NWIiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiVXNlciBPbmUiLCJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vdm94LXRyYW5zbGF0ZS1iOGM5NCIsImF1ZCI6InZveC10cmFuc2xhdGUtYjhjOTQiLCJhdXRoX3RpbWUiOjE3Njg3OTU2MjAsInVzZXJfaWQiOiJnd1dWc3NFZkhYZjFlMUMwRHRSQ1UyMW80MXgxIiwic3ViIjoiZ3dXVnNzRWZIWGYxZTFDMER0UkNVMjFvNDF4MSIsImlhdCI6MTc2ODc5NTYyMCwiZXhwIjoxNzY4Nzk5MjIwLCJlbWFpbCI6InVzZXIxQGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJlbWFpbCI6WyJ1c2VyMUBnbWFpbC5jb20iXX0sInNpZ25faW5fcHJvdmlkZXIiOiJwYXNzd29yZCJ9fQ.qxutW8WybEFvkHoEqYqACnrSZ4K3ufolaT8CbG4jNX8ZWb4uucjibw46WBFTC1mEHtfIT7AQ9XpXGgnJEgim6-MoMBo6i6DinxAB3UX9EHEL31HaNzIfaDYFvdLG6TcbZIqLFPdy6l0sjKt6EJl3acBDvV0FBBN90O171AdfwwQp8JNjMr8OE8_B-DgXrL16IhnekgmG2nTpPwZlJ0QwLNZCGhzS6St3cQhpOHtkxSVyE2VC4Nr0KdR14VV59CWYB8fREGbSaCx6xMc54M1WgM3ewNWeWpMy0Xfo8A3n32F-a7v_Zd09-pvHdZ3ijxOzuFjURM79aVWwrD8hk4PS5g",
                        "refresh_token": "AMf-vBxAtBIKeMkKj0cZH79SHm3eQaH4kA2omfT2JV3f6h4aIvV1Mf89o6-ExkqWawmZ9kTpuxBtJ_w2dDjpZORRuXZ1CaqlViBst4ENA-hgp6QtjzKMzsKYNpcrEpAiflBMkPHRZc85eeomugbu2UJ5Pof8EXyb7yhIICqeQvV_2ctTYRwXVFLa49kRW6vL_K85nN1HR2zf9sEubsVqx6P0tl4-KOqnB6c_pNwmje6Wjz-hogjCu_8",
                        "token_type": "Bearer",
                        "expires_in": 3600
                    }
                }
            }
        },
        401: {
            "description": "Invalid credentials",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid email or password"}
                }
            }
        },
        400: {
            "description": "Email/password auth disabled or other error",
            "content": {
                "application/json": {
                    "example": {"detail": "Email/password authentication is not enabled. Please enable it in Firebase Console > Authentication > Sign-in method > Email/Password"}
                }
            }
        }
    }
)
async def login_user(request: UserLoginRequest):
    """
    Login user with email and password.
    
    Verifies credentials using Firebase Auth REST API and returns ID token.
    
    Args:
        request: Login request with email and password
        
    Returns:
        TokenResponse: ID token and refresh token
    """
    try:
        # Use Firebase Auth REST API to verify password and get ID token
        # API endpoint: https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword
        api_key = settings.firebase_web_api_key
        
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="Firebase Web API key not configured. Please set FIREBASE_WEB_API_KEY in your .env file. You can find this key in Firebase Console > Project Settings > General > Web API Key"
            )
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}",
                json={
                    "email": request.email,
                    "password": request.password,
                    "returnSecureToken": True
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", "Login failed")
                
                # Check for API key errors
                if "API key not valid" in error_message or "INVALID_API_KEY" in error_message:
                    raise HTTPException(
                        status_code=500,
                        detail="Invalid Firebase Web API key. Please check your FIREBASE_WEB_API_KEY in .env file. Get it from Firebase Console > Project Settings > General > Web API Key"
                    )
                
                if "INVALID_PASSWORD" in error_message or "EMAIL_NOT_FOUND" in error_message:
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid email or password"
                    )
                if "PASSWORD_LOGIN_DISABLED" in error_message:
                    raise HTTPException(
                        status_code=400,
                        detail="Email/password authentication is not enabled. Please enable it in Firebase Console > Authentication > Sign-in method > Email/Password"
                    )
                raise HTTPException(
                    status_code=400,
                    detail=error_message
                )
            
            data = response.json()
            
            return TokenResponse(
                access_token=data["idToken"],
                refresh_token=data["refreshToken"],
                token_type="Bearer",
                expires_in=int(data.get("expiresIn", 3600))
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )


@router.post(
    "/google",
    response_model=TokenResponse,
    responses={
        200: {
            "description": "Google sign-in successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjA4MmU5NzVlMDdkZmE0OTYwYzdiN2I0ZmMxZDEwZjkxNmRjMmY1NWIiLCJ0eXAiOiJKV1QifQ...",
                        "refresh_token": "AMf-vBxAtBIKeMkKj0cZH79SHm3eQaH4kA2omfT2JV3f6h4aIvV1Mf89o6-ExkqWawmZ9kTpuxBtJ_w2dDjpZORRuXZ1CaqlViBst4ENA-hgp6QtjzKMzsKYNpcrEpAiflBMkPHRZc85eeomugbu2UJ5Pof8EXyb7yhIICqeQvV_2ctTYRwXVFLa49kRW6vL_K85nN1HR2zf9sEubsVqx6P0tl4-KOqnB6c_pNwmje6Wjz-hogjCu_8",
                        "token_type": "Bearer",
                        "expires_in": 3600
                    }
                }
            }
        },
        400: {
            "description": "Invalid Google ID token",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid Google ID token"}
                }
            }
        },
        500: {
            "description": "Firebase configuration error",
            "content": {
                "application/json": {
                    "example": {"detail": "Firebase Web API key not configured"}
                }
            }
        }
    }
)
async def google_sign_in(request: GoogleOAuthRequest):
    """
    Sign in or register user with Google OAuth.
    
    This endpoint accepts a Google ID token from the client (obtained via Google Sign-In)
    and exchanges it for Firebase credentials. If the user doesn't exist, they are
    automatically created.
    
    Client-side flow:
    1. User clicks "Sign in with Google"
    2. Client uses Google Sign-In SDK to get Google ID token
    3. Client sends Google ID token to this endpoint
    4. Server verifies token and returns Firebase credentials
    
    Args:
        request: Google OAuth request with ID token
        
    Returns:
        TokenResponse: Firebase ID token and refresh token
    """
    try:
        api_key = settings.firebase_web_api_key
        
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="Firebase Web API key not configured. Please set FIREBASE_WEB_API_KEY in your .env file. You can find this key in Firebase Console > Project Settings > General > Web API Key"
            )
        
        # Use Firebase Auth REST API to sign in with Google ID token
        # This will create the user if they don't exist
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp?key={api_key}",
                json={
                    "postBody": f"id_token={request.id_token}&providerId=google.com",
                    "requestUri": settings.google_redirect_uri,
                    "returnSecureToken": True,
                    "returnIdpCredential": True
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", "Google sign-in failed")
                
                # Check for API key errors
                if "API key not valid" in error_message or "INVALID_API_KEY" in error_message:
                    raise HTTPException(
                        status_code=500,
                        detail="Invalid Firebase Web API key. Please check your FIREBASE_WEB_API_KEY in .env file. Get it from Firebase Console > Project Settings > General > Web API Key"
                    )
                
                if "INVALID_IDP_RESPONSE" in error_message or "INVALID_ID_TOKEN" in error_message:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid Google ID token. Please ensure you're using a valid token from Google Sign-In."
                    )
                
                if "FEDERATED_USER_ID_ALREADY_LINKED" in error_message:
                    raise HTTPException(
                        status_code=409,
                        detail="This Google account is already linked to another user."
                    )
                
                raise HTTPException(
                    status_code=400,
                    detail=f"Google sign-in failed: {error_message}"
                )
            
            data = response.json()
            
            # Check if this is a new user
            is_new_user = data.get("isNewUser", False)
            if is_new_user:
                try:
                    # Automatically create Default Project for new user
                    user_id = data.get("localId")
                    if user_id:
                        firestore_service.create_project(user_id, "Default Project")
                except Exception as e:
                    print(f"[AUTH] Failed to create Default Project for Google user: {e}")
            
            return TokenResponse(
                access_token=data["idToken"],
                refresh_token=data["refreshToken"],
                token_type="Bearer",
                expires_in=int(data.get("expiresIn", 3600))
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Google sign-in failed: {str(e)}"
        )



@router.get(
    "/me",
    response_model=UserInfo,
    responses={
        200: {
            "description": "User information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "user_id": "gwWVssEfHXf1e1C0DtRCU21o41x1",
                        "email": "user1@gmail.com",
                        "name": "User One",
                        "auth_provider": "email",
                        "created_at": "2026-01-18T19:51:14.015000"
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized - Invalid or missing token",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated"}
                }
            }
        }
    }
)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
) -> UserInfo:
    """
    Get current authenticated user information.
    
    Note: Most authentication happens client-side with Firebase SDK.
    This endpoint just returns the user info from the verified token.
    
    Args:
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        UserInfo: User information
    """
    # Get additional user info from Firebase Auth if needed
    try:
        firebase_user = auth.get_user(current_user["user_id"])
        
        return UserInfo(
            user_id=current_user["user_id"],
            email=current_user.get("email") or firebase_user.email,
            name=current_user.get("name") or firebase_user.display_name,
            auth_provider=_get_auth_provider(firebase_user),
            created_at=datetime.fromtimestamp(firebase_user.user_metadata.creation_timestamp / 1000)
        )
    except Exception as e:
        # Fallback to token info if Firebase lookup fails
        return UserInfo(
            user_id=current_user["user_id"],
            email=current_user.get("email"),
            name=current_user.get("name"),
            auth_provider="unknown",
            created_at=datetime.utcnow()
        )


def _get_auth_provider(firebase_user) -> str:
    """Extract auth provider from Firebase user."""
    if not firebase_user.provider_data:
        return "email"
    
    # Check provider IDs
    for provider in firebase_user.provider_data:
        provider_id = provider.provider_id
        if provider_id == "google.com":
            return "google"
        elif provider_id == "apple.com":
            return "apple"
        elif provider_id == "password":
            return "email"
    
    return "email"


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh Firebase ID token using refresh token.
    
    Firebase ID tokens expire after 1 hour. Use this endpoint to get a new
    access token using the refresh token.
    
    Args:
        request: Refresh token request
        
    Returns:
        TokenResponse: New access token and refresh token
    """
    try:
        api_key = settings.firebase_web_api_key
        
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="Firebase Web API key not configured. Please set FIREBASE_WEB_API_KEY in your .env file. You can find this key in Firebase Console > Project Settings > General > Web API Key"
            )
        
        # Use Firebase Auth REST API to refresh token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://securetoken.googleapis.com/v1/token?key={api_key}",
                json={
                    "grant_type": "refresh_token",
                    "refresh_token": request.refresh_token
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", "Token refresh failed")
                
                raise HTTPException(
                    status_code=401,
                    detail=error_message
                )
            
            data = response.json()
            
            return TokenResponse(
                access_token=data["id_token"],
                refresh_token=data["refresh_token"],
                token_type="Bearer",
                expires_in=int(data.get("expires_in", 3600))
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Token refresh failed: {str(e)}"
        )


@router.post("/verify-token")
async def verify_token(
    current_user: dict = Depends(get_current_user)
):
    """
    Verify Firebase ID token (optional endpoint for server-side verification).
    
    Most clients verify tokens client-side, but this can be used for
    server-side verification if needed.
    
    Args:
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        dict: Token verification result
    """
    return {
        "valid": True,
        "user_id": current_user["user_id"],
        "email": current_user.get("email")
    }
