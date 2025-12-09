#!/usr/bin/env python3
"""
Database migration script to add timezone columns to all tables.
This ensures every record includes timezone information.
"""

import sqlite3
import os
import shutil
from datetime import datetime
import pytz

def find_database_path():
    """Find the database file in common locations."""
    possible_paths = [
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
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to: {backup_path}")
    return backup_path

def add_timezone_columns(db_path):
    """Add timezone columns to all tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Found tables: {tables}")
        
        # Filter out system tables and process all user tables
        system_tables = ['sqlite_sequence', 'sqlite_master', 'sqlite_stat1', 'sqlite_stat4']
        user_tables = [table for table in tables if table not in system_tables]
        
        print(f"Found {len(user_tables)} user tables: {user_tables}")
        
        for table in user_tables:
            print(f"\nUpdating table: {table}")
            
            # Check if timezone column already exists
            cursor.execute(f"PRAGMA table_info({table});")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'timezone' not in columns:
                # Add timezone column
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN timezone TEXT DEFAULT 'UTC';")
                print(f"  ✓ Added timezone column to {table}")
            else:
                print(f"  ✓ timezone column already exists in {table}")
            
            # Update existing records with timezone info (set to UTC since current data is in UTC)
            cursor.execute(f"UPDATE {table} SET timezone = 'UTC' WHERE timezone IS NULL;")
            updated_rows = cursor.rowcount
            print(f"  ✓ Updated {updated_rows} existing records with timezone info (UTC)")
        
        # Create indexes for timezone columns on all tables
        print("\nCreating indexes for timezone columns...")
        
        for table in user_tables:
            try:
                # Check if timezone column exists before creating index
                cursor.execute(f"PRAGMA table_info({table});")
                columns = [row[1] for row in cursor.fetchall()]
                if 'timezone' in columns:
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_timezone ON {table}(timezone);")
                    print(f"  ✓ Created index for {table}.timezone")
                else:
                    print(f"  ⚠ No timezone column in {table}, skipping index")
            except Exception as e:
                print(f"  ⚠ Could not create index for {table}.timezone: {e}")
        
        # Commit all changes
        conn.commit()
        print("\n✅ All timezone columns added successfully!")
        
        # Show summary
        print("\n📊 Migration Summary:")
        for table in user_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE timezone IS NOT NULL;")
            with_tz = cursor.fetchone()[0]
            print(f"  {table}: {with_tz}/{count} records have timezone info")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def main():
    """Main migration function."""
    print("🕐 Starting timezone columns migration...")
    
    # Find database
    db_path = find_database_path()
    if not db_path:
        db_path = input("Please enter the full path to the database file: ").strip()
        if not os.path.exists(db_path):
            print(f"❌ Database file not found: {db_path}")
            return
    
    # Backup database
    backup_path = backup_database(db_path)
    
    try:
        # Add timezone columns
        add_timezone_columns(db_path)
        print(f"\n🎉 Migration completed successfully!")
        print(f"📁 Backup saved at: {backup_path}")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print(f"🔄 You can restore from backup: {backup_path}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
