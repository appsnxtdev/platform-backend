from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class UserSignUp(BaseModel):
    """Schema for user sign up."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    company: Optional[str] = None
    phone: Optional[str] = None


class UserSignIn(BaseModel):
    """Schema for user sign in."""
    email: EmailStr
    password: str


class UserSignOut(BaseModel):
    """Schema for user sign out."""
    access_token: str


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class UserResponse(BaseModel):
    """Schema for user response."""
    id: int
    supabase_id: str
    email: str
    full_name: str
    company: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    is_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class SignInResponse(BaseModel):
    """Schema for sign in response that includes both user and token details."""
    user: UserResponse
    session: TokenResponse

class PasswordReset(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class PasswordUpdate(BaseModel):
    """Schema for password update."""
    access_token: str
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)


class EmailVerification(BaseModel):
    """Schema for email verification."""
    email: EmailStr

class RefreshToken(BaseModel):
    """Schema for token refresh."""
    refresh_token: str