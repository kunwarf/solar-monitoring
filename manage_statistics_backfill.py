#!/usr/bin/env python3
"""
Helper script to enable/disable statistics backfill via database flag.

Usage:
    python manage_statistics_backfill.py <db_path> enable   # Enable backfill
    python manage_statistics_backfill.py <db_path> disable  # Disable backfill
    python manage_statistics_backfill.py <db_path> status   # Check current status
"""

import sqlite3
import sys
from pathlib import Path

def get_flag_value(db_path: str) -> str:
    """Get current value of enable_statistics_backfill flag."""
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT value FROM configuration WHERE key = ?", ("enable_statistics_backfill",))
    result = cur.fetchone()
    con.close()
    return result[0] if result else None

def set_flag_value(db_path: str, value: str) -> None:
    """Set value of enable_statistics_backfill flag."""
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO configuration (key, value, updated_at, source)
        VALUES ('enable_statistics_backfill', ?, datetime('now'), 'manual')
    """, (value,))
    con.commit()
    con.close()

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    db_path = sys.argv[1]
    action = sys.argv[2].lower()
    
    if not Path(db_path).exists():
        print(f"Error: Database file not found: {db_path}")
        sys.exit(1)
    
    if action == "enable":
        set_flag_value(db_path, "true")
        print("✓ Statistics backfill enabled")
        print("  Backfill will run on next application restart")
    elif action == "disable":
        set_flag_value(db_path, "false")
        print("✓ Statistics backfill disabled")
        print("  Backfill will not run on next application restart")
    elif action == "status":
        value = get_flag_value(db_path)
        if value is None:
            print("Status: Flag not set (defaults to disabled)")
        else:
            status = "enabled" if value.lower() == "true" else "disabled"
            print(f"Status: Statistics backfill is {status}")
    else:
        print(f"Error: Unknown action '{action}'")
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()

