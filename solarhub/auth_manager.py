"""
Authentication Manager
Handles user registration, login, and session management
"""

import sqlite3
import hashlib
import secrets
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import os

log = logging.getLogger(__name__)


class AuthManager:
    """Manages user authentication and sessions."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            base = os.path.expanduser("~/.solarhub")
            os.makedirs(base, exist_ok=True)
            db_path = os.path.join(base, "solarhub.db")
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the users and sessions tables."""
        try:
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            
            # Create users table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            """)
            
            # Create sessions table for token-based authentication
            cur.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(token)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)")
            
            con.commit()
            con.close()
            log.info("Authentication tables initialized successfully")
            
        except Exception as e:
            log.error(f"Failed to initialize authentication tables: {e}", exc_info=True)
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using PBKDF2."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 100k iterations
        )
        return f"{salt}:{password_hash.hex()}"
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against a hash."""
        try:
            salt, stored_hash = password_hash.split(':')
            password_hash_check = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            return password_hash_check.hex() == stored_hash
        except Exception as e:
            log.error(f"Password verification error: {e}")
            return False
    
    def _generate_token(self) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(32)
    
    def register_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str
    ) -> Dict[str, Any]:
        """Register a new user."""
        try:
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            
            # Check if user already exists
            cur.execute("SELECT id FROM users WHERE email = ?", (email.lower(),))
            if cur.fetchone():
                con.close()
                return {
                    "success": False,
                    "error": "An account with this email already exists"
                }
            
            # Validate password
            if len(password) < 8:
                con.close()
                return {
                    "success": False,
                    "error": "Password must be at least 8 characters"
                }
            
            # Hash password and create user
            password_hash = self._hash_password(password)
            now = datetime.utcnow().isoformat()
            
            cur.execute("""
                INSERT INTO users (email, password_hash, first_name, last_name, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (email.lower(), password_hash, first_name, last_name, now, now))
            
            user_id = cur.lastrowid
            
            # Create session token
            token = self._generate_token()
            expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
            
            cur.execute("""
                INSERT INTO user_sessions (user_id, token, expires_at, created_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, token, expires_at, now))
            
            con.commit()
            con.close()
            
            log.info(f"User registered: {email}")
            
            return {
                "success": True,
                "user": {
                    "id": str(user_id),
                    "email": email,
                    "firstName": first_name,
                    "lastName": last_name
                },
                "token": token
            }
            
        except sqlite3.IntegrityError:
            return {
                "success": False,
                "error": "An account with this email already exists"
            }
        except Exception as e:
            log.error(f"Registration error: {e}", exc_info=True)
            return {
                "success": False,
                "error": "Registration failed. Please try again."
            }
    
    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate a user and create a session."""
        try:
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            
            # Find user
            cur.execute("""
                SELECT id, email, password_hash, first_name, last_name, is_active
                FROM users
                WHERE email = ?
            """, (email.lower(),))
            
            user_row = cur.fetchone()
            if not user_row:
                con.close()
                return {
                    "success": False,
                    "error": "Invalid email or password"
                }
            
            user_id, db_email, password_hash, first_name, last_name, is_active = user_row
            
            if not is_active:
                con.close()
                return {
                    "success": False,
                    "error": "Account is disabled"
                }
            
            # Verify password
            if not self._verify_password(password, password_hash):
                con.close()
                return {
                    "success": False,
                    "error": "Invalid email or password"
                }
            
            # Create session token
            token = self._generate_token()
            expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
            now = datetime.utcnow().isoformat()
            
            cur.execute("""
                INSERT INTO user_sessions (user_id, token, expires_at, created_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, token, expires_at, now))
            
            con.commit()
            con.close()
            
            log.info(f"User logged in: {email}")
            
            return {
                "success": True,
                "user": {
                    "id": str(user_id),
                    "email": db_email,
                    "firstName": first_name,
                    "lastName": last_name
                },
                "token": token
            }
            
        except Exception as e:
            log.error(f"Login error: {e}", exc_info=True)
            return {
                "success": False,
                "error": "Login failed. Please try again."
            }
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify a session token and return user info."""
        try:
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            
            # Find session
            cur.execute("""
                SELECT s.user_id, s.expires_at, u.email, u.first_name, u.last_name, u.is_active
                FROM user_sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.token = ?
            """, (token,))
            
            session_row = cur.fetchone()
            if not session_row:
                con.close()
                return None
            
            user_id, expires_at_str, email, first_name, last_name, is_active = session_row
            
            # Check if session expired
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.utcnow() > expires_at:
                # Delete expired session
                cur.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
                con.commit()
                con.close()
                return None
            
            # Check if user is active
            if not is_active:
                con.close()
                return None
            
            con.close()
            
            return {
                "id": str(user_id),
                "email": email,
                "firstName": first_name,
                "lastName": last_name
            }
            
        except Exception as e:
            log.error(f"Token verification error: {e}", exc_info=True)
            return None
    
    def logout_user(self, token: str) -> bool:
        """Delete a session token (logout)."""
        try:
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            
            cur.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
            con.commit()
            con.close()
            
            return True
            
        except Exception as e:
            log.error(f"Logout error: {e}", exc_info=True)
            return False
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions from the database."""
        try:
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            
            now = datetime.utcnow().isoformat()
            cur.execute("DELETE FROM user_sessions WHERE expires_at < ?", (now,))
            
            deleted = cur.rowcount
            con.commit()
            con.close()
            
            if deleted > 0:
                log.info(f"Cleaned up {deleted} expired sessions")
            
        except Exception as e:
            log.error(f"Session cleanup error: {e}", exc_info=True)

