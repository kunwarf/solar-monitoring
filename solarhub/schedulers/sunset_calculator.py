#!/usr/bin/env python3
"""
Sunset Time Calculator for Pakistan

Provides accurate sunset times for Pakistan throughout the year,
replacing hard-coded 18:00 sunset times with dynamic calculations.
"""

import logging
import math
from typing import Tuple
from datetime import datetime, timezone, timedelta
import pytz

log = logging.getLogger(__name__)

class PakistanSunsetCalculator:
    """
    Calculates sunset times for Pakistan using astronomical formulas.
    
    Pakistan coordinates: approximately 30.3753° N, 69.3451° E
    Timezone: Asia/Karachi (UTC+5)
    """
    
    def __init__(self, timezone_name: str = "Asia/Karachi"):
        # Pakistan coordinates (approximate center)
        self.latitude = 30.3753  # North
        self.longitude = 69.3451  # East
        self.timezone = pytz.timezone(timezone_name)
        
        # Month-by-month sunset times for Pakistan (fallback table)
        # These are approximate times in 24-hour format
        self.monthly_sunset_hours = {
            1: 17.5,   # January: ~5:30 PM
            2: 18.0,   # February: ~6:00 PM
            3: 18.3,   # March: ~6:20 PM
            4: 18.7,   # April: ~6:40 PM
            5: 19.0,   # May: ~7:00 PM
            6: 19.2,   # June: ~7:10 PM
            7: 19.1,   # July: ~7:05 PM
            8: 18.8,   # August: ~6:50 PM
            9: 18.3,   # September: ~6:20 PM
            10: 17.8,  # October: ~5:50 PM
            11: 17.3,  # November: ~5:20 PM
            12: 17.2   # December: ~5:10 PM
        }
    
    def get_sunset_hour(self, date: datetime = None) -> float:
        """
        Get sunset hour for a given date in Pakistan timezone.
        
        Args:
            date: Date to calculate sunset for (defaults to today)
            
        Returns:
            Sunset hour as float (e.g., 18.5 for 6:30 PM)
        """
        if date is None:
            from solarhub.timezone_utils import now_configured
            date = now_configured()
        
        try:
            # Convert to Pakistan timezone if needed
            if date.tzinfo is None:
                date = self.timezone.localize(date)
            elif date.tzinfo != self.timezone:
                date = date.astimezone(self.timezone)
            
            # Calculate astronomical sunset
            sunset_hour = self._calculate_astronomical_sunset(date)
            
            # Fallback to monthly table if calculation fails
            if sunset_hour is None:
                month = date.month
                sunset_hour = self.monthly_sunset_hours.get(month, 18.0)
                log.warning(f"Using fallback sunset time for month {month}: {sunset_hour}")
            
            return sunset_hour
            
        except Exception as e:
            log.error(f"Failed to calculate sunset time: {e}")
            # Fallback to monthly table
            month = date.month if date else now_configured().month
            return self.monthly_sunset_hours.get(month, 18.0)
    
    def _calculate_astronomical_sunset(self, date: datetime) -> float:
        """
        Calculate astronomical sunset time using solar position formulas.
        
        Args:
            date: Date in Pakistan timezone
            
        Returns:
            Sunset hour as float, or None if calculation fails
        """
        try:
            # Calculate day of year
            day_of_year = date.timetuple().tm_yday
            
            # Solar declination angle
            declination = 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))
            
            # Hour angle at sunset
            hour_angle = math.degrees(math.acos(-math.tan(math.radians(self.latitude)) * 
                                               math.tan(math.radians(declination))))
            
            # Sunset time in hours from noon
            sunset_hour_offset = hour_angle / 15.0
            
            # Convert to local time (noon = 12:00)
            sunset_hour = 12.0 + sunset_hour_offset
            
            # Adjust for longitude (Pakistan is UTC+5, so longitude offset is minimal)
            longitude_offset = (self.longitude - 75.0) / 15.0  # 75°E is standard meridian for UTC+5
            sunset_hour += longitude_offset
            
            # Ensure sunset is reasonable (between 16:00 and 20:00)
            if 16.0 <= sunset_hour <= 20.0:
                return sunset_hour
            else:
                log.warning(f"Calculated sunset hour {sunset_hour} is outside reasonable range")
                return None
                
        except Exception as e:
            log.error(f"Astronomical sunset calculation failed: {e}")
            return None
    
    def get_sunrise_hour(self, date: datetime = None) -> float:
        """
        Get sunrise hour for a given date in Pakistan timezone.
        
        Args:
            date: Date to calculate sunrise for (defaults to today)
            
        Returns:
            Sunrise hour as float (e.g., 6.5 for 6:30 AM)
        """
        if date is None:
            from solarhub.timezone_utils import now_configured
            date = now_configured()
        
        try:
            # Convert to Pakistan timezone if needed
            if date.tzinfo is None:
                date = self.timezone.localize(date)
            elif date.tzinfo != self.timezone:
                date = date.astimezone(self.timezone)
            
            # Calculate astronomical sunrise
            sunrise_hour = self._calculate_astronomical_sunrise(date)
            
            # Fallback to monthly table if calculation fails
            if sunrise_hour is None:
                month = date.month
                # Approximate sunrise times for Pakistan
                monthly_sunrise_hours = {
                    1: 7.0,   # January: ~7:00 AM
                    2: 6.8,   # February: ~6:50 AM
                    3: 6.3,   # March: ~6:20 AM
                    4: 5.8,   # April: ~5:50 AM
                    5: 5.5,   # May: ~5:30 AM
                    6: 5.3,   # June: ~5:20 AM
                    7: 5.4,   # July: ~5:25 AM
                    8: 5.7,   # August: ~5:40 AM
                    9: 6.0,   # September: ~6:00 AM
                    10: 6.3,  # October: ~6:20 AM
                    11: 6.7,  # November: ~6:40 AM
                    12: 7.0   # December: ~7:00 AM
                }
                sunrise_hour = monthly_sunrise_hours.get(month, 6.0)
                log.warning(f"Using fallback sunrise time for month {month}: {sunrise_hour}")
            
            return sunrise_hour
            
        except Exception as e:
            log.error(f"Failed to calculate sunrise time: {e}")
            # Fallback to monthly table
            month = date.month if date else now_configured().month
            return 6.0  # Default sunrise time
    
    def _calculate_astronomical_sunrise(self, date: datetime) -> float:
        """
        Calculate astronomical sunrise time using solar position formulas.
        
        Args:
            date: Date in Pakistan timezone
            
        Returns:
            Sunrise hour as float, or None if calculation fails
        """
        try:
            # Calculate day of year
            day_of_year = date.timetuple().tm_yday
            
            # Solar declination angle
            declination = 23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365))
            
            # Hour angle at sunrise (negative of sunset)
            hour_angle = math.degrees(math.acos(-math.tan(math.radians(self.latitude)) * 
                                               math.tan(math.radians(declination))))
            
            # Sunrise time in hours from noon
            sunrise_hour_offset = -hour_angle / 15.0
            
            # Convert to local time (noon = 12:00)
            sunrise_hour = 12.0 + sunrise_hour_offset
            
            # Adjust for longitude
            longitude_offset = (self.longitude - 75.0) / 15.0
            sunrise_hour += longitude_offset
            
            # Ensure sunrise is reasonable (between 5:00 and 8:00)
            if 5.0 <= sunrise_hour <= 8.0:
                return sunrise_hour
            else:
                log.warning(f"Calculated sunrise hour {sunrise_hour} is outside reasonable range")
                return None
                
        except Exception as e:
            log.error(f"Astronomical sunrise calculation failed: {e}")
            return None
    
    def is_night_time(self, date: datetime = None) -> bool:
        """
        Check if current time is during night hours (after sunset or before sunrise).
        
        Args:
            date: Date/time to check (defaults to now)
            
        Returns:
            True if it's night time, False otherwise
        """
        if date is None:
            from solarhub.timezone_utils import now_configured
            date = now_configured()
        
        # Convert to Pakistan timezone if needed
        if date.tzinfo is None:
            date = self.timezone.localize(date)
        elif date.tzinfo != self.timezone:
            date = date.astimezone(self.timezone)
        
        current_hour = date.hour + date.minute / 60.0
        sunset_hour = self.get_sunset_hour(date)
        sunrise_hour = self.get_sunrise_hour(date)
        
        # Night time is after sunset or before sunrise
        return current_hour >= sunset_hour or current_hour <= sunrise_hour
    
    def get_night_duration_hours(self, date: datetime = None) -> float:
        """
        Get duration of night in hours for a given date.
        
        Args:
            date: Date to calculate for (defaults to today)
            
        Returns:
            Night duration in hours
        """
        if date is None:
            from solarhub.timezone_utils import now_configured
            date = now_configured()
        
        sunset_hour = self.get_sunset_hour(date)
        sunrise_hour = self.get_sunrise_hour(date)
        
        # Night duration = (24 - sunset) + sunrise
        night_duration = (24.0 - sunset_hour) + sunrise_hour
        
        return night_duration
    
    def get_sunset_sunrise_times(self, date: datetime = None) -> Tuple[float, float]:
        """
        Get both sunset and sunrise times for a given date.
        
        Args:
            date: Date to calculate for (defaults to today)
            
        Returns:
            Tuple of (sunset_hour, sunrise_hour)
        """
        if date is None:
            from solarhub.timezone_utils import now_configured
            date = now_configured()
        
        sunset_hour = self.get_sunset_hour(date)
        sunrise_hour = self.get_sunrise_hour(date)
        
        return sunset_hour, sunrise_hour
