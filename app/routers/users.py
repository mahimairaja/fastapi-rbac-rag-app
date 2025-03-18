from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from app.database import get_db
from app.models.user import User
from app.auth.jwt import get_current_active_user
from app.auth.authorization import authorize, require_permission
from app.auth.security import get_password_hash
from pydantic import BaseModel, EmailStr, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    is_active: bool
    
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)

class UserRoleUpdate(BaseModel):
    role: str = Field(..., description="User role (e.g., 'admin', 'user', 'moderator')")


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    To get current user profile.
    """
    return current_user


@router.get("/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    To get user by ID.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        logger.error(f"User {current_user.username} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not authorize(current_user, "read", user):
        logger.error(f"User {current_user.username} not authorized to read user {user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to read this user"
        )
    
    logger.info(f"User {user.username} accessed successfully by user {current_user.username}")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    To update user by ID.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        logger.error(f"User {current_user.username} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not authorize(current_user, "update", user):
        logger.error(f"User {current_user.username} not authorized to update user {user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )
    
    if user_update.username:
        existing_user = db.query(User).filter(User.username == user_update.username).first()
        if existing_user and existing_user.id != user_id:
            logger.error(f"Username {user_update.username} already taken")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        user.username = user_update.username
    
    if user_update.email:
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user and existing_user.id != user_id:
            logger.error(f"Email {user_update.email} already taken")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already taken"
            )
        user.email = user_update.email
    
    if user_update.password:
        user.hashed_password = get_password_hash(user_update.password)
    
    db.commit()
    db.refresh(user)
    logger.info(f"User {user.username} updated successfully by user {current_user.username}")
    
    return user


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_permission("read", "user"))
):
    """
    To list all users. Requires admin or moderator role.
    """
    db = next(get_db())
    users = db.query(User).offset(skip).limit(limit).all()
    logger.info(f"Listed {len(users)} users successfully by user {current_user.username}")
    return users


@router.put("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    current_user: User = Depends(require_permission("update", "user_role")),
    db: Session = Depends(get_db)
):
    """
    To update user role. Requires admin role.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        logger.error(f"User {current_user.username} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.role = role_update.role
    
    db.commit()
    db.refresh(user)
    logger.info(f"User {user.username} role updated successfully by user {current_user.username}")
    return user 