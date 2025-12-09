#!/usr/bin/env python3
"""
Simple weather provider that uses basic solar calculations without external API.
Good for testing and when no internet connection is available.
"""

from typing import Dict, List, Optional
import pytz
import datetime as dt
import logging
import pandas as pd
import numpy as np
import time

log = logging.getLogger(__name__)

class SimpleWeather:
    """Simple weather provider using basic solar calculations."""
    def __init__(self, lat: float, lon: float, tz: str):
        self.lat, self.lon, self.tz = lat, lon, tz
        self.timezone = pytz.timezone(tz)
        # Cache for expensive calculations
        self._forecast_cache: Dict[str, Dict] = {}
        self._cache_date: Optional[str] = None
        self._factors_cache: Optional[Dict[str, float]] = None
        self._factors_cache_time: Optional[float] = None
        self._cache_ttl_seconds = 45000  # 5 minutes cache TTL
        # Unique cache key for this provider instance
        self._cache_key = f"simple_weather_{self.lat}_{self.lon}_{self.tz}"
    
    async def get_enhanced_forecast(self, days: int = 2) -> Dict[str, Dict]:
        """
        Get enhanced weather forecast using basic solar calculations.
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
                log.info(f"Using cached simple weather forecast for {today_str} (cache_key: {self._cache_key})")
                return self._forecast_cache
            
            daily_forecasts = {}
            
            for i in range(days):
                date = today + dt.timedelta(days=i)
                date_str = date.strftime("%Y-%m-%d")
                
                # Generate weather data based on solar calculations
                hours = list(range(24))
                cloud_cover = []
                temperature = []
                humidity = []
                wind_speed = []
                precipitation = []
                solar_radiation = []
                
                for hour in hours:
                    # Basic solar radiation calculation
                    radiation = self._calculate_solar_radiation(date, hour)
                    solar_radiation.append(radiation)
                    
                    # Estimate cloud cover based on season and time
                    cloud = self._estimate_cloud_cover(date, hour, radiation)
                    cloud_cover.append(cloud)
                    
                    # Estimate temperature based on time of day and season
                    temp = self._estimate_temperature(date, hour)
                    temperature.append(temp)
                    
                    # Basic humidity estimation
                    humidity.append(50 + (cloud * 0.3))  # Higher humidity with more clouds
                    
                    # Basic wind speed estimation
                    wind_speed.append(2.0 + (cloud * 0.1))  # Slightly higher wind with clouds
                    
                    # No precipitation for simplicity
                    precipitation.append(0)
                
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
            
            # Cache the results
            self._forecast_cache = daily_forecasts
            self._cache_date = today_str
            log.info(f"Generated and cached simple weather forecast for {today_str} (cache_key: {self._cache_key})")
            
            return daily_forecasts
            
        except Exception as e:
            log.error(f"Error generating simple weather forecast: {e}")
            return self._get_fallback_forecast(days)
    
    def _calculate_solar_radiation(self, date: dt.date, hour: int) -> float:
        """Calculate basic solar radiation for given date and hour."""
        try:
            # Create datetime for the specific hour
            dt_obj = dt.datetime.combine(date, dt.time(hour))
            dt_obj = self.timezone.localize(dt_obj)
            
            # Convert to pandas timestamp for pvlib compatibility
            ts = pd.Timestamp(dt_obj)
            
            # Basic solar position calculation
            import pvlib
            location = pvlib.location.Location(self.lat, self.lon, tz=self.tz)
            solpos = location.get_solarposition(ts)
            
            # Calculate clear sky irradiance
            cs = location.get_clearsky(ts, model='ineichen')
            
            # Use GHI (Global Horizontal Irradiance) as base
            ghi = cs['ghi']
            
            # Apply seasonal and time-of-day factors
            doy = ts.dayofyear
            
            # Seasonal factor (higher in summer, lower in winter)
            seasonal_factor = 0.5 + 0.5 * np.cos(2 * np.pi * (doy - 172) / 365)
            
            # Time-of-day factor (higher at noon, lower at sunrise/sunset)
            if 6 <= hour <= 18:  # Daylight hours
                time_factor = np.sin(np.pi * (hour - 6) / 12)
            else:
                time_factor = 0
            
            # Calculate final radiation
            radiation = ghi * seasonal_factor * time_factor
            
            return max(0, radiation)
            
        except Exception as e:
            log.debug(f"Error calculating solar radiation: {e}")
            return 0
    
    def _estimate_cloud_cover(self, date: dt.date, hour: int, radiation: float) -> float:
        """Estimate cloud cover based on date, time, and radiation."""
        # Base cloud cover
        base_cloud = 30  # 30% average cloud cover
        
        # Seasonal variation (more clouds in monsoon season)
        doy = date.timetuple().tm_yday
        if 150 <= doy <= 250:  # Monsoon season (roughly June-September)
            base_cloud += 20
        
        # Time-of-day variation (more clouds in afternoon)
        if 12 <= hour <= 16:
            base_cloud += 10
        
        # Radiation-based adjustment (lower radiation = more clouds)
        if radiation < 200:
            base_cloud += 30
        elif radiation < 500:
            base_cloud += 15
        
        return min(100, max(0, base_cloud))
    
    def _estimate_temperature(self, date: dt.date, hour: int) -> float:
        """Estimate temperature based on date and time."""
        # Base temperature for Lahore
        base_temp = 25  # 25°C average
        
        # Seasonal variation
        doy = date.timetuple().tm_yday
        seasonal_temp = 10 * np.sin(2 * np.pi * (doy - 80) / 365)  # ±10°C seasonal variation
        
        # Daily variation (cooler at night, warmer during day)
        if 6 <= hour <= 18:  # Daylight hours
            daily_temp = 8 * np.sin(np.pi * (hour - 6) / 12)  # ±8°C daily variation
        else:
            daily_temp = -5  # Cooler at night
        
        return base_temp + seasonal_temp + daily_temp
    
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
        """Get fallback forecast when calculation fails."""
        log.warning("Using fallback simple weather forecast")
        
        fallback_forecasts = {}
        today = dt.datetime.now(self.timezone).date()
        
        for i in range(days):
            date = today + dt.timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            # Generate reasonable fallback data
            hours = list(range(24))
            cloud_cover = [25] * 24  # 25% cloud cover
            temperature = [28] * 24  # 28°C (good for Lahore)
            humidity = [45] * 24  # 45% humidity
            wind_speed = [2.5] * 24  # 2.5 m/s
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
                    "irradiance_factor": 0.75,
                    "temperature_factor": 1.0,
                    "soiling_factor": 0.95,
                    "overall_factor": 0.71
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
                log.info(f"Using cached day factors (cache_key: {self._cache_key})")
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
                result = {"today": 0.75, "tomorrow": 0.75}
            
            # Cache the result
            self._factors_cache = result
            self._factors_cache_time = current_time
            log.info(f"Generated and cached day factors: {result} (cache_key: {self._cache_key})")
            
            return result
                
        except Exception as e:
            log.error(f"Error getting day factors: {e}")
            return {"today": 0.75, "tomorrow": 0.75}
