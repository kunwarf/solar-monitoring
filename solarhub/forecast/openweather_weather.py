#!/usr/bin/env python3
"""
OpenWeatherMap weather forecasting provider with solar irradiance data.
Uses the One Call API to get detailed weather and solar radiation information.
"""

from typing import Dict, List, Optional
import pytz
import datetime as dt
import aiohttp
import logging
import pandas as pd
import numpy as np
import time
from solarhub.api_key_manager import get_weather_api_key

log = logging.getLogger(__name__)

class OpenWeatherWeather:
    """OpenWeatherMap weather forecasting provider with solar irradiance."""
    def __init__(self, lat: float, lon: float, tz: str, api_key: str = None):
        self.lat, self.lon, self.tz = lat, lon, tz
        self.timezone = pytz.timezone(tz)

        # Get API key from parameter, database, or environment
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = get_weather_api_key("openweathermap") or "demo"
        
        if self.api_key == "demo":
            log.warning("Using demo API key for OpenWeatherMap. Get a free key from openweathermap.org")
        self.base_url = "https://api.openweathermap.org/data/2.5/onecall"
        
        # Cache for expensive API calls
        self._forecast_cache: Dict[str, Dict] = {}
        self._cache_date: Optional[str] = None
        self._factors_cache: Optional[Dict[str, float]] = None
        self._factors_cache_time: Optional[float] = None
        self._cache_ttl_seconds = 45000  # 5 minutes cache TTL
        
        # Unique cache key for this provider instance
        self._cache_key = f"openweather_{self.lat}_{self.lon}_{self.tz}_{self.api_key[:8]}"

    async def get_enhanced_forecast(self, days: int = 2) -> Dict[str, Dict]:
        """
        Get enhanced weather forecast with solar irradiance data.
        """
        try:
            # Check cache first
            today = dt.datetime.now(self.timezone).date()
            today_str = today.strftime("%Y-%m-%d")
            
            if (self._cache_date == today_str and 
                self._forecast_cache and 
                len(self._forecast_cache) >= days):
                log.info(f"Using cached OpenWeatherMap forecast for {today_str} (cache_key: {self._cache_key})")
                return self._forecast_cache
            
            # Build API request URL
            url = f"{self.base_url}"
            params = {
                "lat": self.lat,
                "lon": self.lon,
                "appid": self.api_key,
                "units": "metric",
                "exclude": "minutely,alerts"  # We don't need minutely data or alerts
            }
            
            log.info(f"Fetching OpenWeatherMap forecast for {self.lat}, {self.lon}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        log.info("OpenWeatherMap API response received successfully")
                        
                        # Process the data
                        result = self._process_openweather_data(data, days)
                        
                        # Cache the results
                        self._forecast_cache = result
                        self._cache_date = today_str
                        log.info(f"Generated and cached OpenWeatherMap forecast for {today_str} (cache_key: {self._cache_key})")
                        
                        return result
                    else:
                        error_text = await response.text()
                        log.error(f"OpenWeatherMap API error {response.status}: {error_text}")
                        return self._get_fallback_forecast(days)
                        
        except Exception as e:
            log.error(f"Error fetching OpenWeatherMap forecast: {e}")
            return self._get_fallback_forecast(days)
    
    def _process_openweather_data(self, data: Dict, days: int) -> Dict[str, Dict]:
        """Process OpenWeatherMap API response data."""
        daily_forecasts = {}
        
        try:
            # Get current day data
            current = data.get("current", {})
            current_time = dt.datetime.fromtimestamp(current.get("dt", 0), tz=self.timezone)
            today_str = current_time.strftime("%Y-%m-%d")
            
            # Process current day (today)
            today_data = self._process_daily_data(current, data.get("hourly", []), today_str)
            daily_forecasts[today_str] = today_data
            
            # Process next days
            daily_data = data.get("daily", [])
            for i in range(1, min(days, len(daily_data) + 1)):
                day_data = daily_data[i - 1]
                day_time = dt.datetime.fromtimestamp(day_data.get("dt", 0), tz=self.timezone)
                day_str = day_time.strftime("%Y-%m-%d")
                
                # Get hourly data for this day
                day_hourly = self._get_hourly_for_day(data.get("hourly", []), day_time)
                
                processed_day = self._process_daily_data(day_data, day_hourly, day_str)
                daily_forecasts[day_str] = processed_day
            
            return daily_forecasts
            
        except Exception as e:
            log.error(f"Error processing OpenWeatherMap data: {e}")
            return self._get_fallback_forecast(days)
    
    def _process_daily_data(self, daily_data: Dict, hourly_data: List[Dict], date_str: str) -> Dict:
        """Process daily weather data."""
        try:
            # Extract basic weather data
            temp_data = daily_data.get("temp", {})
            weather_data = daily_data.get("weather", [{}])[0]
            
            # Get hourly solar radiation data
            hourly_solar_radiation = []
            hourly_temperature = []
            hourly_cloud_cover = []
            hourly_precipitation = []
            
            for hour_data in hourly_data[:24]:  # First 24 hours
                # Solar radiation (direct + diffuse)
                solar_radiation = hour_data.get("solar_radiation", 0)
                if solar_radiation == 0:
                    # Fallback: estimate from UV index if available
                    uv_index = hour_data.get("uvi", 0)
                    solar_radiation = uv_index * 25  # Rough conversion: UV index * 25 W/m²
                
                hourly_solar_radiation.append(solar_radiation)
                hourly_temperature.append(hour_data.get("temp", 20))
                hourly_cloud_cover.append(hour_data.get("clouds", 0))
                hourly_precipitation.append(hour_data.get("rain", {}).get("1h", 0))
            
            # Calculate daily factors
            daily_factors = self._calculate_daily_factors(hourly_solar_radiation, hourly_cloud_cover)
            
            return {
                "temperature": hourly_temperature,
                "cloud_cover": hourly_cloud_cover,
                "precipitation": hourly_precipitation,
                "solar_radiation": hourly_solar_radiation,
                "factors": daily_factors,
                "weather_description": weather_data.get("description", "unknown"),
                "weather_main": weather_data.get("main", "unknown")
            }
            
        except Exception as e:
            log.error(f"Error processing daily data for {date_str}: {e}")
            return self._get_fallback_daily_data()
    
    def _get_hourly_for_day(self, hourly_data: List[Dict], target_day: dt.datetime) -> List[Dict]:
        """Get hourly data for a specific day."""
        target_date = target_day.date()
        day_hourly = []
        
        for hour_data in hourly_data:
            hour_time = dt.datetime.fromtimestamp(hour_data.get("dt", 0), tz=self.timezone)
            if hour_time.date() == target_date:
                day_hourly.append(hour_data)
        
        return day_hourly
    
    def _calculate_daily_factors(self, solar_radiation: List[float], cloud_cover: List[float]) -> Dict[str, float]:
        """Calculate daily weather factors from hourly data."""
        try:
            if not solar_radiation or len(solar_radiation) == 0:
                return {"overall_factor": 0.7}
            
            # Calculate average solar radiation during daylight hours (6 AM to 6 PM)
            daylight_hours = solar_radiation[6:18] if len(solar_radiation) >= 18 else solar_radiation
            avg_solar_radiation = sum(daylight_hours) / len(daylight_hours) if daylight_hours else 0
            
            # Calculate average cloud cover during daylight hours
            daylight_clouds = cloud_cover[6:18] if len(cloud_cover) >= 18 else cloud_cover
            avg_cloud_cover = sum(daylight_clouds) / len(daylight_clouds) if daylight_clouds else 50
            
            # Calculate factors
            # Solar radiation factor (normalize to clear sky conditions)
            # For Lahore, clear sky should be around 600-700 W/m² average during daylight
            clear_sky_reference = 650.0
            solar_factor = min(1.0, avg_solar_radiation / clear_sky_reference)
            
            # Cloud cover factor (inverse relationship)
            cloud_factor = max(0.1, 1.0 - (avg_cloud_cover / 100.0))
            
            # Overall factor (weighted combination)
            overall_factor = (solar_factor * 0.7 + cloud_factor * 0.3)
            
            log.info(f"OpenWeatherMap factors: solar={solar_factor:.3f}, cloud={cloud_factor:.3f}, overall={overall_factor:.3f}")
            
            return {
                "solar_factor": solar_factor,
                "cloud_factor": cloud_factor,
                "overall_factor": overall_factor
            }
            
        except Exception as e:
            log.error(f"Error calculating daily factors: {e}")
            return {"overall_factor": 0.7}
    
    def _get_fallback_daily_data(self) -> Dict:
        """Get fallback daily data when API fails."""
        return {
            "temperature": [20.0] * 24,
            "cloud_cover": [50] * 24,
            "precipitation": [0.0] * 24,
            "solar_radiation": [0.0] * 24,
            "factors": {"overall_factor": 0.7},
            "weather_description": "unknown",
            "weather_main": "unknown"
        }
    
    def _get_fallback_forecast(self, days: int) -> Dict[str, Dict]:
        """Get fallback forecast when API fails."""
        fallback_forecasts = {}
        today = dt.datetime.now(self.timezone).date()
        
        for i in range(days):
            date = today + dt.timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            fallback_forecasts[date_str] = self._get_fallback_daily_data()
        
        return fallback_forecasts
    
    async def day_factors(self) -> Dict[str, float]:
        """Get simple day factors for compatibility with existing code."""
        try:
            # Check cache first
            current_time = time.time()
            if (self._factors_cache is not None and 
                self._factors_cache_time is not None and 
                current_time - self._factors_cache_time < self._cache_ttl_seconds):
                log.info(f"Using cached OpenWeatherMap day factors (cache_key: {self._cache_key})")
                return self._factors_cache
            
            # Get today's forecast
            forecast = await self.get_enhanced_forecast(days=1)
            from solarhub.timezone_utils import now_configured
            today_str = now_configured().strftime("%Y-%m-%d")
            
            if today_str in forecast:
                factors = forecast[today_str]["factors"]
                result = {
                    "today": factors["overall_factor"],
                    "tomorrow": factors["overall_factor"]  # Use same for tomorrow
                }
            else:
                result = {"today": 0.7, "tomorrow": 0.7}
            
            # Cache the result
            self._factors_cache = result
            self._factors_cache_time = current_time
            log.info(f"Generated and cached OpenWeatherMap day factors: {result} (cache_key: {self._cache_key})")
            
            return result
                
        except Exception as e:
            log.error(f"Error getting OpenWeatherMap day factors: {e}")
            return {"today": 0.7, "tomorrow": 0.7}
