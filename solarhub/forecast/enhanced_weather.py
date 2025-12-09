#!/usr/bin/env python3
"""
Enhanced weather forecasting for solar PV generation.
Uses multiple weather parameters for more accurate predictions.
"""

from typing import Dict, List, Optional
import pytz
import datetime as dt
import aiohttp
import logging
import pandas as pd
import numpy as np
import time

log = logging.getLogger(__name__)
class EnhancedWeather:
    """Enhanced weather forecasting with multiple parameters."""


    def __init__(self, lat: float, lon: float, tz: str):
        self.lat, self.lon, self.tz = lat, lon, tz
        self.timezone = pytz.timezone(tz)
        
        # Cache for expensive API calls
        self._forecast_cache: Dict[str, Dict] = {}
        self._cache_date: Optional[str] = None
        self._factors_cache: Optional[Dict[str, float]] = None
        self._factors_cache_time: Optional[float] = None
        self._cache_ttl_seconds = 45000  # 5 minutes cache TTL
        
        # Unique cache key for this provider instance
        self._cache_key = f"enhanced_weather_{self.lat}_{self.lon}_{self.tz}"
    
    async def get_enhanced_forecast(self, days: int = 2) -> Dict[str, Dict]:
        """
        Get enhanced weather forecast with multiple parameters.
        
        Args:
            days: Number of forecast days (1-7)
            
        Returns:
            Dictionary with hourly weather data for each day
        """
        try:
            # Check cache first
            today = dt.datetime.now(self.timezone).date()
            today_str = today.strftime("%Y-%m-%d")
            
            # If we have cached data for today and it's recent, use it
            if (self._cache_date == today_str and 
                self._forecast_cache and 
                len(self._forecast_cache) >= days):
                log.info(f"Using cached enhanced weather forecast for {today_str}")
                return self._forecast_cache
            
            # OpenMeteo API with multiple parameters
            url = (f"https://api.open-meteo.com/v1/forecast?"
                   f"latitude={self.lat}&longitude={self.lon}"
                   f"&hourly=temperature_2m,relative_humidity_2m,cloud_cover,"
                   f"wind_speed_10m,precipitation,shortwave_radiation"
                   f"&timezone={self.tz}&forecast_days={days}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = self._process_weather_data(data)
                    else:
                        log.warning(f"Weather API returned status {response.status}")
                        result = self._get_fallback_forecast(days)
            
            # Cache the results
            self._forecast_cache = result
            self._cache_date = today_str
            log.info(f"Generated and cached enhanced weather forecast for {today_str}")
            
            return result
                        
        except Exception as e:
            log.error(f"Weather API error: {e}")
            return self._get_fallback_forecast(days)
    
    def _process_weather_data(self, data: Dict) -> Dict[str, Dict]:
        """Process raw weather API data into structured format."""
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        
        # Extract hourly data
        weather_data = {
            "time": times,
            "temperature": hourly.get("temperature_2m", []),
            "humidity": hourly.get("relative_humidity_2m", []),
            "cloud_cover": hourly.get("cloud_cover", []),
            "wind_speed": hourly.get("wind_speed_10m", []),
            "precipitation": hourly.get("precipitation", []),
            "shortwave_radiation": hourly.get("shortwave_radiation", [])
        }
        
        # Group by day
        daily_forecasts = {}
        current_date = None
        day_data = {"hours": [], "temperature": [], "humidity": [], 
                   "cloud_cover": [], "wind_speed": [], "precipitation": [],
                   "shortwave_radiation": []}
        
        for i, time_str in enumerate(times):
            dt_obj = dt.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            local_dt = dt_obj.astimezone(self.timezone)
            date_str = local_dt.date().isoformat()
            
            if current_date != date_str:
                if current_date is not None:
                    daily_forecasts[current_date] = self._calculate_daily_factors(day_data)
                current_date = date_str
                day_data = {"hours": [], "temperature": [], "humidity": [], 
                           "cloud_cover": [], "wind_speed": [], "precipitation": [],
                           "shortwave_radiation": []}
            
            # Store hourly data
            day_data["hours"].append(local_dt.hour)
            day_data["temperature"].append(weather_data["temperature"][i])
            day_data["humidity"].append(weather_data["humidity"][i])
            day_data["cloud_cover"].append(weather_data["cloud_cover"][i])
            day_data["wind_speed"].append(weather_data["wind_speed"][i])
            day_data["precipitation"].append(weather_data["precipitation"][i])
            day_data["shortwave_radiation"].append(weather_data["shortwave_radiation"][i])
        
        # Process last day
        if current_date is not None:
            daily_forecasts[current_date] = self._calculate_daily_factors(day_data)
        
        return daily_forecasts
    
    def _calculate_daily_factors(self, day_data: Dict) -> Dict[str, float]:
        """Calculate daily weather factors for PV generation."""
        if not day_data["hours"]:
            return {"irradiance_factor": 0.7, "temperature_factor": 1.0, 
                   "soiling_factor": 1.0, "overall_factor": 0.7}
        
        # Convert to numpy arrays for easier calculation
        hours = np.array(day_data["hours"])
        cloud_cover = np.array(day_data["cloud_cover"])
        temperature = np.array(day_data["temperature"])
        humidity = np.array(day_data["humidity"])
        wind_speed = np.array(day_data["wind_speed"])
        precipitation = np.array(day_data["precipitation"])
        shortwave_radiation = np.array(day_data["shortwave_radiation"])
        
        # Filter daylight hours (6 AM to 8 PM)
        daylight_mask = (hours >= 6) & (hours <= 20)
        
        if not np.any(daylight_mask):
            return {"irradiance_factor": 0.7, "temperature_factor": 1.0, 
                   "soiling_factor": 1.0, "overall_factor": 0.7}
        
        # 1. Irradiance factor (cloud cover + actual radiation)
        daylight_cloud = cloud_cover[daylight_mask]
        daylight_radiation = shortwave_radiation[daylight_mask]
        
        # Use actual radiation if available, otherwise estimate from cloud cover
        if np.any(daylight_radiation > 0):
            # Normalize radiation to 0-1 scale (assuming max ~1000 W/m²)
            max_radiation = 1000.0
            irradiance_factor = np.mean(daylight_radiation) / max_radiation
        else:
            # Fallback to cloud cover estimation
            avg_cloud = np.mean(daylight_cloud)
            irradiance_factor = max(0.1, 1.0 - (avg_cloud / 100.0))
        
        # 2. Temperature factor (panel efficiency decreases with high temperature)
        daylight_temp = temperature[daylight_mask]
        avg_temp = np.mean(daylight_temp)
        
        # Standard temperature coefficient: -0.4% per °C above 25°C
        temp_coefficient = -0.004
        temp_factor = 1.0 + (temp_coefficient * (avg_temp - 25.0))
        temp_factor = max(0.7, min(1.1, temp_factor))  # Clamp to reasonable range
        
        # 3. Soiling factor (precipitation cleans panels)
        total_precip = np.sum(precipitation)
        if total_precip > 5.0:  # Significant rain (>5mm)
            soiling_factor = 1.0  # Clean panels
        elif total_precip > 1.0:  # Light rain
            soiling_factor = 0.98  # Slightly cleaner
        else:
            soiling_factor = 0.95  # Some soiling accumulation
        
        # 4. Wind factor (cooling effect)
        daylight_wind = wind_speed[daylight_mask]
        avg_wind = np.mean(daylight_wind)
        
        # Wind cooling: +0.1% efficiency per m/s wind speed
        wind_factor = 1.0 + (0.001 * avg_wind)
        wind_factor = max(0.95, min(1.05, wind_factor))  # Clamp to reasonable range
        
        # 5. Combined overall factor
        overall_factor = irradiance_factor * temp_factor * soiling_factor * wind_factor
        overall_factor = max(0.1, min(1.2, overall_factor))  # Clamp to reasonable range
        
        return {
            "irradiance_factor": round(irradiance_factor, 3),
            "temperature_factor": round(temp_factor, 3),
            "soiling_factor": round(soiling_factor, 3),
            "wind_factor": round(wind_factor, 3),
            "overall_factor": round(overall_factor, 3),
            "avg_temperature": round(avg_temp, 1),
            "avg_cloud_cover": round(np.mean(daylight_cloud), 1),
            "total_precipitation": round(total_precip, 1),
            "avg_wind_speed": round(avg_wind, 1)
        }
    
    def _get_fallback_forecast(self, days: int) -> Dict[str, Dict]:
        """Fallback forecast when API is unavailable."""
        today = dt.date.today()
        forecast = {}
        
        for i in range(days):
            date = today + dt.timedelta(days=i)
            date_str = date.isoformat()
            
            # Simple fallback with seasonal variation
            day_of_year = date.timetuple().tm_yday
            
            # Seasonal irradiance variation (higher in summer)
            seasonal_factor = 0.5 + 0.4 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
            
            forecast[date_str] = {
                "irradiance_factor": round(seasonal_factor, 3),
                "temperature_factor": 1.0,
                "soiling_factor": 0.95,
                "wind_factor": 1.0,
                "overall_factor": round(seasonal_factor * 0.95, 3),
                "avg_temperature": 25.0,
                "avg_cloud_cover": 50.0,
                "total_precipitation": 0.0,
                "avg_wind_speed": 3.0
            }
        
        return forecast
    
    async def day_factors(self) -> Dict[str, float]:
        """Compatibility method for existing code."""
        # Check cache first
        current_time = time.time()
        if (self._factors_cache is not None and 
            self._factors_cache_time is not None and 
            current_time - self._factors_cache_time < self._cache_ttl_seconds):
            log.info("Using cached enhanced weather day factors")
            return self._factors_cache
        
        forecast = await self.get_enhanced_forecast(days=2)
        
        # Get today and tomorrow
        today = dt.date.today().isoformat()
        tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
        
        today_factor = forecast.get(today, {}).get("overall_factor", 0.7)
        tomorrow_factor = forecast.get(tomorrow, {}).get("overall_factor", 0.7)
        
        result = {
            "today": today_factor,
            "tomorrow": tomorrow_factor
        }
        
        # Cache the result
        self._factors_cache = result
        self._factors_cache_time = current_time
        log.info(f"Generated and cached enhanced weather day factors: {result}")
        
        return result

class NaiveWeather:
    """Simple fallback weather provider."""
    
    async def day_factors(self) -> Dict[str, float]:
        return {"today": 0.7, "tomorrow": 0.7}
    
    async def get_enhanced_forecast(self, days: int = 2) -> Dict[str, Dict]:
        """Fallback enhanced forecast."""
        today = dt.date.today()
        forecast = {}
        
        for i in range(days):
            date = today + dt.timedelta(days=i)
            date_str = date.isoformat()
            
            forecast[date_str] = {
                "irradiance_factor": 0.7,
                "temperature_factor": 1.0,
                "soiling_factor": 0.95,
                "wind_factor": 1.0,
                "overall_factor": 0.7,
                "avg_temperature": 25.0,
                "avg_cloud_cover": 50.0,
                "total_precipitation": 0.0,
                "avg_wind_speed": 3.0
            }
        
        return forecast

