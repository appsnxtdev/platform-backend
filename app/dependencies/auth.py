from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import get_db
from app.models.user import User, UserRole
from app.services.supabase_service import supabase_service

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Verify JWT token and return the current user.
    Raises HTTPException if token is invalid or user is not found.
    """
    try:
        token = credentials.credentials
        
        # Verify token with Supabase and get user info
        supabase_user = await supabase_service.get_user(token)
        if not supabase_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database using Supabase ID
        supabase_id = supabase_user.id
        db_user = await get_user_by_supabase_id(db, supabase_id)
        if not db_user:
            logger.error(f"User with Supabase ID {supabase_id} found in Supabase but not in local database")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in system",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return db_user
        
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Check if the current user is active.
    """
    if not current_user.is_active():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    return current_user

async def get_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Check if the current user is an admin.
    """
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user

async def get_user_by_supabase_id(db: AsyncSession, supabase_id: str) -> User:
    """
    Get user from database by Supabase ID.
    """
    from sqlalchemy import select
    
    # Get user by Supabase ID
    query = select(User).where(User.supabase_id == supabase_id)
    result = await db.execute(query)
    user = result.scalars().first()
    
    return user 