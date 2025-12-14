#!/usr/bin/env python3
"""
Script to check meter attachments to systems in the database.
"""
import sqlite3
import sys
from pathlib import Path

def check_meter_attachments(db_path: str):
    """Check which system_id each meter is attached to."""
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    
    print("=" * 80)
    print("METER ATTACHMENT CHECK")
    print("=" * 80)
    
    # Check all systems
    print("\n1. Systems in database:")
    try:
        cur.execute("SELECT system_id, name, created_at FROM systems ORDER BY system_id")
        systems = cur.fetchall()
        if systems:
            for row in systems:
                name = row['name'] if 'name' in row.keys() else 'N/A'
                print(f"   - System ID: {row['system_id']}, Name: {name}")
        else:
            print("   No systems found!")
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            print("   Systems table does not exist yet (migration may not have run)")
        else:
            raise
    
    # Check all meters
    print("\n2. Meters in database:")
    cur.execute("""
        SELECT 
            meter_id, 
            name, 
            system_id, 
            array_id, 
            attachment_target,
            model,
            type
        FROM meters 
        ORDER BY system_id, meter_id
    """)
    meters = cur.fetchall()
    
    if meters:
        for row in meters:
            print(f"\n   Meter ID: {row['meter_id']}")
            name = row['name'] if 'name' in row.keys() and row['name'] else 'N/A'
            attachment_target = row['attachment_target'] if 'attachment_target' in row.keys() and row['attachment_target'] else 'N/A'
            model = row['model'] if 'model' in row.keys() and row['model'] else 'N/A'
            meter_type = row['type'] if 'type' in row.keys() and row['type'] else 'N/A'
            print(f"   - Name: {name}")
            print(f"   - System ID: {row['system_id']}")
            print(f"   - Array ID: {row['array_id'] or 'NULL (system-level)'}")
            print(f"   - Attachment Target: {attachment_target}")
            print(f"   - Model: {model}")
            print(f"   - Type: {meter_type}")
    else:
        print("   No meters found!")
    
    # Check for meters with system_id = 'home'
    print("\n3. Meters with system_id = 'home':")
    cur.execute("SELECT COUNT(*) FROM meters WHERE system_id = 'home'")
    count = cur.fetchone()[0]
    print(f"   Found {count} meter(s) with system_id = 'home'")
    
    if count > 0:
        cur.execute("SELECT meter_id, name, array_id, attachment_target FROM meters WHERE system_id = 'home'")
        for row in cur.fetchall():
            attachment_target = row['attachment_target'] if 'attachment_target' in row.keys() and row['attachment_target'] else 'N/A'
            print(f"   - {row['meter_id']}: array_id={row['array_id']}, attachment_target={attachment_target}")
    
    # Check for meters with system_id = 'system'
    print("\n4. Meters with system_id = 'system':")
    cur.execute("SELECT COUNT(*) FROM meters WHERE system_id = 'system'")
    count = cur.fetchone()[0]
    print(f"   Found {count} meter(s) with system_id = 'system'")
    
    if count > 0:
        cur.execute("SELECT meter_id, name, array_id, attachment_target FROM meters WHERE system_id = 'system'")
        for row in cur.fetchall():
            attachment_target = row['attachment_target'] if 'attachment_target' in row.keys() and row['attachment_target'] else 'N/A'
            print(f"   - {row['meter_id']}: array_id={row['array_id']}, attachment_target={attachment_target}")
    
    # Check for system-level meters (array_id is NULL)
    print("\n5. System-level meters (array_id IS NULL):")
    cur.execute("SELECT meter_id, name, system_id, attachment_target FROM meters WHERE array_id IS NULL")
    system_meters = cur.fetchall()
    print(f"   Found {len(system_meters)} system-level meter(s)")
    
    if system_meters:
        for row in system_meters:
            attachment_target = row['attachment_target'] if 'attachment_target' in row.keys() and row['attachment_target'] else 'N/A'
            print(f"   - {row['meter_id']} (system: {row['system_id']}, attachment_target: {attachment_target})")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    cur.execute("SELECT system_id, COUNT(*) as count FROM meters GROUP BY system_id")
    summary = cur.fetchall()
    if summary:
        print("\nMeters per system:")
        for row in summary:
            print(f"   - System '{row['system_id']}': {row['count']} meter(s)")
    else:
        print("\nNo meters found in database!")
    
    con.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_meter_attachments.py <db_path>")
        print("Example: python check_meter_attachments.py ~/.solarhub/solarhub.db")
        sys.exit(1)
    
    db_path = sys.argv[1]
    if not Path(db_path).exists():
        print(f"Error: Database file not found: {db_path}")
        sys.exit(1)
    
    check_meter_attachments(db_path)

