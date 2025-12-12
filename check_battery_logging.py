#!/usr/bin/env python3
"""
Quick script to check if battery unit and cell data are being logged properly.
"""
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

def check_battery_logging(db_path: str):
    """Check battery unit and cell sample logging."""
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    print("=" * 80)
    print("BATTERY DATA LOGGING CHECK")
    print("=" * 80)
    
    # Check battery bank samples
    print("\n1. BATTERY BANK SAMPLES (battery_bank_samples):")
    try:
        cur.execute("SELECT COUNT(*), MAX(ts) FROM battery_bank_samples")
        count, latest = cur.fetchone()
        print(f"   Total samples: {count}")
        print(f"   Latest sample: {latest}")
        
        # Check recent samples (last hour)
        one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("SELECT COUNT(*), COUNT(DISTINCT bank_id) FROM battery_bank_samples WHERE ts >= ?", (one_hour_ago,))
        recent_count, banks = cur.fetchone()
        print(f"   Samples in last hour: {recent_count} (from {banks} bank(s))")
        
        # List all banks
        cur.execute("SELECT DISTINCT bank_id FROM battery_bank_samples ORDER BY bank_id")
        banks_list = [row[0] for row in cur.fetchall()]
        print(f"   Banks with data: {banks_list}")
    except sqlite3.OperationalError as e:
        print(f"   ERROR: {e}")
    
    # Check battery unit samples
    print("\n2. BATTERY UNIT SAMPLES (battery_unit_samples):")
    try:
        cur.execute("SELECT COUNT(*), MAX(ts) FROM battery_unit_samples")
        count, latest = cur.fetchone()
        print(f"   Total samples: {count}")
        print(f"   Latest sample: {latest}")
        
        # Check recent samples
        one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("SELECT COUNT(*), COUNT(DISTINCT bank_id), COUNT(DISTINCT power) FROM battery_unit_samples WHERE ts >= ?", (one_hour_ago,))
        recent_count, banks, units = cur.fetchone()
        print(f"   Samples in last hour: {recent_count} (from {banks} bank(s), {units} unit(s))")
        
        # List banks and units
        cur.execute("""
            SELECT bank_id, power, COUNT(*) as sample_count, MAX(ts) as latest
            FROM battery_unit_samples 
            GROUP BY bank_id, power 
            ORDER BY bank_id, power
        """)
        print("   Units by bank:")
        for row in cur.fetchall():
            bank_id, power, samples, latest_ts = row
            print(f"     - Bank: {bank_id}, Unit: {power}, Samples: {samples}, Latest: {latest_ts}")
    except sqlite3.OperationalError as e:
        print(f"   ERROR: {e}")
    
    # Check battery cell samples
    print("\n3. BATTERY CELL SAMPLES (battery_cell_samples):")
    try:
        cur.execute("SELECT COUNT(*), MAX(ts) FROM battery_cell_samples")
        count, latest = cur.fetchone()
        print(f"   Total samples: {count}")
        print(f"   Latest sample: {latest}")
        
        # Check recent samples
        one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            SELECT COUNT(*), COUNT(DISTINCT bank_id), COUNT(DISTINCT power), COUNT(DISTINCT cell)
            FROM battery_cell_samples 
            WHERE ts >= ?
        """, (one_hour_ago,))
        recent_count, banks, units, cells = cur.fetchone()
        print(f"   Samples in last hour: {recent_count} (from {banks} bank(s), {units} unit(s), {cells} unique cells)")
        
        # List cells by bank and unit (with error handling for encoding issues)
        try:
            cur.execute("""
                SELECT bank_id, power, COUNT(DISTINCT cell) as cell_count, COUNT(*) as sample_count, MAX(ts) as latest
                FROM battery_cell_samples 
                GROUP BY bank_id, power 
                ORDER BY bank_id, power
            """)
            print("   Cells by bank/unit:")
            for row in cur.fetchall():
                try:
                    bank_id, power, cell_count, samples, latest_ts = row
                    # Handle potential encoding issues
                    if isinstance(bank_id, bytes):
                        bank_id = bank_id.decode('utf-8', errors='replace')
                    if isinstance(latest_ts, bytes):
                        latest_ts = latest_ts.decode('utf-8', errors='replace')
                    print(f"     - Bank: {bank_id}, Unit: {power}, Cells: {cell_count}, Samples: {samples}, Latest: {latest_ts}")
                except Exception as e:
                    print(f"     - Error decoding row: {e}")
        except Exception as e:
            print(f"   ERROR: Could not query cells by bank/unit: {e}")
        
        # Show sample cell data (with error handling for encoding issues)
        try:
            cur.execute("""
                SELECT bank_id, power, cell, voltage, temperature, ts
                FROM battery_cell_samples 
                ORDER BY ts DESC 
                LIMIT 5
            """)
            print("\n   Recent cell samples (last 5):")
            for row in cur.fetchall():
                try:
                    bank_id, power, cell, voltage, temp, ts = row
                    # Handle potential encoding issues
                    if isinstance(bank_id, bytes):
                        bank_id = bank_id.decode('utf-8', errors='replace')
                    if isinstance(ts, bytes):
                        ts = ts.decode('utf-8', errors='replace')
                    print(f"     - {ts}: Bank={bank_id}, Unit={power}, Cell={cell}, V={voltage}V, T={temp}°C")
                except Exception as e:
                    print(f"     - Error decoding row: {e}")
        except Exception as e:
            print(f"   ERROR: Could not query cell samples: {e}")
            # Try to check for encoding issues
            try:
                cur.execute("SELECT COUNT(*) FROM battery_cell_samples")
                count = cur.fetchone()[0]
                print(f"   Total cell samples in table: {count}")
                print(f"   WARNING: There may be encoding/corruption issues in battery_cell_samples table")
            except Exception as e2:
                print(f"   ERROR: Could not even count cell samples: {e2}")
    except sqlite3.OperationalError as e:
        print(f"   ERROR: {e}")
    
    # Check if jkbms_bank_ble has data
    print("\n4. SPECIFIC CHECK: jkbms_bank_ble")
    try:
        # Bank samples
        cur.execute("SELECT COUNT(*), MAX(ts) FROM battery_bank_samples WHERE bank_id = 'jkbms_bank_ble'")
        count, latest = cur.fetchone()
        print(f"   Bank samples: {count} (latest: {latest})")
        
        # Unit samples
        cur.execute("SELECT COUNT(*), COUNT(DISTINCT power), MAX(ts) FROM battery_unit_samples WHERE bank_id = 'jkbms_bank_ble'")
        count, units, latest = cur.fetchone()
        print(f"   Unit samples: {count} (from {units} units, latest: {latest})")
        
        # Cell samples
        cur.execute("SELECT COUNT(*), COUNT(DISTINCT power), COUNT(DISTINCT cell), MAX(ts) FROM battery_cell_samples WHERE bank_id = 'jkbms_bank_ble'")
        count, units, cells, latest = cur.fetchone()
        print(f"   Cell samples: {count} (from {units} units, {cells} cells, latest: {latest})")
        
        if count == 0:
            print("   ⚠️  WARNING: No cell samples found for jkbms_bank_ble!")
    except sqlite3.OperationalError as e:
        print(f"   ERROR: {e}")
    
    print("\n" + "=" * 80)
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Try default path
        default_path = Path.home() / ".solarhub" / "solarhub.db"
        if default_path.exists():
            db_path = str(default_path)
        else:
            print("Usage: python check_battery_logging.py <db_path>")
            print(f"Or place database at: {default_path}")
            sys.exit(1)
    else:
        db_path = sys.argv[1]
    
    check_battery_logging(db_path)

