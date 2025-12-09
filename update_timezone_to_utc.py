#!/usr/bin/env python3
"""
Script to update all existing timezone values from 'Asia/Karachi' to 'UTC'.
This is needed when the data is actually in UTC but was marked as PKST.
"""

import sqlite3
import os
import shutil
from datetime import datetime

def find_database_path():
    """Find the database file in common locations."""
    possible_paths = [
        'solarhub.db',
        os.path.expanduser('~/.solarhub/solarhub.db')
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"Found database at: {path}")
            return path
    
    print("Database not found in common locations. Please provide the path manually.")
    return None

def backup_database(db_path):
    """Create a backup of the database before migration."""
    backup_path = f"{db_path}.backup_utc_update_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to: {backup_path}")
    return backup_path

def update_timezone_to_utc(db_path):
    """Update all timezone values from 'Asia/Karachi' to 'UTC'."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Found tables: {tables}")
        
        # Define tables that have timezone columns
        tables_to_update = [
            'energy_samples',
            'hourly_energy', 
            'pv_daily',
            'configuration',
            'inverter_config',
            'system_logs'
        ]
        
        total_updated = 0
        
        for table in tables_to_update:
            if table in tables:
                print(f"\nUpdating table: {table}")
                
                # Check if timezone column exists
                cursor.execute(f"PRAGMA table_info({table});")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'timezone' in columns:
                    # Count records with 'Asia/Karachi' timezone
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE timezone = 'Asia/Karachi';")
                    asia_karachi_count = cursor.fetchone()[0]
                    
                    # Count records with 'UTC' timezone
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE timezone = 'UTC';")
                    utc_count = cursor.fetchone()[0]
                    
                    # Count total records
                    cursor.execute(f"SELECT COUNT(*) FROM {table};")
                    total_count = cursor.fetchone()[0]
                    
                    print(f"  Current timezone distribution:")
                    print(f"    Asia/Karachi: {asia_karachi_count}")
                    print(f"    UTC: {utc_count}")
                    print(f"    NULL/Other: {total_count - asia_karachi_count - utc_count}")
                    print(f"    Total: {total_count}")
                    
                    if asia_karachi_count > 0:
                        # Update all 'Asia/Karachi' records to 'UTC'
                        cursor.execute(f"UPDATE {table} SET timezone = 'UTC' WHERE timezone = 'Asia/Karachi';")
                        updated_rows = cursor.rowcount
                        total_updated += updated_rows
                        print(f"  ✓ Updated {updated_rows} records from Asia/Karachi to UTC")
                    else:
                        print(f"  ✓ No Asia/Karachi records found to update")
                    
                    # Also update any NULL timezone records to UTC
                    cursor.execute(f"UPDATE {table} SET timezone = 'UTC' WHERE timezone IS NULL;")
                    null_updated = cursor.rowcount
                    if null_updated > 0:
                        total_updated += null_updated
                        print(f"  ✓ Updated {null_updated} NULL timezone records to UTC")
                    
                    # Verify the update
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE timezone = 'UTC';")
                    final_utc_count = cursor.fetchone()[0]
                    print(f"  ✓ Final UTC count: {final_utc_count}/{total_count}")
                    
                else:
                    print(f"  ⚠ No timezone column found in {table}, skipping")
            else:
                print(f"  ⚠ Table {table} not found, skipping")
        
        # Commit all changes
        conn.commit()
        print(f"\n✅ Successfully updated {total_updated} records to UTC timezone!")
        
        # Show final summary
        print("\n📊 Final Summary:")
        for table in tables_to_update:
            if table in tables:
                cursor.execute(f"PRAGMA table_info({table});")
                columns = [row[1] for row in cursor.fetchall()]
                if 'timezone' in columns:
                    cursor.execute(f"SELECT timezone, COUNT(*) FROM {table} GROUP BY timezone;")
                    timezone_counts = cursor.fetchall()
                    print(f"  {table}:")
                    for tz, count in timezone_counts:
                        print(f"    {tz or 'NULL'}: {count}")
        
    except Exception as e:
        print(f"❌ Error during update: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """Main update function."""
    print("🕐 Starting timezone update from Asia/Karachi to UTC...")
    print("This will update all existing records to use UTC timezone.")
    
    # Find database
    db_path = find_database_path()
    if not db_path:
        db_path = input("Please enter the full path to the database file: ").strip()
        if not os.path.exists(db_path):
            print(f"❌ Database file not found: {db_path}")
            return 1
    
    # Backup database
    backup_path = backup_database(db_path)
    
    try:
        # Update timezone values
        update_timezone_to_utc(db_path)
        print(f"\n🎉 Timezone update completed successfully!")
        print(f"📁 Backup saved at: {backup_path}")
        
    except Exception as e:
        print(f"\n❌ Update failed: {e}")
        print(f"🔄 You can restore from backup: {backup_path}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
