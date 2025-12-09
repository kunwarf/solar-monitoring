#!/usr/bin/env python3
"""
API Key Manager for weather providers and other external services.
Handles secure storage and retrieval of API keys from database or environment variables.
"""

import os
import logging
from typing import Dict, Optional
from dataclasses import dataclass
import sqlite3
import hashlib
import base64

log = logging.getLogger(__name__)

@dataclass
class APIKey:
    """API Key data structure."""
    service: str
    key: str
    description: str = ""
    is_active: bool = True

class APIKeyManager:
    """Manages API keys for external services."""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/.solarhub/solarhub.db")
        self._init_database()
    
    def _init_database(self):
        """Initialize the API keys table in the database."""
        try:
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            
            # Create API keys table if it doesn't exist
            cur.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    service TEXT PRIMARY KEY,
                    encrypted_key TEXT NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            con.commit()
            con.close()
            log.info("API keys table initialized successfully")
            
        except Exception as e:
            log.error(f"Failed to initialize API keys table: {e}")
    
    def _encrypt_key(self, key: str) -> str:
        """Simple encryption for API keys (base64 encoding for now)."""
        # In production, use proper encryption like Fernet
        return base64.b64encode(key.encode()).decode()
    
    def _decrypt_key(self, encrypted_key: str) -> str:
        """Decrypt API key."""
        try:
            return base64.b64decode(encrypted_key.encode()).decode()
        except Exception as e:
            log.error(f"Failed to decrypt API key: {e}")
            return ""
    
    def store_api_key(self, service: str, key: str, description: str = "") -> bool:
        """Store an API key in the database."""
        try:
            if not key or not service:
                log.error("Service name and API key are required")
                return False
            
            encrypted_key = self._encrypt_key(key)
            
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            
            # Insert or update API key
            cur.execute("""
                INSERT OR REPLACE INTO api_keys 
                (service, encrypted_key, description, is_active, updated_at)
                VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
            """, (service, encrypted_key, description))
            
            con.commit()
            con.close()
            
            log.info(f"API key stored successfully for service: {service}")
            return True
            
        except Exception as e:
            log.error(f"Failed to store API key for {service}: {e}")
            return False
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Retrieve an API key from database or environment variables."""
        try:
            # First try database
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            
            cur.execute("""
                SELECT encrypted_key FROM api_keys 
                WHERE service = ? AND is_active = 1
            """, (service,))
            
            result = cur.fetchone()
            con.close()
            
            if result:
                decrypted_key = self._decrypt_key(result[0])
                if decrypted_key:
                    log.debug(f"Retrieved API key from database for service: {service}")
                    return decrypted_key
            
            # Fallback to environment variables
            env_key = self._get_env_api_key(service)
            if env_key:
                log.debug(f"Retrieved API key from environment for service: {service}")
                return env_key
            
            log.warning(f"No API key found for service: {service}")
            return None
            
        except Exception as e:
            log.error(f"Failed to retrieve API key for {service}: {e}")
            return None
    
    def _get_env_api_key(self, service: str) -> Optional[str]:
        """Get API key from environment variables."""
        # Common environment variable patterns
        env_vars = [
            f"{service.upper()}_API_KEY",
            f"{service.upper()}_KEY", 
            f"API_KEY_{service.upper()}",
            f"WEATHER_{service.upper()}_KEY"
        ]
        
        for env_var in env_vars:
            key = os.getenv(env_var)
            if key:
                return key
        
        return None
    
    def list_api_keys(self) -> Dict[str, APIKey]:
        """List all stored API keys (without revealing the actual keys)."""
        try:
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            
            cur.execute("""
                SELECT service, description, is_active, created_at, updated_at
                FROM api_keys
                ORDER BY service
            """)
            
            results = cur.fetchall()
            con.close()
            
            api_keys = {}
            for row in results:
                service, description, is_active, created_at, updated_at = row
                api_keys[service] = APIKey(
                    service=service,
                    key="***hidden***",  # Don't expose actual keys
                    description=description,
                    is_active=bool(is_active)
                )
            
            return api_keys
            
        except Exception as e:
            log.error(f"Failed to list API keys: {e}")
            return {}
    
    def delete_api_key(self, service: str) -> bool:
        """Delete an API key from the database."""
        try:
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            
            cur.execute("DELETE FROM api_keys WHERE service = ?", (service,))
            deleted = cur.rowcount > 0
            
            con.commit()
            con.close()
            
            if deleted:
                log.info(f"API key deleted for service: {service}")
            else:
                log.warning(f"No API key found to delete for service: {service}")
            
            return deleted
            
        except Exception as e:
            log.error(f"Failed to delete API key for {service}: {e}")
            return False
    
    def deactivate_api_key(self, service: str) -> bool:
        """Deactivate an API key without deleting it."""
        try:
            con = sqlite3.connect(self.db_path)
            cur = con.cursor()
            
            cur.execute("""
                UPDATE api_keys 
                SET is_active = 0, updated_at = CURRENT_TIMESTAMP
                WHERE service = ?
            """, (service,))
            
            updated = cur.rowcount > 0
            con.commit()
            con.close()
            
            if updated:
                log.info(f"API key deactivated for service: {service}")
            else:
                log.warning(f"No API key found to deactivate for service: {service}")
            
            return updated
            
        except Exception as e:
            log.error(f"Failed to deactivate API key for {service}: {e}")
            return False

# Global instance
_api_key_manager = None

def get_api_key_manager() -> APIKeyManager:
    """Get the global API key manager instance."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager

def get_weather_api_key(provider: str) -> Optional[str]:
    """Get API key for a specific weather provider."""
    manager = get_api_key_manager()
    
    # Map provider names to service names
    service_map = {
        "weatherapi": "weatherapi",
        "openmeteo": "openmeteo", 
        "openweather": "openweathermap",
        "weatherbit": "weatherbit"
    }
    
    service = service_map.get(provider.lower(), provider.lower())
    return manager.get_api_key(service)
