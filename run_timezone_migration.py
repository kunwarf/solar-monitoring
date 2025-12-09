#!/usr/bin/env python3
"""
Simple script to run the timezone migration.
This will add timezone columns to all database tables and set them to UTC.
"""

import subprocess
import sys
import os

def main():
    """Run the timezone migration script."""
    print("🕐 Starting timezone migration...")
    print("This will add timezone columns to all database tables and set them to UTC.")
    print("A backup will be created before making any changes.")
    
    # Check if migration script exists
    if not os.path.exists('add_timezone_columns_migration.py'):
        print("❌ Migration script not found: add_timezone_columns_migration.py")
        return 1
    
    try:
        # Run the migration script
        result = subprocess.run([sys.executable, 'add_timezone_columns_migration.py'], 
                              capture_output=True, text=True, check=True)
        
        print("✅ Migration completed successfully!")
        print("\n📋 Migration Output:")
        print(result.stdout)
        
        if result.stderr:
            print("\n⚠️ Warnings/Errors:")
            print(result.stderr)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed with exit code {e.returncode}")
        print(f"Error output: {e.stderr}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
    
    print("\n🎉 Timezone migration completed!")
    print("All database tables now have timezone columns set to UTC.")
    return 0

if __name__ == "__main__":
    exit(main())
