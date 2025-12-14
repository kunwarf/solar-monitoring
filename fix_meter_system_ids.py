#!/usr/bin/env python3
"""
Script to fix meter system_id mismatches where attachment_target doesn't match system_id.
This fixes cases where meters have system_id='system' but attachment_target='home'.
"""
import sqlite3
import sys
from pathlib import Path

def fix_meter_system_ids(db_path: str, dry_run: bool = True):
    """Fix meter system_id to match attachment_target when they don't match."""
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    
    print("=" * 80)
    print("METER SYSTEM_ID FIX")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will update database)'}")
    print()
    
    # Find meters where system_id doesn't match attachment_target
    cur.execute("""
        SELECT 
            meter_id,
            name,
            system_id,
            attachment_target,
            array_id
        FROM meters
        WHERE attachment_target IS NOT NULL
          AND attachment_target != ''
          AND system_id != attachment_target
          AND array_id IS NULL
    """)
    
    mismatched_meters = cur.fetchall()
    
    if not mismatched_meters:
        print("✓ No mismatched meters found. All meters have matching system_id and attachment_target.")
        con.close()
        return
    
    print(f"Found {len(mismatched_meters)} meter(s) with mismatched system_id and attachment_target:\n")
    
    for row in mismatched_meters:
        print(f"Meter: {row['meter_id']}")
        print(f"  Current system_id: {row['system_id']}")
        print(f"  attachment_target: {row['attachment_target']}")
        print(f"  Should be moved to system: {row['attachment_target']}")
        print()
    
    # Check if target systems exist
    print("Checking if target systems exist...")
    target_systems = set(row['attachment_target'] for row in mismatched_meters)
    
    for target_system in target_systems:
        cur.execute("SELECT COUNT(*) FROM systems WHERE system_id = ?", (target_system,))
        exists = cur.fetchone()[0] > 0
        if exists:
            print(f"  ✓ System '{target_system}' exists")
        else:
            print(f"  ✗ System '{target_system}' does NOT exist - cannot fix this meter!")
    
    print()
    
    if dry_run:
        print("DRY RUN: Would update the following meters:")
        for row in mismatched_meters:
            target_system = row['attachment_target']
            cur.execute("SELECT COUNT(*) FROM systems WHERE system_id = ?", (target_system,))
            system_exists = cur.fetchone()[0] > 0
            
            if system_exists:
                print(f"  UPDATE meters SET system_id = '{target_system}' WHERE meter_id = '{row['meter_id']}'")
            else:
                print(f"  SKIP {row['meter_id']} - target system '{target_system}' doesn't exist")
    else:
        print("Updating meters...")
        updated_count = 0
        skipped_count = 0
        
        for row in mismatched_meters:
            meter_id = row['meter_id']
            target_system = row['attachment_target']
            
            # Verify target system exists
            cur.execute("SELECT COUNT(*) FROM systems WHERE system_id = ?", (target_system,))
            system_exists = cur.fetchone()[0] > 0
            
            if not system_exists:
                print(f"  ✗ Skipping {meter_id} - target system '{target_system}' doesn't exist")
                skipped_count += 1
                continue
            
            try:
                cur.execute("""
                    UPDATE meters 
                    SET system_id = ? 
                    WHERE meter_id = ?
                """, (target_system, meter_id))
                print(f"  ✓ Updated {meter_id}: system_id '{row['system_id']}' -> '{target_system}'")
                updated_count += 1
            except sqlite3.Error as e:
                print(f"  ✗ Error updating {meter_id}: {e}")
                skipped_count += 1
        
        if updated_count > 0:
            con.commit()
            print(f"\n✓ Successfully updated {updated_count} meter(s)")
        else:
            print(f"\n✗ No meters were updated")
        
        if skipped_count > 0:
            print(f"⚠ Skipped {skipped_count} meter(s) due to missing target systems")
    
    con.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix meter system_id to match attachment_target")
    parser.add_argument("db_path", help="Path to the database file")
    parser.add_argument("--apply", action="store_true", help="Actually apply the changes (default is dry-run)")
    
    args = parser.parse_args()
    
    if not Path(args.db_path).exists():
        print(f"Error: Database file not found: {args.db_path}")
        sys.exit(1)
    
    fix_meter_system_ids(args.db_path, dry_run=not args.apply)

