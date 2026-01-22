"""Authentication-related Pydantic schemas."""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserRegisterRequest(BaseModel):
    """Request model for user registration."""
    email: EmailStr = Field(..., example="newuser@example.com", description="User's email address")
    password: str = Field(..., example="password123", min_length=6, description="User's password (min 6 characters)")
    name: Optional[str] = Field(None, example="New User", description="User's display name (optional)")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "newuser@example.com",
                "password": "password123",
                "name": "New User"
            }
        }


class UserLoginRequest(BaseModel):
    """Request model for user login."""
    email: EmailStr = Field(..., example="user1@gmail.com", description="User's email address")
    password: str = Field(..., example="123456", description="User's password")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user1@gmail.com",
                "password": "123456"
            }
        }


class TokenResponse(BaseModel):
    """Response model for token exchange."""
    access_token: str = Field(..., example="eyJhbGciOiJSUzI1NiIsImtpZCI6IjA4MmU5NzVlMDdkZmE0OTYwYzdiN2I0ZmMxZDEwZjkxNmRjMmY1NWIiLCJ0eXAiOiJKV1QifQ...", description="Firebase ID token (JWT)")
    refresh_token: str = Field(..., example="AMf-vBxAtBIKeMkKj0cZH79SHm3eQaH4kA2omfT2JV3f6h4aIvV1Mf89o6-ExkqWawmZ9kTpuxBtJ_w2dDjpZORRuXZ1CaqlViBst4ENA-hgp6QtjzKMzsKYNpcrEpAiflBMkPHRZc85eeomugbu2UJ5Pof8EXyb7yhIICqeQvV_2ctTYRwXVFLa49kRW6vL_K85nN1HR2zf9sEubsVqx6P0tl4-KOqnB6c_pNwmje6Wjz-hogjCu_8", description="Refresh token for getting new access tokens")
    token_type: str = Field(default="Bearer", example="Bearer", description="Token type")
    expires_in: int = Field(default=3600, example=3600, description="Token expiration time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjA4MmU5NzVlMDdkZmE0OTYwYzdiN2I0ZmMxZDEwZjkxNmRjMmY1NWIiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiVXNlciBPbmUiLCJpc3MiOiJodHRwczovL3NlY3VyZXRva2VuLmdvb2dsZS5jb20vdm94LXRyYW5zbGF0ZS1iOGM5NCIsImF1ZCI6InZveC10cmFuc2xhdGUtYjhjOTQiLCJhdXRoX3RpbWUiOjE3Njg3OTU2MjAsInVzZXJfaWQiOiJnd1dWc3NFZkhYZjFlMUMwRHRSQ1UyMW80MXgxIiwic3ViIjoiZ3dXVnNzRWZIWGYxZTFDMER0UkNVMjFvNDF4MSIsImlhdCI6MTc2ODc5NTYyMCwiZXhwIjoxNzY4Nzk5MjIwLCJlbWFpbCI6InVzZXIxQGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjpmYWxzZSwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJlbWFpbCI6WyJ1c2VyMUBnbWFpbC5jb20iXX0sInNpZ25faW5fcHJvdmlkZXIiOiJwYXNzd29yZCJ9fQ.qxutW8WybEFvkHoEqYqACnrSZ4K3ufolaT8CbG4jNX8ZWb4uucjibw46WBFTC1mEHtfIT7AQ9XpXGgnJEgim6-MoMBo6i6DinxAB3UX9EHEL31HaNzIfaDYFvdLG6TcbZIqLFPdy6l0sjKt6EJl3acBDvV0FBBN90O171AdfwwQp8JNjMr8OE8_B-DgXrL16IhnekgmG2nTpPwZlJ0QwLNZCGhzS6St3cQhpOHtkxSVyE2VC4Nr0KdR14VV59CWYB8fREGbSaCx6xMc54M1WgM3ewNWeWpMy0Xfo8A3n32F-a7v_Zd09-pvHdZ3ijxOzuFjURM79aVWwrD8hk4PS5g",
                "refresh_token": "AMf-vBxAtBIKeMkKj0cZH79SHm3eQaH4kA2omfT2JV3f6h4aIvV1Mf89o6-ExkqWawmZ9kTpuxBtJ_w2dDjpZORRuXZ1CaqlViBst4ENA-hgp6QtjzKMzsKYNpcrEpAiflBMkPHRZc85eeomugbu2UJ5Pof8EXyb7yhIICqeQvV_2ctTYRwXVFLa49kRW6vL_K85nN1HR2zf9sEubsVqx6P0tl4-KOqnB6c_pNwmje6Wjz-hogjCu_8",
                "token_type": "Bearer",
                "expires_in": 3600
            }
        }


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str = Field(..., example="AMf-vBxAtBIKeMkKj0cZH79SHm3eQaH4kA2omfT2JV3f6h4aIvV1Mf89o6-ExkqWawmZ9kTpuxBtJ_w2dDjpZORRuXZ1CaqlViBst4ENA-hgp6QtjzKMzsKYNpcrEpAiflBMkPHRZc85eeomugbu2UJ5Pof8EXyb7yhIICqeQvV_2ctTYRwXVFLa49kRW6vL_K85nN1HR2zf9sEubsVqx6P0tl4-KOqnB6c_pNwmje6Wjz-hogjCu_8", description="Refresh token from previous login")

    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "AMf-vBxAtBIKeMkKj0cZH79SHm3eQaH4kA2omfT2JV3f6h4aIvV1Mf89o6-ExkqWawmZ9kTpuxBtJ_w2dDjpZORRuXZ1CaqlViBst4ENA-hgp6QtjzKMzsKYNpcrEpAiflBMkPHRZc85eeomugbu2UJ5Pof8EXyb7yhIICqeQvV_2ctTYRwXVFLa49kRW6vL_K85nN1HR2zf9sEubsVqx6P0tl4-KOqnB6c_pNwmje6Wjz-hogjCu_8"
            }
        }


class UserInfo(BaseModel):
    """User information model."""
    user_id: str = Field(..., example="gwWVssEfHXf1e1C0DtRCU21o41x1", description="Firebase user ID (UID)")
    email: Optional[str] = Field(None, example="user1@gmail.com", description="User's email address")
    name: Optional[str] = Field(None, example="User One", description="User's display name")
    auth_provider: str = Field(..., example="email", description="Authentication provider: 'email', 'google', or 'apple'")
    created_at: datetime = Field(..., example="2026-01-18T19:51:14.015000", description="Account creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "gwWVssEfHXf1e1C0DtRCU21o41x1",
                "email": "user1@gmail.com",
                "name": "User One",
                "auth_provider": "email",
                "created_at": "2026-01-18T19:51:14.015000"
            }
        }


class AuthCallbackResponse(BaseModel):
    """Response model for OAuth callback."""
    message: str
    access_token: str
    refresh_token: str
    user: UserInfo


class YouTubeConnectionResponse(BaseModel):
    """Response model for YouTube channel connection."""
    connection_id: str
    youtube_channel_id: str
    youtube_channel_name: Optional[str] = None
    channel_avatar_url: Optional[str] = None
    is_primary: bool
    connected_at: datetime
    connection_type: Optional[str] = None  # "master" or "satellite" (language channel)
    master_connection_id: Optional[str] = None  # If satellite, the master connection ID


class YouTubeConnectionListResponse(BaseModel):
    """Response model for list of YouTube connections."""
    connections: list[YouTubeConnectionResponse]
    total: int


class UpdateConnectionRequest(BaseModel):
    """Request model for updating YouTube connection settings."""
    is_primary: Optional[bool] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_primary": True
            }
        }