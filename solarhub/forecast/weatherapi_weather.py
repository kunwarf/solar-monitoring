#!/usr/bin/env python3
"""
WeatherAPI.com weather forecasting provider.
Provides enhanced weather data including solar radiation for accurate PV forecasting.
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

class WeatherAPIWeather:
    """WeatherAPI.com weather forecasting provider."""
    
    def __init__(self, lat: float, lon: float, tz: str, api_key: str = None):
        self.lat, self.lon, self.tz = lat, lon, tz
        self.timezone = pytz.timezone(tz)
        
        # Get API key from parameter, database, or environment
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = get_weather_api_key("weatherapi") or "demo"
        
        if self.api_key == "demo":
            log.warning("Using demo API key for WeatherAPI. Get a free key from weatherapi.com")
        
        self.base_url = "http://api.weatherapi.com/v1"
        
        # Cache for expensive API calls
        self._forecast_cache: Dict[str, Dict] = {}
        self._cache_date: Optional[str] = None
        self._factors_cache: Optional[Dict[str, float]] = None
        self._factors_cache_time: Optional[float] = None
        self._cache_ttl_seconds = 45000  # 5 minutes cache TTL
        
        # Unique cache key for this provider instance
        self._cache_key = f"weatherapi_{self.lat}_{self.lon}_{self.tz}_{self.api_key[:8]}"

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
                log.info(f"Using cached WeatherAPI forecast for {today_str}")
                return self._forecast_cache
            
            # WeatherAPI.com forecast endpoint
            url = (f"{self.base_url}/forecast.json?"
                   f"key={self.api_key}&q={self.lat},{self.lon}"
                   f"&days={days}&aqi=no&alerts=no")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = self._process_weather_data(data)
                    else:
                        log.warning(f"WeatherAPI returned status {response.status}")
                        result = self._get_fallback_forecast(days)
            
            # Cache the results
            self._forecast_cache = result
            self._cache_date = today_str
            log.info(f"Generated and cached WeatherAPI forecast for {today_str}")
            
            return result
                        
        except Exception as e:
            log.error(f"WeatherAPI error: {e}")
            return self._get_fallback_forecast(days)
    
    def _process_weather_data(self, data: Dict) -> Dict[str, Dict]:
        """Process raw WeatherAPI data into structured format."""
        try:
            forecast_data = data.get("forecast", {})
            forecast_days = forecast_data.get("forecastday", [])
            
            daily_forecasts = {}
            
            for day_data in forecast_days:
                date_str = day_data.get("date")
                if not date_str:
                    continue
                
                # Process hourly data
                hourly_data = day_data.get("hour", [])
                hours = []
                cloud_cover = []
                temperature = []
                humidity = []
                wind_speed = []
                precipitation = []
                uv_index = []
                solar_radiation = []
                
                for hour_data in hourly_data:
                    time_str = hour_data.get("time", "")
                    if time_str:
                        # Extract hour from time string (format: "2024-01-01 12:00")
                        try:
                            hour = int(time_str.split(" ")[1].split(":")[0])
                            hours.append(hour)
                            
                            # Extract weather parameters
                            cloud_cover.append(hour_data.get("cloud", 0))
                            temperature.append(hour_data.get("temp_c", 25))
                            humidity.append(hour_data.get("humidity", 50))
                            wind_speed.append(hour_data.get("wind_kph", 0) / 3.6)  # Convert to m/s
                            precipitation.append(hour_data.get("precip_mm", 0))
                            uv_index.append(hour_data.get("uv", 0))
                            
                            # Estimate solar radiation from UV index
                            # UV index can be used to estimate solar radiation
                            uv = hour_data.get("uv", 0)
                            if uv > 0:
                                # Rough conversion: UV index * 25 = approximate W/m²
                                estimated_radiation = uv * 25
                                solar_radiation.append(estimated_radiation)
                            else:
                                solar_radiation.append(0)
                                
                        except (ValueError, IndexError):
                            continue
                
                # Calculate daily factors
                daily_factors = self._calculate_daily_factors({
                    "hours": hours,
                    "cloud_cover": cloud_cover,
                    "temperature": temperature,
                    "humidity": humidity,
                    "wind_speed": wind_speed,
                    "precipitation": precipitation,
                    "solar_radiation": solar_radiation
                })
                
                daily_forecasts[date_str] = {
                    "hours": hours,
                    "cloud_cover": cloud_cover,
                    "temperature": temperature,
                    "humidity": humidity,
                    "wind_speed": wind_speed,
                    "precipitation": precipitation,
                    "solar_radiation": solar_radiation,
                    "factors": daily_factors
                }
            
            return daily_forecasts
            
        except Exception as e:
            log.error(f"Error processing WeatherAPI data: {e}")
            return self._get_fallback_forecast(2)
    
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
        solar_radiation = np.array(day_data["solar_radiation"])
        
        # Filter daylight hours (6 AM to 8 PM)
        daylight_mask = (hours >= 6) & (hours <= 20)
        
        if not np.any(daylight_mask):
            return {"irradiance_factor": 0.7, "temperature_factor": 1.0, 
                   "soiling_factor": 1.0, "overall_factor": 0.7}
        
        # 1. Irradiance factor (cloud cover + actual radiation)
        daylight_cloud = cloud_cover[daylight_mask]
        daylight_radiation = solar_radiation[daylight_mask]
        
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
        
        # 4. Overall factor (combination of all factors)
        overall_factor = irradiance_factor * temp_factor * soiling_factor
        overall_factor = max(0.1, min(1.0, overall_factor))  # Clamp to reasonable range
        
        return {
            "irradiance_factor": round(irradiance_factor, 3),
            "temperature_factor": round(temp_factor, 3),
            "soiling_factor": round(soiling_factor, 3),
            "overall_factor": round(overall_factor, 3)
        }
    
    def _get_fallback_forecast(self, days: int) -> Dict[str, Dict]:
        """Get fallback forecast when API fails."""
        log.warning("Using fallback weather forecast")
        
        fallback_forecasts = {}
        today = dt.datetime.now(self.timezone).date()
        
        for i in range(days):
            date = today + dt.timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            # Generate reasonable fallback data
            hours = list(range(24))
            cloud_cover = [20] * 24  # 20% cloud cover
            temperature = [25] * 24  # 25°C
            humidity = [50] * 24  # 50% humidity
            wind_speed = [2.0] * 24  # 2 m/s
            precipitation = [0] * 24  # No precipitation
            solar_radiation = [0] * 24  # No radiation data
            
            fallback_forecasts[date_str] = {
                "hours": hours,
                "cloud_cover": cloud_cover,
                "temperature": temperature,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "precipitation": precipitation,
                "solar_radiation": solar_radiation,
                "factors": {
                    "irradiance_factor": 0.8,
                    "temperature_factor": 1.0,
                    "soiling_factor": 0.95,
                    "overall_factor": 0.76
                }
            }
        
        return fallback_forecasts
    
    async def day_factors(self) -> Dict[str, float]:
        """Get simple day factors for compatibility with existing code."""
        try:
            # Check cache first
            current_time = time.time()
            if (self._factors_cache is not None and 
                self._factors_cache_time is not None and 
                current_time - self._factors_cache_time < self._cache_ttl_seconds):
                log.info("Using cached WeatherAPI day factors")
                return self._factors_cache
            
            # Get today's forecast
            forecast = await self.get_enhanced_forecast(days=1)
            from solarhub.timezone_utils import now_configured
            today_str = now_configured().strftime("%Y-%m-%d")
            
            if today_str in forecast:
                # Calculate day factor based on solar radiation during daylight hours
                solar_radiation = forecast[today_str].get("solar_radiation", [])
                if solar_radiation and len(solar_radiation) == 24:
                    # Only consider daylight hours (6 AM to 6 PM)
                    daylight_radiation = solar_radiation[6:18]  # Hours 6-17
                    
                    # Calculate average radiation during daylight hours
                    avg_daylight_radiation = sum(daylight_radiation) / len(daylight_radiation)
                    
                    # Normalize to clear sky conditions for Lahore, Pakistan
                    # WeatherAPI.com seems to provide lower values, so adjust normalization
                    # For Lahore, clear sky should be around 600-700 W/m² average during daylight
                    clear_sky_reference = 600.0  # Adjusted for WeatherAPI.com data
                    day_factor = min(1.0, avg_daylight_radiation / clear_sky_reference)
                    
                    log.info(f"WeatherAPI day factor calculation: avg daylight radiation={avg_daylight_radiation:.1f} W/m², factor={day_factor:.3f}")
                    
                    result = {
                        "today": day_factor,
                        "tomorrow": day_factor  # Use same for tomorrow
                    }
                else:
                    # Fallback to factors from forecast
                    factors = forecast[today_str]["factors"]
                    result = {
                        "today": factors["overall_factor"],
                        "tomorrow": factors["overall_factor"]
                    }
            else:
                result = {"today": 0.8, "tomorrow": 0.8}
            
            # Cache the result
            self._factors_cache = result
            self._factors_cache_time = current_time
            log.info(f"Generated and cached WeatherAPI day factors: {result}")
            
            return result
                
        except Exception as e:
            log.error(f"Error getting day factors: {e}")
            return {"today": 0.8, "tomorrow": 0.8}
