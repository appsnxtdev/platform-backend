from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.supabase_service import supabase_service
from app.schemas.auth import (
    UserSignUp,
    UserSignIn,
    UserSignOut,
    TokenResponse,
    UserResponse,
    PasswordReset,
    PasswordUpdate,
    EmailVerification,
    RefreshToken,
    SignInResponse,
)
from app.models.user import User
from sqlalchemy import select
from loguru import logger
from datetime import datetime

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/signup", response_model=UserResponse)
async def sign_up(
    user_data: UserSignUp,
    db: AsyncSession = Depends(get_db)
):
    """Sign up a new user."""
    try:
        # Check if the user already exists
        existing_user = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if existing_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists."
            )

        # Create user in Supabase Auth
        supabase_user = await supabase_service.sign_up(
            email=user_data.email,
            password=user_data.password,
            user_data={
                "full_name": user_data.full_name,
                "company": user_data.company,
                "phone": user_data.phone
            }
        )

        # Create user in our database
        db_user = User(
            supabase_id=supabase_user.id,
            email=user_data.email,
            full_name=user_data.full_name,
            company=user_data.company,
            phone=user_data.phone
        )
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)

        user_dict = db_user.to_dict()
        # Add is_verified field from Supabase user data
        user_dict["is_verified"] = supabase_user.email_confirmed_at is not None
        # Convert is_active from method to property
        user_dict["is_active"] = db_user.is_active()
        
        return UserResponse(**user_dict)

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in sign up: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@auth_router.post("/signin", response_model=SignInResponse)
async def sign_in(
    user_data: UserSignIn,
    db: AsyncSession = Depends(get_db)
):
    """Sign in a user."""
    try:
        # Authenticate with Supabase
        supabase_response = await supabase_service.sign_in(
            email=user_data.email,
            password=user_data.password
        )
        supabase_user = supabase_response["user"]
        supabase_session = supabase_response["session"]

        # Get user from our database
        result = await db.execute(
            select(User).where(User.supabase_id == supabase_user.id)
        )
        db_user = result.scalar_one_or_none()

        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if not db_user.is_active():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not active"
            )

        # Update last login
        db_user.last_login_at = datetime.utcnow()
        await db.commit()

        # Prepare user response
        user_dict = db_user.to_dict()
        user_dict["is_verified"] = supabase_user.email_confirmed_at is not None
        user_dict["is_active"] = db_user.is_active()
        user_response = UserResponse(**user_dict)

        # Return combined response
        return {
            "user": user_response,
            "session": supabase_session
        }

    except Exception as e:
        logger.error(f"Error in sign in: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@auth_router.post("/signout")
async def sign_out(
    user_data: UserSignOut
):
    """Sign out a user."""
    try:
        await supabase_service.sign_out(user_data.access_token)
        return {"message": "Successfully signed out"}
    except Exception as e:
        logger.error(f"Error in sign out: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@auth_router.post("/reset-password")
async def reset_password(
    user_data: PasswordReset
):
    """Request password reset."""
    try:
        await supabase_service.reset_password(user_data.email)
        return {"message": "Password reset email sent"}
    except Exception as e:
        logger.error(f"Error in password reset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@auth_router.post("/update-password")
async def update_password(
    user_data: PasswordUpdate
):
    """Update user password."""
    try:
        await supabase_service.update_password(
            access_token=user_data.access_token,
            current_password=user_data.current_password,
            new_password=user_data.new_password
        )
        return {"message": "Password updated successfully"}
    except Exception as e:
        logger.error(f"Error in password update: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update password: {str(e)}"
        )

@auth_router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    user_data: RefreshToken
):
    """Refresh access token."""
    try:
        session = await supabase_service.refresh_token(user_data.refresh_token)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to refresh token"
            )
            
        return TokenResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            token_type="bearer",
            expires_in=session.expires_in
        )
    except Exception as e:
        logger.error(f"Error in token refresh: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
