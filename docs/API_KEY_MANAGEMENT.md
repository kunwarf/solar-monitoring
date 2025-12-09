# API Key Management System

This document describes the API key management system for weather providers and other external services in the Solar Monitoring application.

## Overview

The API key management system provides secure storage and retrieval of API keys for various weather providers. It supports:

- **Secure storage** in SQLite database with basic encryption
- **Environment variable fallback** for deployment flexibility
- **Multiple weather providers** (WeatherAPI.com, OpenWeatherMap, WeatherBit, etc.)
- **CLI management tools** for easy key management
- **Automatic key retrieval** by weather providers

## Supported Weather Providers

| Provider | Service Name | API Key Required | Free Tier |
|----------|--------------|------------------|-----------|
| WeatherAPI.com | `weatherapi` | ✅ Yes | 1M calls/month |
| OpenWeatherMap | `openweather` | ✅ Yes | 1000 calls/day |
| WeatherBit | `weatherbit` | ✅ Yes | 500 calls/day |
| Open-Meteo | `openmeteo` | ❌ No | Unlimited |

## Quick Start

### 1. Store an API Key

```bash
# Store WeatherAPI.com key
python manage_api_keys.py store weatherapi "your_api_key_here" --description "WeatherAPI.com key"

# Store OpenWeatherMap key
python manage_api_keys.py store openweather "your_openweather_key" --description "OpenWeatherMap key"
```

### 2. List Stored Keys

```bash
python manage_api_keys.py list
```

### 3. Interactive Setup

```bash
python manage_api_keys.py setup
```

### 4. Configure in config.yaml

```yaml
smart:
  forecast:
    provider: weatherapi  # Use WeatherAPI.com
    # API keys can be stored in config file (optional)
    weatherapi_key: "your_key_here"
    # Or use database storage (recommended)
```

## Configuration Methods

### Method 1: Database Storage (Recommended)

Store API keys securely in the database:

```bash
python manage_api_keys.py store weatherapi "your_key_here"
```

### Method 2: Environment Variables

Set environment variables for deployment:

```bash
export WEATHERAPI_API_KEY="your_key_here"
export OPENWEATHER_API_KEY="your_key_here"
```

### Method 3: Config File

Add keys directly to `config.yaml`:

```yaml
smart:
  forecast:
    weatherapi_key: "your_key_here"
    openweather_key: "your_key_here"
```

## CLI Commands

### Store API Key
```bash
python manage_api_keys.py store <service> <key> [--description "description"]
```

### List API Keys
```bash
python manage_api_keys.py list
```

### Get API Key
```bash
python manage_api_keys.py get <service>
```

### Delete API Key
```bash
python manage_api_keys.py delete <service>
```

### Deactivate API Key
```bash
python manage_api_keys.py deactivate <service>
```

### Interactive Setup
```bash
python manage_api_keys.py setup
```

## Programmatic Usage

### Using the API Key Manager

```python
from solarhub.api_key_manager import get_api_key_manager, get_weather_api_key

# Get the manager instance
manager = get_api_key_manager()

# Store an API key
manager.store_api_key("weatherapi", "your_key_here", "Description")

# Retrieve an API key
key = manager.get_api_key("weatherapi")

# Get weather provider key
weather_key = get_weather_api_key("weatherapi")
```

### Using in Weather Providers

Weather providers automatically retrieve API keys:

```python
from solarhub.forecast.weatherapi_weather import WeatherAPIWeather

# API key will be retrieved automatically from database or environment
weather = WeatherAPIWeather(lat=31.5497, lon=74.3436, tz="Asia/Karachi")
```

## Security Features

### Encryption
- API keys are encrypted using base64 encoding (basic security)
- For production, consider implementing stronger encryption (Fernet, AES)

### Access Control
- Keys are stored in SQLite database with proper access controls
- Environment variables provide deployment flexibility
- CLI tools require appropriate file system permissions

### Key Rotation
- Keys can be easily updated using the CLI
- Old keys can be deactivated without deletion
- Support for multiple keys per service (future enhancement)

## Database Schema

```sql
CREATE TABLE api_keys (
    service TEXT PRIMARY KEY,
    encrypted_key TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Environment Variables

The system checks for API keys in the following environment variables:

| Service | Environment Variables |
|---------|----------------------|
| WeatherAPI | `WEATHERAPI_API_KEY`, `WEATHERAPI_KEY`, `API_KEY_WEATHERAPI` |
| OpenWeather | `OPENWEATHER_API_KEY`, `OPENWEATHER_KEY`, `API_KEY_OPENWEATHER` |
| WeatherBit | `WEATHERBIT_API_KEY`, `WEATHERBIT_KEY`, `API_KEY_WEATHERBIT` |

## Troubleshooting

### No API Key Found
```
❌ No API key found for service: weatherapi
```

**Solutions:**
1. Store the key: `python manage_api_keys.py store weatherapi "your_key"`
2. Set environment variable: `export WEATHERAPI_API_KEY="your_key"`
3. Add to config.yaml: `weatherapi_key: "your_key"`

### Invalid API Key
```
❌ API request failed: 401 Unauthorized
```

**Solutions:**
1. Verify the key is correct
2. Check if the key has expired
3. Ensure the service account has sufficient quota

### Database Issues
```
❌ Failed to initialize API keys table
```

**Solutions:**
1. Check database file permissions
2. Ensure SQLite is available
3. Verify database path is writable

## Testing

Run the test suite to verify API key management:

```bash
python test_api_key_manager.py
```

## Future Enhancements

- [ ] Stronger encryption (Fernet/AES)
- [ ] Key rotation support
- [ ] Multiple keys per service
- [ ] API key validation
- [ ] Usage tracking and quotas
- [ ] Web interface for key management
- [ ] Integration with secret management systems (Vault, etc.)

## Contributing

When adding new weather providers:

1. Add the provider to the service mapping in `api_key_manager.py`
2. Update the provider class to use `get_weather_api_key()`
3. Add environment variable patterns
4. Update this documentation
5. Add tests for the new provider
