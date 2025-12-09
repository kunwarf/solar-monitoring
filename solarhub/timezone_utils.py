"""
Timezone Utilities for Solar Monitoring System

This module provides centralized timezone handling to ensure all data
is consistently stored and processed in the configured system timezone.
It handles conversion from OS timezone to the configured timezone.
"""

import pytz
from datetime import datetime, timezone
from typing import Optional
import os
import logging

# Global logger
log = logging.getLogger(__name__)

# Global timezone variables (will be initialized from config)
SYSTEM_TZ = None
CONFIGURED_TZ = None
UTC = pytz.UTC
_WARNING_LOGGED = False  # Track if we've already logged the warning

def initialize_timezones(configured_timezone: str = "Asia/Karachi"):
    """
    Initialize timezone settings from configuration.
    This should be called once at application startup.
    
    Args:
        configured_timezone: The timezone string from config (e.g., "Asia/Karachi")
    """
    global SYSTEM_TZ, CONFIGURED_TZ, _WARNING_LOGGED
    
    try:
        # Set the configured timezone
        CONFIGURED_TZ = pytz.timezone(configured_timezone)
        log.info(f"Configured timezone set to: {configured_timezone}")
        
        # Detect OS timezone
        SYSTEM_TZ = get_os_timezone()
        log.info(f"OS timezone detected as: {SYSTEM_TZ.zone}")
        
        # Reset warning flag since we're now initialized
        _WARNING_LOGGED = False
        
    except Exception as e:
        log.error(f"Failed to initialize timezones: {e}")
        # Fallback to UTC
        CONFIGURED_TZ = UTC
        SYSTEM_TZ = UTC

