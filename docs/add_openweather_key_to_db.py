#!/usr/bin/env python3
"""
Script to add OpenWeatherMap API key directly to the database.
"""

import sqlite3
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def add_api_key_to_database():
    """Add OpenWeatherMap API key to the database."""
    db_path = "/root/.solarhub/solarhub.db"
    api_key = "8b3c3b9e82005cd0a0a3e2363cc26086"
    
    if not os.path.exists(db_path):
        log.error(f"Database not found at: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Add the API key to the database
        cursor.execute("""
            INSERT OR REPLACE INTO configuration (key, value, updated_at, source)
            VALUES ('smart.forecast.openweather_key', ?, CURRENT_TIMESTAMP, 'manual_fix')
        """, (api_key,))
        
        conn.commit()
        log.info("✅ Added OpenWeatherMap API key to database")
        
        # Verify the addition
        cursor.execute("SELECT value FROM configuration WHERE key = 'smart.forecast.openweather_key'")
        result = cursor.fetchone()
        
        if result and result[0] == api_key:
            log.info("✅ Verification successful - API key added to database")
            return True
        else:
            log.error("❌ Verification failed - API key not added properly")
            return False
            
    except Exception as e:
        log.error(f"Error adding API key to database: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def check_database_config():
    """Check what's in the database configuration."""
    db_path = "/root/.solarhub/solarhub.db"
    
    if not os.path.exists(db_path):
        log.error(f"Database not found at: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check all configuration entries
        cursor.execute("SELECT key, value FROM configuration WHERE key LIKE '%openweather%' OR key LIKE '%api%' ORDER BY key")
        results = cursor.fetchall()
        
        log.info(f"API key related configuration entries ({len(results)} total):")
        for key, value in results:
            log.info(f"  {key}: {value[:8] + '...' if len(value) > 8 else value}")
        
        conn.close()
        return True
        
    except Exception as e:
        log.error(f"Error checking database: {e}")
        return False

if __name__ == "__main__":
    print("🔑 OpenWeatherMap API Key Database Fix")
    print("=" * 40)
    
    print("\n📋 Checking current database configuration...")
    check_database_config()
    
    print("\n🔄 Adding OpenWeatherMap API key to database...")
    success = add_api_key_to_database()
    
    if success:
        print("\n✅ API key added successfully!")
        print("🔄 Restart the application to use the API key from database")
    else:
        print("\n❌ Failed to add API key to database")
    
    print("\n📋 Updated database configuration:")
    check_database_config()
