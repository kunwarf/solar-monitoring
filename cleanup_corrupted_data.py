#!/usr/bin/env python3
"""
Script to identify and clean up corrupted data in battery_cell_samples table.

This script:
1. Identifies corrupted rows (invalid bank_id, invalid power values, etc.)
2. Reports what would be cleaned
3. Optionally deletes corrupted rows (with --delete flag)
"""
import sqlite3
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple

def is_valid_bank_id(bank_id: Any) -> bool:
    """Check if bank_id is a valid string."""
    if bank_id is None:
        return False
    if isinstance(bank_id, bytes):
        return False
    if not isinstance(bank_id, str):
        return False
    # Check if it's a valid UTF-8 string and not empty
    try:
        bank_id.encode('utf-8')
        return len(bank_id.strip()) > 0
    except (UnicodeEncodeError, AttributeError):
        return False

def is_valid_power(power: Any) -> bool:
    """Check if power is a valid integer in reasonable range (1-100)."""
    if power is None:
        return False
    try:
        power_int = int(power)
        # Reasonable range for battery unit index: 1-100
        return 1 <= power_int <= 100
    except (ValueError, TypeError):
        return False

def is_valid_cell(cell: Any) -> bool:
    """Check if cell is a valid integer in reasonable range (1-100)."""
    if cell is None:
        return False
    try:
        cell_int = int(cell)
        # Reasonable range for cell index: 1-100
        return 1 <= cell_int <= 100
    except (ValueError, TypeError):
        return False

def identify_corrupted_rows(db_path: str) -> Dict[str, Any]:
    """Identify corrupted rows in battery_cell_samples table."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Get total count
    cur.execute("SELECT COUNT(*) FROM battery_cell_samples")
    total_count = cur.fetchone()[0]
    
    corrupted_rows = []
    valid_rows = 0
    
    # Fetch all rows and check each one
    cur.execute("SELECT rowid, ts, bank_id, power, cell, voltage, temperature FROM battery_cell_samples")
    
    print("Scanning battery_cell_samples table for corrupted data...")
    print(f"Total rows: {total_count}")
    
    for row in cur.fetchall():
        rowid, ts, bank_id, power, cell, voltage, temp = row
        issues = []
        
        # Check bank_id
        if not is_valid_bank_id(bank_id):
            issues.append(f"invalid_bank_id: {repr(bank_id)}")
        
        # Check power
        if not is_valid_power(power):
            issues.append(f"invalid_power: {repr(power)}")
        
        # Check cell
        if not is_valid_cell(cell):
            issues.append(f"invalid_cell: {repr(cell)}")
        
        if issues:
            corrupted_rows.append({
                "rowid": rowid,
                "ts": ts,
                "bank_id": bank_id,
                "power": power,
                "cell": cell,
                "issues": issues
            })
        else:
            valid_rows += 1
    
    conn.close()
    
    return {
        "total_rows": total_count,
        "valid_rows": valid_rows,
        "corrupted_rows": corrupted_rows,
        "corrupted_count": len(corrupted_rows)
    }

def delete_corrupted_rows(db_path: str, corrupted_rowids: List[int], backup: bool = True) -> int:
    """Delete corrupted rows from battery_cell_samples table."""
    if backup:
        # Create backup
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"\nCreating backup: {backup_path}")
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"Backup created successfully")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Delete corrupted rows
    placeholders = ','.join('?' * len(corrupted_rowids))
    cur.execute(f"DELETE FROM battery_cell_samples WHERE rowid IN ({placeholders})", corrupted_rowids)
    deleted_count = cur.rowcount
    
    conn.commit()
    conn.close()
    
    return deleted_count

def main():
    parser = argparse.ArgumentParser(description="Clean up corrupted data in battery_cell_samples table")
    parser.add_argument("db_path", help="Path to SQLite database")
    parser.add_argument("--delete", action="store_true", help="Actually delete corrupted rows (default: dry-run)")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating backup before deletion")
    parser.add_argument("--min-power", type=int, default=1, help="Minimum valid power value (default: 1)")
    parser.add_argument("--max-power", type=int, default=100, help="Maximum valid power value (default: 100)")
    
    args = parser.parse_args()
    
    if not Path(args.db_path).exists():
        print(f"Error: Database not found: {args.db_path}")
        sys.exit(1)
    
    print("=" * 80)
    print("CORRUPTED DATA CLEANUP")
    print("=" * 80)
    print(f"Database: {args.db_path}")
    print(f"Mode: {'DELETE' if args.delete else 'DRY-RUN (no changes will be made)'}")
    print()
    
    # Identify corrupted rows
    result = identify_corrupted_rows(args.db_path)
    
    print(f"\nResults:")
    print(f"  Total rows: {result['total_rows']}")
    print(f"  Valid rows: {result['valid_rows']}")
    print(f"  Corrupted rows: {result['corrupted_count']}")
    
    if result['corrupted_count'] == 0:
        print("\n✓ No corrupted data found!")
        return 0
    
    # Group by issue type
    issue_types = {}
    for row in result['corrupted_rows']:
        for issue in row['issues']:
            issue_type = issue.split(':')[0]
            if issue_type not in issue_types:
                issue_types[issue_type] = []
            issue_types[issue_type].append(row['rowid'])
    
    print(f"\nCorruption by type:")
    for issue_type, rowids in issue_types.items():
        print(f"  {issue_type}: {len(rowids)} rows")
    
    # Show sample corrupted rows
    print(f"\nSample corrupted rows (first 10):")
    for i, row in enumerate(result['corrupted_rows'][:10]):
        print(f"  Row {row['rowid']}: {', '.join(row['issues'])}")
        if isinstance(row['bank_id'], bytes):
            print(f"    bank_id (hex): {row['bank_id'].hex()[:50]}...")
        else:
            print(f"    bank_id: {repr(row['bank_id'])}")
        print(f"    power: {repr(row['power'])}, cell: {repr(row['cell'])}, ts: {row['ts']}")
    
    if len(result['corrupted_rows']) > 10:
        print(f"  ... and {len(result['corrupted_rows']) - 10} more")
    
    # Delete if requested
    if args.delete:
        print(f"\n{'=' * 80}")
        print("DELETING CORRUPTED ROWS")
        print("=" * 80)
        
        corrupted_rowids = [row['rowid'] for row in result['corrupted_rows']]
        deleted_count = delete_corrupted_rows(
            args.db_path,
            corrupted_rowids,
            backup=not args.no_backup
        )
        
        print(f"\n✓ Deleted {deleted_count} corrupted rows")
        print(f"✓ Valid rows remaining: {result['valid_rows']}")
    else:
        print(f"\n{'=' * 80}")
        print("DRY-RUN COMPLETE")
        print("=" * 80)
        print("No changes were made. Use --delete to actually remove corrupted rows.")
        print("A backup will be created automatically unless --no-backup is specified.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

