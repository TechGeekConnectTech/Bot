from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr
import bcrypt

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.core.logging_config import get_auth_logger, get_user_logger
import logging

logger = logging.getLogger(__name__)
auth_logger = get_auth_logger()
user_logger = get_user_logger()

router = APIRouter()
security = HTTPBearer()

# Use direct bcrypt instead of passlib for better compatibility
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto",
    bcrypt__rounds=12,
    bcrypt__ident="2b"
)

# Pydantic models
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    department: str = "DC Automation Support"

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_info: dict

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    department: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using bcrypt with proper error handling"""
    try:
        # Ensure password is not too long for bcrypt (72 byte limit)
        if len(plain_password.encode('utf-8')) > 72:
            plain_password = plain_password.encode('utf-8')[:72].decode('utf-8')
        
        # Use direct bcrypt for verification to avoid passlib compatibility issues
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        print(f"Password verification error: {e}")
        # Fallback to passlib if bcrypt fails
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as fallback_error:
            print(f"Fallback verification error: {fallback_error}")
            return False

def get_password_hash(password: str) -> str:
    """Generate password hash using bcrypt"""
    # Ensure password is not too long for bcrypt
    if len(password.encode('utf-8')) > 72:
        password = password.encode('utf-8')[:72].decode('utf-8')
    
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            auth_logger.warning("Token validation failed - No username in token payload")
            raise credentials_exception
    except JWTError as e:
        auth_logger.warning(f"Token validation failed - JWT error: {str(e)}")
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        auth_logger.warning(f"Token validation failed - User not found: {username}")
        raise credentials_exception
    
    # Log successful token validation (less frequent to avoid log spam)
    logger.debug(f"Token validated successfully for user: {username}")
    return user

def get_admin_user(current_user: User = Depends(get_current_user)):
    """Dependency to ensure current user is an admin"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# Routes
@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        department=user_data.department
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.post("/login", response_model=Token)
async def login_user(user_data: UserLogin, request: Request = None, db: Session = Depends(get_db)):
    client_ip = request.client.host if request else "unknown"
    username = user_data.username
    
    auth_logger.info(f"Login attempt - Username: {username}, IP: {client_ip}")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        auth_logger.warning(f"Failed login - User not found: {username}, IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(user_data.password, user.hashed_password):
        auth_logger.warning(f"Failed login - Invalid password: {username}, IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    auth_logger.info(f"Successful login - User: {user.full_name} ({username}), Role: {user.role}, Department: {user.department}, IP: {client_ip}")
    user_logger.info(f"User session started - {user.full_name} ({username}) logged in from {client_ip}")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_info": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "department": user.department,
            "role": user.role
        }
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user