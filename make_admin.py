"""
Script to make a user an admin in the database.
"""
import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.user import User
from app.models.document import Document

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def make_user_admin(user_id):
    """Make a user an admin by ID."""
    db = SessionLocal()
    try:
        # Get user by ID
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            print(f"User with ID {user_id} not found!")
            return False
        
        # Update role to admin
        user.role = "admin"
        db.commit()
        
        print(f"User {user.username} (ID: {user.id}) is now an admin!")
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False
    finally:
        db.close()

def list_users():
    """List all users in the database."""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print("Available users:")
        for user in users:
            print(f"ID: {user.id}, Username: {user.username}, Email: {user.email}, Role: {user.role}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python make_admin.py [user_id]")
        print("Or use 'python make_admin.py list' to see all users")
        sys.exit(1)
    
    if sys.argv[1] == "list":
        list_users()
    else:
        try:
            user_id = int(sys.argv[1])
            make_user_admin(user_id)
        except ValueError:
            print("Error: user_id must be a number!")
            sys.exit(1) 