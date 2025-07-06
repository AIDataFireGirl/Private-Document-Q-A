"""
Security Module for Private Document Q&A System.
Handles authentication, authorization, and security features.
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from functools import wraps

# Security imports
import bcrypt
from jose import JWTError, jwt

# Local imports
from config.settings import Config


class SecurityManager:
    """
    Security manager for handling authentication and authorization.
    
    This class provides functionality to:
    - Hash and verify passwords
    - Generate and validate JWT tokens
    - Manage user sessions
    - Implement access control
    """
    
    def __init__(self, config: Config):
        """
        Initialize the SecurityManager.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.secret_key = config.JWT_SECRET_KEY
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
        
        # In-memory session storage (use Redis in production)
        self.active_sessions = {}
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt(rounds=self.config.BCRYPT_LOG_ROUNDS)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password
            hashed_password: Hashed password string
            
        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            hashed_password.encode('utf-8')
        )
    
    def create_access_token(self, data: Dict[str, Any], 
                          expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: Data to encode in the token
            expires_delta: Optional expiration time
            
        Returns:
            JWT token string
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token data or None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
    
    def create_session(self, user_id: str, user_role: str = "user") -> Dict[str, Any]:
        """
        Create a new user session.
        
        Args:
            user_id: User identifier
            user_role: User role (admin, user, etc.)
            
        Returns:
            Session data including token
        """
        # Generate session ID
        session_id = secrets.token_urlsafe(32)
        
        # Create token data
        token_data = {
            "sub": user_id,
            "role": user_role,
            "session_id": session_id,
            "type": "access"
        }
        
        # Create access token
        access_token = self.create_access_token(token_data)
        
        # Store session
        session_data = {
            "user_id": user_id,
            "user_role": user_role,
            "session_id": session_id,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "is_active": True
        }
        
        self.active_sessions[session_id] = session_data
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "session_id": session_id,
            "user_id": user_id,
            "user_role": user_role
        }
    
    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate an active session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data if valid, None otherwise
        """
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        
        # Check if session is still active
        if not session.get("is_active", False):
            return None
        
        # Update last activity
        session["last_activity"] = datetime.utcnow()
        
        return session
    
    def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was invalidated, False otherwise
        """
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["is_active"] = False
            return True
        return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        current_time = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            # Check if session is older than 24 hours
            if (current_time - session["created_at"]).total_seconds() > 86400:
                expired_sessions.append(session_id)
        
        # Remove expired sessions
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
        
        return len(expired_sessions)
    
    def check_permission(self, user_role: str, required_role: str) -> bool:
        """
        Check if user has required permission.
        
        Args:
            user_role: User's role
            required_role: Required role for the action
            
        Returns:
            True if user has permission, False otherwise
        """
        role_hierarchy = {
            "admin": 3,
            "moderator": 2,
            "user": 1
        }
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
    
    def sanitize_input(self, input_string: str) -> str:
        """
        Sanitize user input to prevent injection attacks.
        
        Args:
            input_string: Raw input string
            
        Returns:
            Sanitized string
        """
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';']
        sanitized = input_string
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Limit length
        if len(sanitized) > 1000:
            sanitized = sanitized[:1000]
        
        return sanitized.strip()
    
    def generate_file_hash(self, file_path: str) -> str:
        """
        Generate a secure hash for file integrity checking.
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA256 hash of the file
        """
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    def validate_file_upload(self, filename: str, file_size: int) -> Dict[str, Any]:
        """
        Validate file upload for security.
        
        Args:
            filename: Name of the uploaded file
            file_size: Size of the file in bytes
            
        Returns:
            Validation result dictionary
        """
        result = {
            "valid": True,
            "errors": []
        }
        
        # Check file size
        if file_size > self.config.MAX_FILE_SIZE:
            result["valid"] = False
            result["errors"].append(f"File size exceeds maximum allowed size of {self.config.MAX_FILE_SIZE} bytes")
        
        # Check file extension
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in [f".{ext}" for ext in self.config.ALLOWED_EXTENSIONS]:
            result["valid"] = False
            result["errors"].append(f"File type {file_ext} is not allowed")
        
        # Check for potentially dangerous file names
        dangerous_patterns = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for pattern in dangerous_patterns:
            if pattern in filename:
                result["valid"] = False
                result["errors"].append("File name contains potentially dangerous characters")
                break
        
        return result
    
    def get_security_stats(self) -> Dict[str, Any]:
        """
        Get security statistics.
        
        Returns:
            Dictionary containing security statistics
        """
        return {
            "active_sessions": len(self.active_sessions),
            "bcrypt_rounds": self.config.BCRYPT_LOG_ROUNDS,
            "token_expire_minutes": self.access_token_expire_minutes,
            "max_file_size": self.config.MAX_FILE_SIZE,
            "allowed_extensions": self.config.ALLOWED_EXTENSIONS,
            "timestamp": datetime.now().isoformat()
        }


def require_auth(f):
    """
    Decorator to require authentication for API endpoints.
    
    Args:
        f: Function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # This would be implemented in the API layer
        # For now, just pass through
        return f(*args, **kwargs)
    return decorated_function


def require_role(required_role: str):
    """
    Decorator to require specific role for API endpoints.
    
    Args:
        required_role: Required role for the endpoint
        
    Returns:
        Decorator function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # This would be implemented in the API layer
            # For now, just pass through
            return f(*args, **kwargs)
        return decorated_function
    return decorator 