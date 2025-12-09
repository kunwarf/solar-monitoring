#!/usr/bin/env python3
"""
Test script to verify timezone consistency across the solar monitoring system.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from solarhub.timezone_utils import *
from datetime import datetime, timedelta
import pytz

def test_timezone_consistency():
    """Test timezone consistency across the system."""
    print("=== Testing Timezone Consistency ===\n")
    
    # Test 1: Current time functions
    print("1. Testing current time functions:")
    now_utc = datetime.now(pytz.UTC)
    now_pkst_time = now_pkst()
    now_pkst_iso_str = now_pkst_iso()
    
    print(f"   UTC now: {now_utc}")
    print(f"   PKST now: {now_pkst_time}")
    print(f"   PKST ISO: {now_pkst_iso_str}")
    print(f"   Time difference: {(now_pkst_time - now_utc.astimezone(PKST)).total_seconds()} seconds")
    print()
    
    # Test 2: Timezone conversion
    print("2. Testing timezone conversion:")
    test_dt_utc = datetime(2024, 1, 15, 12, 0, 0, tzinfo=pytz.UTC)
    test_dt_naive = datetime(2024, 1, 15, 12, 0, 0)
    
    converted_utc = to_pkst(test_dt_utc)
    converted_naive = to_pkst(test_dt_naive)
    
    print(f"   UTC input: {test_dt_utc}")
    print(f"   Converted to PKST: {converted_utc}")
    print(f"   Naive input: {test_dt_naive}")
    print(f"   Converted to PKST: {converted_naive}")
    print()
    
    # Test 3: ISO string parsing
    print("3. Testing ISO string parsing:")
    iso_utc = "2024-01-15T12:00:00Z"
    iso_pkst = "2024-01-15T17:00:00+05:00"
    
    parsed_utc = parse_iso_to_pkst(iso_utc)
    parsed_pkst = parse_iso_to_pkst(iso_pkst)
    
    print(f"   UTC ISO: {iso_utc}")
    print(f"   Parsed to PKST: {parsed_utc}")
    print(f"   PKST ISO: {iso_pkst}")
    print(f"   Parsed to PKST: {parsed_pkst}")
    print()
    
    # Test 4: Date and time string functions
    print("4. Testing date/time string functions:")
    test_dt = datetime(2024, 1, 15, 14, 30, 45, tzinfo=PKST)
    
    date_str = get_pkst_date_string(test_dt)
    time_str = get_pkst_time_string(test_dt)
    hour = get_pkst_hour(test_dt)
    
    print(f"   Test datetime: {test_dt}")
    print(f"   Date string: {date_str}")
    print(f"   Time string: {time_str}")
    print(f"   Hour: {hour}")
    print()
    
    # Test 5: Start/end of day functions
    print("5. Testing start/end of day functions:")
    test_dt = datetime(2024, 1, 15, 14, 30, 45, tzinfo=PKST)
    
    start_of_day = get_pkst_start_of_day(test_dt)
    end_of_day = get_pkst_end_of_day(test_dt)
    
    print(f"   Test datetime: {test_dt}")
    print(f"   Start of day: {start_of_day}")
    print(f"   End of day: {end_of_day}")
    print()
    
    # Test 6: Database formatting
    print("6. Testing database formatting:")
    test_dt = datetime(2024, 1, 15, 14, 30, 45, tzinfo=pytz.UTC)
    
    db_format = format_pkst_for_db(test_dt)
    print(f"   UTC input: {test_dt}")
    print(f"   DB format (PKST): {db_format}")
    print()
    
    # Test 7: Ensure PKST datetime
    print("7. Testing ensure PKST datetime:")
    test_dt_utc = datetime(2024, 1, 15, 12, 0, 0, tzinfo=pytz.UTC)
    test_dt_naive = datetime(2024, 1, 15, 17, 0, 0)  # This should be treated as PKST
    test_dt_pkst = datetime(2024, 1, 15, 17, 0, 0, tzinfo=PKST)
    
    ensured_utc = ensure_pkst_datetime(test_dt_utc)
    ensured_naive = ensure_pkst_datetime(test_dt_naive)
    ensured_pkst = ensure_pkst_datetime(test_dt_pkst)
    
    print(f"   UTC input: {test_dt_utc}")
    print(f"   Ensured PKST: {ensured_utc}")
    print(f"   Naive input: {test_dt_naive}")
    print(f"   Ensured PKST: {ensured_naive}")
    print(f"   PKST input: {test_dt_pkst}")
    print(f"   Ensured PKST: {ensured_pkst}")
    print()
    
    print("=== All timezone tests completed ===")

if __name__ == "__main__":
    test_timezone_consistency()