def get_os_timezone():
    """
    Get the system's local timezone.
    This detects the OS timezone which may be different from our configured timezone.
    """
    try:
        # Try to get system timezone from environment
        system_tz = os.environ.get('TZ')
        if system_tz:
            return pytz.timezone(system_tz)
        
        # Try to detect from system time
        import time
        if time.daylight:
            offset = time.altzone
        else:
            offset = time.timezone
        
        # Convert offset to timezone name (simplified detection)
        if offset == -18000:  # UTC-5
            return pytz.timezone('America/New_York')
        elif offset == -28800:  # UTC-8
            return pytz.timezone('America/Los_Angeles')
        elif offset == 0:  # UTC
            return UTC
        elif offset == 18000:  # UTC+5 (Pakistan)
            return pytz.timezone('Asia/Karachi')
        else:
            # Try to get system timezone using platform-specific methods
            try:
                import platform
                if platform.system() == 'Windows':
                    # Windows timezone detection
                    import winreg
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                      r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation") as key:
                        tz_name = winreg.QueryValueEx(key, "TimeZoneKeyName")[0]
                        return pytz.timezone(tz_name)
                else:
                    # Unix/Linux timezone detection
                    import subprocess
                    result = subprocess.run(['timedatectl', 'show', '--property=Timezone', '--value'], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        tz_name = result.stdout.strip()
                        return pytz.timezone(tz_name)
            except Exception:
                pass
            
            # Fallback to UTC
            return UTC
            
    except Exception as e:
        log.warning(f"Failed to detect OS timezone: {e}, using UTC")
        return UTC

def get_configured_timezone():
    """Get the configured timezone object."""
    global _WARNING_LOGGED
    if CONFIGURED_TZ is None:
        if not _WARNING_LOGGED:
            log.warning("Timezones not initialized, using UTC. This is normal during module import. Timezones will be initialized at application startup.")
            _WARNING_LOGGED = True
        return UTC
    return CONFIGURED_TZ

def get_system_timezone():
    """Get the OS timezone object."""
    global _WARNING_LOGGED
    if SYSTEM_TZ is None:
        if not _WARNING_LOGGED:
            log.warning("Timezones not initialized, using UTC. This is normal during module import. Timezones will be initialized at application startup.")
            _WARNING_LOGGED = True
        return UTC
    return SYSTEM_TZ

def now_configured() -> datetime:
    """Get current time in configured timezone."""
    return datetime.now(get_configured_timezone())

def now_system() -> datetime:
    """Get current time in OS timezone."""
    return datetime.now(get_system_timezone())

def now_utc() -> datetime:
    """Get current time in UTC."""
    return datetime.now(UTC)

def to_configured(dt: datetime) -> datetime:
    """
    Convert any datetime to configured timezone.
    
    Args:
        dt: datetime object (with or without timezone info)
    
    Returns:
        datetime object in configured timezone
    """
    if dt.tzinfo is None:
        # No timezone info, assume it's in OS timezone
        dt = get_system_timezone().localize(dt)
    
    return dt.astimezone(get_configured_timezone())

def to_system(dt: datetime) -> datetime:
    """
    Convert any datetime to OS timezone.
    
    Args:
        dt: datetime object (with or without timezone info)
    
    Returns:
        datetime object in OS timezone
    """
    if dt.tzinfo is None:
        # No timezone info, assume it's in configured timezone
        dt = get_configured_timezone().localize(dt)
    
    return dt.astimezone(get_system_timezone())

def to_utc(dt: datetime) -> datetime:
    """
    Convert any datetime to UTC timezone.
    
    Args:
        dt: datetime object (with or without timezone info)
    
    Returns:
        datetime object in UTC timezone
    """
    if dt.tzinfo is None:
        # No timezone info, assume it's in configured timezone
        dt = get_configured_timezone().localize(dt)
    
    return dt.astimezone(UTC)

def from_os_to_configured(dt: datetime) -> datetime:
    """
    Convert datetime from OS timezone to configured timezone.
    This is the main function for database operations.
    
    Args:
        dt: datetime object in OS timezone (with or without timezone info)
    
    Returns:
        datetime object in configured timezone
    """
    if dt.tzinfo is None:
        # No timezone info, assume it's in OS timezone
        dt = get_system_timezone().localize(dt)
    
    return dt.astimezone(get_configured_timezone())

def now_configured_iso() -> str:
    """Get current time in configured timezone as ISO string."""
    return now_configured().isoformat()

def now_system_iso() -> str:
    """Get current time in OS timezone as ISO string."""
    return now_system().isoformat()

def now_utc_iso() -> str:
    """Get current time in UTC as ISO string."""
    return now_utc().isoformat()

def get_configured_timezone_name() -> str:
    """Get the configured timezone name as string."""
    return get_configured_timezone().zone

def get_system_timezone_name() -> str:
    """Get the OS timezone name as string."""
    return get_system_timezone().zone

def get_hour_configured(dt: Optional[datetime] = None) -> int:
    """
    Get hour in configured timezone.
    
    Args:
        dt: datetime object (optional, defaults to now)
    
    Returns:
        Hour (0-23) in configured timezone
    """
    if dt is None:
        dt = now_configured()
    elif dt.tzinfo is None:
        # No timezone info, assume it's in OS timezone
        dt = get_system_timezone().localize(dt)
        dt = dt.astimezone(get_configured_timezone())
    else:
        dt = dt.astimezone(get_configured_timezone())
    
    return dt.hour

def get_hour_system(dt: Optional[datetime] = None) -> int:
    """
    Get hour in OS timezone.
    
    Args:
        dt: datetime object (optional, defaults to now)
    
    Returns:
        Hour (0-23) in OS timezone
    """
    if dt is None:
        dt = now_system()
    elif dt.tzinfo is None:
        # No timezone info, assume it's in configured timezone
        dt = get_configured_timezone().localize(dt)
        dt = dt.astimezone(get_system_timezone())
    else:
        dt = dt.astimezone(get_system_timezone())
    
    return dt.hour

def ensure_configured_datetime(dt: datetime) -> datetime:
    """
    Ensure datetime is in configured timezone.
    
    If in other timezone, convert to configured.
    If no timezone, assume OS timezone and convert to configured.
    
    Args:
        dt: datetime object
    
    Returns:
        datetime object in configured timezone
    """
    if dt.tzinfo is None:
        # No timezone info, assume it's in OS timezone
        dt = get_system_timezone().localize(dt)
    
    return dt.astimezone(get_configured_timezone())

def create_configured_datetime(year: int, month: int, day: int, 
                              hour: int = 0, minute: int = 0, second: int = 0) -> datetime:
    """
    Create a datetime object in configured timezone.
    
    Args:
        year, month, day, hour, minute, second: datetime components
    
    Returns:
        datetime object in configured timezone
    """
    return get_configured_timezone().localize(
        datetime(year, month, day, hour, minute, second)
    )

def get_configured_start_of_day(dt: Optional[datetime] = None) -> datetime:
    """
    Get start of day (00:00:00) in configured timezone.
    
    Args:
        dt: datetime object (optional, defaults to today)
    
    Returns:
        datetime object representing start of day in configured timezone
    """
    if dt is None:
        dt = now_configured()
    elif dt.tzinfo is None:
        # No timezone info, assume it's in OS timezone
        dt = get_system_timezone().localize(dt)
        dt = dt.astimezone(get_configured_timezone())
    else:
        dt = dt.astimezone(get_configured_timezone())
    
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)

