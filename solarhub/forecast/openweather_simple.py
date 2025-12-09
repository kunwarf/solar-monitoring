#!/usr/bin/env python3
"""
Simple OpenWeatherMap weather forecasting provider using free APIs.
Uses current weather and 5-day forecast APIs to estimate solar conditions.
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

class OpenWeatherSimple:
    """Simple OpenWeatherMap weather forecasting provider using free APIs."""


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
        
        self.current_url = "https://api.openweathermap.org/data/2.5/weather"
        self.forecast_url = "https://api.openweathermap.org/data/2.5/forecast"


        # Cache for expensive API calls
        self._forecast_cache: Dict[str, Dict] = {}
        self._cache_date: Optional[str] = None
        self._factors_cache: Optional[Dict[str, float]] = None
        self._factors_cache_time: Optional[float] = None
        self._cache_ttl_seconds = 45000  # 5 minutes cache TTL
        
        # Unique cache key for this provider instance
        self._cache_key = f"openweather_simple_{self.lat}_{self.lon}_{self.tz}_{self.api_key[:8]}"

    async def get_enhanced_forecast(self, days: int = 2) -> Dict[str, Dict]:
        """
        Get enhanced weather forecast using free OpenWeatherMap APIs.
        """
        try:
            # Check cache first
            today = dt.datetime.now(self.timezone).date()
            today_str = today.strftime("%Y-%m-%d")
            
            if (self._cache_date == today_str and 
                self._forecast_cache and 
                len(self._forecast_cache) >= days):
                log.debug(f"Using cached OpenWeatherMap simple forecast for {today_str} (cache_key: {self._cache_key})")
                return self._forecast_cache
            
            # Get current weather and 5-day forecast
            current_data, forecast_data = await self._fetch_weather_data()
            
            if not current_data or not forecast_data:
                log.error("Failed to fetch weather data from OpenWeatherMap")
                return self._get_fallback_forecast(days)
            
            # Process the data
            result = self._process_weather_data(current_data, forecast_data, days)
            
            # Cache the results
            self._forecast_cache = result
            self._cache_date = today_str
            log.debug(f"Generated and cached OpenWeatherMap simple forecast for {today_str} (cache_key: {self._cache_key})")
            
            return result
                        
        except Exception as e:
            log.error(f"Error fetching OpenWeatherMap simple forecast: {e}")
            return self._get_fallback_forecast(days)
    
    async def _fetch_weather_data(self) -> tuple[Optional[Dict], Optional[Dict]]:
        """Fetch current weather and forecast data."""
        try:
            params = {
                "lat": self.lat,
                "lon": self.lon,
                "appid": self.api_key,
                "units": "metric"
            }
            
            async with aiohttp.ClientSession() as session:
                # Get current weather
                async with session.get(self.current_url, params=params) as response:
                    if response.status == 200:
                        current_data = await response.json()
                        log.info("OpenWeatherMap current weather received successfully")
                    else:
                        log.error(f"OpenWeatherMap current weather API error {response.status}")
                        current_data = None
                
                # Get 5-day forecast
                async with session.get(self.forecast_url, params=params) as response:
                    if response.status == 200:
                        forecast_data = await response.json()
                        log.info("OpenWeatherMap forecast received successfully")
                    else:
                        log.error(f"OpenWeatherMap forecast API error {response.status}")
                        forecast_data = None
                
                return current_data, forecast_data
                
        except Exception as e:
            log.error(f"Error fetching weather data: {e}")
            return None, None
    
    def _process_weather_data(self, current_data: Dict, forecast_data: Dict, days: int) -> Dict[str, Dict]:
        """Process weather data into daily forecasts."""
        daily_forecasts = {}
        
        try:
            # Process today using current weather
            today = dt.datetime.now(self.timezone).date()
            today_str = today.strftime("%Y-%m-%d")
            
            today_forecast = self._create_daily_forecast_from_current(current_data, today_str)
            daily_forecasts[today_str] = today_forecast
            
            # Process next days using forecast data
            forecast_list = forecast_data.get("list", [])
            processed_dates = {today_str}
            
            for forecast_item in forecast_list:
                forecast_time = dt.datetime.fromtimestamp(forecast_item.get("dt", 0), tz=self.timezone)
                forecast_date = forecast_time.date()
                forecast_date_str = forecast_date.strftime("%Y-%m-%d")
                
                if forecast_date_str not in processed_dates and len(daily_forecasts) < days:
                    # Create daily forecast from 3-hourly data
                    day_forecast = self._create_daily_forecast_from_forecast(forecast_list, forecast_date)
                    daily_forecasts[forecast_date_str] = day_forecast
                    processed_dates.add(forecast_date_str)
            
            return daily_forecasts
            
        except Exception as e:
            log.error(f"Error processing weather data: {e}")
            return self._get_fallback_forecast(days)
    
    def _create_daily_forecast_from_current(self, current_data: Dict, date_str: str) -> Dict:
        """Create daily forecast from current weather data."""
        try:
            # Extract current weather data
            main_data = current_data.get("main", {})
            weather_data = current_data.get("weather", [{}])[0]
            clouds_data = current_data.get("clouds", {})
            
            # Estimate solar radiation based on weather conditions
            cloud_cover = clouds_data.get("all", 50)
            weather_main = weather_data.get("main", "Clear")
            
            # Calculate solar radiation based on cloud cover and weather
            base_radiation = self._estimate_solar_radiation(cloud_cover, weather_main)
            
            # Create hourly data (24 hours)
            hourly_temperature = []
            hourly_cloud_cover = []
            hourly_precipitation = []
            hourly_solar_radiation = []
            
            current_temp = main_data.get("temp", 25)
            
            for hour in range(24):
                # Simple hourly variation
                if 6 <= hour <= 18:  # Daylight hours
                    # Temperature variation during day
                    if hour < 12:
                        temp = current_temp + (hour - 6) * 2  # Rising temperature
                    else:
                        temp = current_temp + (18 - hour) * 2  # Falling temperature
                    
                    # Solar radiation variation (peak at noon)
                    if hour < 12:
                        solar_rad = base_radiation * (hour - 6) / 6
                    else:
                        solar_rad = base_radiation * (18 - hour) / 6
                else:  # Night hours
                    temp = current_temp - 5
                    solar_rad = 0
                
                hourly_temperature.append(temp)
                hourly_cloud_cover.append(cloud_cover)
                hourly_precipitation.append(0.0)  # No precipitation data from current weather
                hourly_solar_radiation.append(solar_rad)
            
            # Calculate daily factors
            daily_factors = self._calculate_daily_factors(hourly_solar_radiation, hourly_cloud_cover)
            
            return {
                "temperature": hourly_temperature,
                "cloud_cover": hourly_cloud_cover,
                "precipitation": hourly_precipitation,
                "solar_radiation": hourly_solar_radiation,
                "factors": daily_factors,
                "weather_description": weather_data.get("description", "unknown"),
                "weather_main": weather_main
            }
            
        except Exception as e:
            log.error(f"Error creating daily forecast from current data: {e}")
            return self._get_fallback_daily_data()
    
    def _create_daily_forecast_from_forecast(self, forecast_list: List[Dict], target_date: dt.date) -> Dict:
        """Create daily forecast from 3-hourly forecast data."""
        try:
            # Get all forecast items for the target date
            day_forecasts = []
            for forecast_item in forecast_list:
                forecast_time = dt.datetime.fromtimestamp(forecast_item.get("dt", 0), tz=self.timezone)
                if forecast_time.date() == target_date:
                    day_forecasts.append(forecast_item)
            
            if not day_forecasts:
                return self._get_fallback_daily_data()
            
            # Calculate averages for the day
            total_temp = 0
            total_clouds = 0
            total_precipitation = 0
            weather_descriptions = []
            
            for forecast_item in day_forecasts:
                main_data = forecast_item.get("main", {})
                weather_data = forecast_item.get("weather", [{}])[0]
                clouds_data = forecast_item.get("clouds", {})
                rain_data = forecast_item.get("rain", {})
                
                total_temp += main_data.get("temp", 25)
                total_clouds += clouds_data.get("all", 50)
                total_precipitation += rain_data.get("3h", 0)
                weather_descriptions.append(weather_data.get("description", "unknown"))
            
            avg_temp = total_temp / len(day_forecasts)
            avg_clouds = total_clouds / len(day_forecasts)
            avg_precipitation = total_precipitation / len(day_forecasts)
            main_weather = max(set(weather_descriptions), key=weather_descriptions.count)
            
            # Estimate solar radiation
            base_radiation = self._estimate_solar_radiation(avg_clouds, main_weather)
            
            # Create hourly data (24 hours)
            hourly_temperature = []
            hourly_cloud_cover = []
            hourly_precipitation = []
            hourly_solar_radiation = []
            
            for hour in range(24):
                # Simple hourly variation
                if 6 <= hour <= 18:  # Daylight hours
                    # Temperature variation during day
                    if hour < 12:
                        temp = avg_temp + (hour - 6) * 2
                    else:
                        temp = avg_temp + (18 - hour) * 2
                    
                    # Solar radiation variation (peak at noon)
                    if hour < 12:
                        solar_rad = base_radiation * (hour - 6) / 6
                    else:
                        solar_rad = base_radiation * (18 - hour) / 6
                else:  # Night hours
                    temp = avg_temp - 5
                    solar_rad = 0
                
                hourly_temperature.append(temp)
                hourly_cloud_cover.append(avg_clouds)
                hourly_precipitation.append(avg_precipitation / 8)  # Distribute precipitation
                hourly_solar_radiation.append(solar_rad)
            
            # Calculate daily factors
            daily_factors = self._calculate_daily_factors(hourly_solar_radiation, hourly_cloud_cover)
            
            return {
                "temperature": hourly_temperature,
                "cloud_cover": hourly_cloud_cover,
                "precipitation": hourly_precipitation,
                "solar_radiation": hourly_solar_radiation,
                "factors": daily_factors,
                "weather_description": main_weather,
                "weather_main": main_weather
            }
            
        except Exception as e:
            log.error(f"Error creating daily forecast from forecast data: {e}")
            return self._get_fallback_daily_data()
    
    def _estimate_solar_radiation(self, cloud_cover: float, weather_main: str) -> float:
        """Estimate solar radiation based on cloud cover and weather conditions."""
        # Base clear sky radiation for Lahore (W/m²)
        clear_sky_radiation = 800.0
        
        # Weather condition multipliers
        weather_multipliers = {
            "Clear": 1.0,
            "Clouds": 0.6,
            "Rain": 0.2,
            "Snow": 0.1,
            "Mist": 0.4,
            "Fog": 0.3,
            "Haze": 0.5,
            "Dust": 0.4,
            "Sand": 0.3,
            "Ash": 0.2,
            "Squall": 0.3,
            "Tornado": 0.1
        }
        
        weather_multiplier = weather_multipliers.get(weather_main, 0.7)
        
        # Cloud cover effect (inverse relationship)
        cloud_effect = 1.0 - (cloud_cover / 100.0)
        
        # Calculate estimated radiation
        estimated_radiation = clear_sky_radiation * weather_multiplier * cloud_effect
        
        return max(0, estimated_radiation)
    
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
            clear_sky_reference = 600.0  # For Lahore
            solar_factor = min(1.0, avg_solar_radiation / clear_sky_reference)
            
            # Cloud cover factor (inverse relationship)
            cloud_factor = max(0.1, 1.0 - (avg_cloud_cover / 100.0))
            
            # Overall factor (weighted combination)
            overall_factor = (solar_factor * 0.7 + cloud_factor * 0.3)
            
            log.info(f"OpenWeatherMap simple factors: solar={solar_factor:.3f}, cloud={cloud_factor:.3f}, overall={overall_factor:.3f}")
            
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
            "temperature": [25.0] * 24,
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
                log.debug(f"Using cached OpenWeatherMap simple day factors (cache_key: {self._cache_key})")
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
            log.debug(f"Generated and cached OpenWeatherMap simple day factors: {result} (cache_key: {self._cache_key})")
            
            return result
                
        except Exception as e:
            log.error(f"Error getting OpenWeatherMap simple day factors: {e}")
            return {"today": 0.7, "tomorrow": 0.7}
