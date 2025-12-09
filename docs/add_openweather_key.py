#!/usr/bin/env python3
"""
Script to add OpenWeatherMap API key to the Linux system.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def add_api_key():
    """Add OpenWeatherMap API key to the system."""
    api_key = "8b3c3b9e82005cd0a0a3e2363cc26086"
    
    try:

        # Method 1: Try using the manage_api_keys.py script
        import subprocess
        result = subprocess.run([
            sys.executable, "manage_api_keys.py", "store", "openweathermap", api_key
        ], capture_output=True, text=True)
        if result.returncode == 0:
            log.info("✅ API key stored successfully using manage_api_keys.py")
            return True
        else:
            log.error(f"❌ Failed to store API key: {result.stderr}")
            
    except Exception as e:
        log.error(f"❌ Error using manage_api_keys.py: {e}")
    
    try:
        # Method 2: Set environment variable
        os.environ["OPENWEATHERMAP_API_KEY"] = api_key
        log.info("✅ API key set as environment variable")
        return True
        
    except Exception as e:
        log.error(f"❌ Error setting environment variable: {e}")
    
    try:
        # Method 3: Direct database access
        from solarhub.api_key_manager import APIKeyManager
        manager = APIKeyManager()
        manager.store_api_key("openweathermap", api_key)
        log.info("✅ API key stored directly in database")
        return True
        
    except Exception as e:
        log.error(f"❌ Error storing in database: {e}")
    
    return False

def verify_api_key():
    """Verify the API key is accessible."""
    try:
        from solarhub.api_key_manager import get_weather_api_key
        key = get_weather_api_key("openweathermap")
        if key:
            log.info(f"✅ API key verified: {key[:8]}...")
            return True
        else:
            log.error("❌ API key not found")
            return False
    except Exception as e:
        log.error(f"❌ Error verifying API key: {e}")
        return False

if __name__ == "__main__":
    print("🔑 OpenWeatherMap API Key Setup")
    print("=" * 40)
    
    print("\n🔄 Adding OpenWeatherMap API key...")
    success = add_api_key()
    
    if success:
        print("\n✅ API key added successfully!")
        
        print("\n🔍 Verifying API key...")
        if verify_api_key():
            print("✅ API key verification successful!")
            print("🔄 Restart the application to use the API key")
        else:
            print("❌ API key verification failed")
    else:
        print("\n❌ Failed to add API key")
        print("\n💡 Manual setup options:")
        print("1. Set environment variable: export OPENWEATHERMAP_API_KEY=8b3c3b9e82005cd0a0a3e2363cc26086")
        print("2. Run: python manage_api_keys.py store openweathermap 8b3c3b9e82005cd0a0a3e2363cc26086")