def get_configured_end_of_day(dt: Optional[datetime] = None) -> datetime:
    """
    Get end of day (23:59:59) in configured timezone.
    
    Args:
        dt: datetime object (optional, defaults to today)
    
    Returns:
        datetime object representing end of day in configured timezone
    """
    if dt is None:
        dt = now_configured()
    elif dt.tzinfo is None:
        # No timezone info, assume it's in OS timezone
        dt = get_system_timezone().localize(dt)
        dt = dt.astimezone(get_configured_timezone())
    else:
        dt = dt.astimezone(get_configured_timezone())
    
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)

def parse_iso_to_configured(iso_string: str) -> datetime:
    """
    Parse ISO string and convert to configured timezone.
    
    Args:
        iso_string: ISO format datetime string
    
    Returns:
        datetime object in configured timezone
    """
    dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    return dt.astimezone(get_configured_timezone())

def get_configured_date_string(dt: Optional[datetime] = None) -> str:
    """
    Get date string in configured timezone.
    
    Args:
        dt: datetime object (optional, defaults to now)
    
    Returns:
        Date string in YYYY-MM-DD format in configured timezone
    """
    if dt is None:
        dt = now_configured()
    elif dt.tzinfo is None:
        # No timezone info, assume it's in OS timezone
        dt = get_system_timezone().localize(dt)
        dt = dt.astimezone(get_configured_timezone())
    else:
        dt = dt.astimezone(get_configured_timezone())
    
    return dt.strftime('%Y-%m-%d')

# Backward compatibility aliases (deprecated - use new functions)
def now_pkst() -> datetime:
    """Deprecated: Use now_configured() instead."""
    log.warning("now_pkst() is deprecated, use now_configured() instead")
    return now_configured()

def now_pkst_iso() -> str:
    """Deprecated: Use now_configured_iso() instead."""
    log.warning("now_pkst_iso() is deprecated, use now_configured_iso() instead")
    return now_configured_iso()

def to_pkst(dt: datetime) -> datetime:
    """Deprecated: Use to_configured() instead."""
    log.warning("to_pkst() is deprecated, use to_configured() instead")
    return to_configured(dt)

def get_pkst_start_of_day(dt: Optional[datetime] = None) -> datetime:
    """Deprecated: Use get_configured_start_of_day() instead."""
    log.warning("get_pkst_start_of_day() is deprecated, use get_configured_start_of_day() instead")
    return get_configured_start_of_day(dt)

def get_pkst_end_of_day(dt: Optional[datetime] = None) -> datetime:
    """Deprecated: Use get_configured_end_of_day() instead."""
    log.warning("get_pkst_end_of_day() is deprecated, use get_configured_end_of_day() instead")
    return get_configured_end_of_day(dt)

def parse_iso_to_pkst(iso_string: str) -> datetime:
    """Deprecated: Use parse_iso_to_configured() instead."""
    log.warning("parse_iso_to_pkst() is deprecated, use parse_iso_to_configured() instead")
    return parse_iso_to_configured(iso_string)

def get_pkst_date_string(dt: Optional[datetime] = None) -> str:
    """Deprecated: Use get_configured_date_string() instead."""
    log.warning("get_pkst_date_string() is deprecated, use get_configured_date_string() instead")
    return get_configured_date_string(dt)

def ensure_pkst_datetime(dt: datetime) -> datetime:
    """Deprecated: Use ensure_configured_datetime() instead."""
    log.warning("ensure_pkst_datetime() is deprecated, use ensure_configured_datetime() instead")
    return ensure_configured_datetime(dt)

# Legacy constants for backward compatibility
PKST = None  # Will be set to configured timezone after initialization
SYSTEM_TZ = None  # Will be set to OS timezone after initialization