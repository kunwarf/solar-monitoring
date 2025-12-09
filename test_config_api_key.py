#!/usr/bin/env python3
"""
Test script to verify that the OpenWeatherMap API key is being read correctly from config.yaml
"""

import yaml
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def test_config_api_key():
    """Test reading API key from config.yaml"""
    try:
        # Read config file
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Extract OpenWeatherMap API key
        openweather_key = config.get('smart', {}).get('forecast', {}).get('openweather_key')
        
        if openweather_key:
            log.info(f"✅ OpenWeatherMap API key found in config.yaml: {openweather_key[:8]}...")
            return openweather_key
        else:
            log.error("❌ OpenWeatherMap API key not found in config.yaml")
            return None
            
    except Exception as e:
        log.error(f"❌ Error reading config.yaml: {e}")
        return None

def test_weather_provider_initialization():
    """Test OpenWeatherMap provider initialization with config API key"""
    try:
        from solarhub.config_manager import ConfigurationManager
        from solarhub.logging.logger import DataLogger
        from solarhub.forecast.openweather_simple import OpenWeatherSimple
        
        # Load config using ConfigurationManager (same as main app)
        db_logger = DataLogger()
        config_manager = ConfigurationManager('config.yaml', db_logger)
        cfg = config_manager.load_config()
        
        # Get API key from config
        api_key = cfg.smart.forecast.openweather_key
        
        if api_key:
            log.info(f"✅ API key loaded from config: {api_key[:8]}...")
            
            # Initialize OpenWeatherMap provider
            weather = OpenWeatherSimple(
                lat=cfg.smart.forecast.lat,
                lon=cfg.smart.forecast.lon,
                tz=cfg.smart.forecast.tz,
                api_key=api_key
            )
            
            log.info(f"✅ OpenWeatherMap provider initialized successfully")
            log.info(f"   API key: {weather.api_key[:8]}...")
            log.info(f"   Location: {weather.lat}, {weather.lon}")
            log.info(f"   Timezone: {weather.tz}")
            
            return True
        else:
            log.error("❌ No API key found in config")
            return False
            
    except Exception as e:
        log.error(f"❌ Error testing weather provider: {e}")
        return False

if __name__ == "__main__":
    print("🔑 OpenWeatherMap API Key Configuration Test")
    print("=" * 50)
    
    print("\n📋 Testing config.yaml API key reading...")
    api_key = test_config_api_key()
    
    if api_key:
        print("\n🧪 Testing weather provider initialization...")
        success = test_weather_provider_initialization()
        
        if success:
            print("\n✅ All tests passed! OpenWeatherMap API key is properly configured.")
            print("🔄 Restart your application to use the API key from config.yaml")
        else:
            print("\n❌ Weather provider initialization failed")
    else:
        print("\n❌ API key not found in config.yaml")
        print("💡 Make sure the config.yaml file contains:")
        print("   smart:")
        print("     forecast:")
        print("       openweather_key: \"your_api_key_here\"")
