from oso import Oso
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
from app.models.user import User
from app.auth.jwt import get_current_active_user
from app.database import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

oso = Oso()

def init_oso():
    """This function initializes Oso with policy and classes."""
    from app.models.user import User

    oso.register_class(User)
    oso.load_files(["app/policy.polar"])
    logger.info("Oso initialized")


def authorize(user: User, action: str, resource) -> bool:
    """
    This function checks if a user is authorized to perform an action on a resource.
    """
    return oso.is_allowed(user, action, resource)


def require_permission(action: str, resource_type: str):
    """
    This function creates a dependency to require permission for an action.
    """
    async def check_permission(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ):
        if not authorize(current_user, action, resource_type):
            logger.error(f"User {current_user.id} is not authorized to {action} {resource_type}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to {action} {resource_type}"
            )
        logger.info(f"User {current_user.id} is authorized to {action} {resource_type}")
        return current_user
    
    return check_permission


def check_resource_permission(action: str, resource):
    """
    This function checks permission for a specific resource instance.
    """
    async def check_permission(
        current_user: User = Depends(get_current_active_user)
    ):
        if not authorize(current_user, action, resource):
            logger.error(f"User {current_user.id} is not authorized to {action} this resource")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to {action} this resource"
            )
        logger.info(f"User {current_user.id} is authorized to {action} this resource")
        return current_user
    
    return check_permission 