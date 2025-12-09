#!/usr/bin/env python3
"""
Test script to verify timezone consistency in the smart scheduler.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from solarhub.timezone_utils import *
from datetime import datetime, timedelta
import pandas as pd
import pytz

def test_smart_scheduler_timezone():
    """Test timezone consistency in smart scheduler components."""
    print("=== Testing Smart Scheduler Timezone Consistency ===\n")
    
    # Test 1: Timezone initialization
    print("1. Testing timezone initialization:")
    from solarhub.timezone_utils import PKST
    print(f"   PKST timezone: {PKST}")
    print(f"   PKST zone: {PKST.zone}")
    print()
    
    # Test 2: Current time functions
    print("2. Testing current time functions:")
    now_pkst_time = now_pkst()
    now_pkst_iso_str = now_pkst_iso()
    
    print(f"   PKST now: {now_pkst_time}")
    print(f"   PKST ISO: {now_pkst_iso_str}")
    print()
    
    # Test 3: Pandas Timestamp conversion
    print("3. Testing pandas Timestamp conversion:")
    tznow = pd.Timestamp(now_pkst())
    print(f"   Pandas Timestamp from PKST: {tznow}")
    print(f"   Timezone: {tznow.tz}")
    print(f"   Hour: {tznow.hour}")
    print(f"   Day of year: {tznow.dayofyear}")
    print()
    
    # Test 4: Date string formatting
    print("4. Testing date string formatting:")
    date_str = tznow.strftime('%Y-%m-%d')
    time_str = tznow.strftime('%H:%M:%S')
    print(f"   Date string: {date_str}")
    print(f"   Time string: {time_str}")
    print()
    
    # Test 5: Timezone conversion consistency
    print("5. Testing timezone conversion consistency:")
    test_dt_utc = datetime(2024, 1, 15, 12, 0, 0, tzinfo=pytz.UTC)
    test_dt_naive = datetime(2024, 1, 15, 17, 0, 0)  # This should be treated as PKST
    
    converted_utc = to_pkst(test_dt_utc)
    converted_naive = to_pkst(test_dt_naive)
    
    print(f"   UTC input: {test_dt_utc}")
    print(f"   Converted to PKST: {converted_utc}")
    print(f"   Naive input (assumed PKST): {test_dt_naive}")
    print(f"   Converted to PKST: {converted_naive}")
    print()
    
    # Test 6: Pandas date range with timezone
    print("6. Testing pandas date range with timezone:")
    day = tznow.normalize()
    idx = pd.date_range(day, periods=24, freq="1h", tz=PKST)
    print(f"   Date range start: {idx[0]}")
    print(f"   Date range end: {idx[-1]}")
    print(f"   Number of hours: {len(idx)}")
    print(f"   First few hours: {[h.hour for h in idx[:5]]}")
    print()
    
    # Test 7: Timezone-aware datetime operations
    print("7. Testing timezone-aware datetime operations:")
    start_of_day = get_pkst_start_of_day(tznow)
    end_of_day = get_pkst_end_of_day(tznow)
    
    print(f"   Start of day: {start_of_day}")
    print(f"   End of day: {end_of_day}")
    print(f"   Hours in day: {(end_of_day - start_of_day).total_seconds() / 3600}")
    print()
    
    # Test 8: Timestamp comparison
    print("8. Testing timestamp comparison:")
    now1 = now_pkst()
    now2 = now_pkst()
    time_diff = (now2 - now1).total_seconds()
    
    print(f"   Time difference: {time_diff} seconds")
    print(f"   Same day: {now1.date() == now2.date()}")
    print(f"   Same hour: {now1.hour == now2.hour}")
    print()
    
    # Test 9: ISO string parsing
    print("9. Testing ISO string parsing:")
    iso_utc = "2024-01-15T12:00:00Z"
    iso_pkst = "2024-01-15T17:00:00+05:00"
    
    parsed_utc = parse_iso_to_pkst(iso_utc)
    parsed_pkst = parse_iso_to_pkst(iso_pkst)
    
    print(f"   UTC ISO: {iso_utc}")
    print(f"   Parsed to PKST: {parsed_utc}")
    print(f"   PKST ISO: {iso_pkst}")
    print(f"   Parsed to PKST: {parsed_pkst}")
    print()
    
    # Test 10: Database formatting
    print("10. Testing database formatting:")
    test_dt = datetime(2024, 1, 15, 14, 30, 45, tzinfo=pytz.UTC)
    db_format = format_pkst_for_db(test_dt)
    
    print(f"   UTC input: {test_dt}")
    print(f"   DB format (PKST): {db_format}")
    print()
    
    print("=== All smart scheduler timezone tests completed ===")

if __name__ == "__main__":
    test_smart_scheduler_timezone()
