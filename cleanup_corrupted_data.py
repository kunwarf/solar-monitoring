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
    encoding_errors = 0
    
    print("Scanning battery_cell_samples table for corrupted data...")
    print(f"Total rows: {total_count}")
    print("This may take a while for large tables...")
    
    # Use rowid to iterate, checking each row individually to handle encoding errors
    # Get min and max rowid first
    try:
        cur.execute("SELECT MIN(rowid), MAX(rowid) FROM battery_cell_samples")
        result = cur.fetchone()
        if result and result[0] is not None:
            min_rowid, max_rowid = result[0], result[1]
        else:
            print("No rows found in table")
            conn.close()
            return {
                "total_rows": 0,
                "valid_rows": 0,
                "corrupted_rows": [],
                "corrupted_count": 0
            }
    except Exception as e:
        print(f"Error getting rowid range: {e}")
        conn.close()
        return {
            "total_rows": total_count,
            "valid_rows": 0,
            "corrupted_rows": [],
            "corrupted_count": 0,
            "error": str(e)
        }
    
    # Process in batches to avoid memory issues
    batch_size = 1000
    processed = 0
    
    for batch_start in range(min_rowid, max_rowid + 1, batch_size):
        batch_end = min(batch_start + batch_size - 1, max_rowid)
        
        # Get rowids in this batch
        try:
            cur.execute(
                "SELECT rowid FROM battery_cell_samples WHERE rowid >= ? AND rowid <= ?",
                (batch_start, batch_end)
            )
            rowids = [row[0] for row in cur.fetchall()]
        except Exception as e:
            print(f"Error getting rowids in batch {batch_start}-{batch_end}: {e}")
            continue
        
        # Check each row individually
        for rowid in rowids:
            try:
                # Try to fetch the row - this will fail if there's an encoding error
                cur.execute(
                    "SELECT ts, bank_id, power, cell, voltage, temperature FROM battery_cell_samples WHERE rowid = ?",
                    (rowid,)
                )
                row = cur.fetchone()
                
                if row is None:
                    continue
                
                ts, bank_id, power, cell, voltage, temp = row
                issues = []
                
                # Check bank_id
                if not is_valid_bank_id(bank_id):
                    issues.append(f"invalid_bank_id")
                
                # Check power
                if not is_valid_power(power):
                    issues.append(f"invalid_power: {repr(power)}")
                
                # Check cell
                if not is_valid_cell(cell):
                    issues.append(f"invalid_cell: {repr(cell)}")
                
                if issues:
                    # Try to get safe representation of values
                    safe_bank_id = repr(bank_id) if not isinstance(bank_id, bytes) else f"<bytes: {len(bank_id)} bytes>"
                    corrupted_rows.append({
                        "rowid": rowid,
                        "ts": str(ts) if ts else None,
                        "bank_id": safe_bank_id,
                        "power": power,
                        "cell": cell,
                        "issues": issues
                    })
                else:
                    valid_rows += 1
                
                processed += 1
                if processed % 10000 == 0:
                    print(f"  Processed {processed}/{total_count} rows... ({len(corrupted_rows)} corrupted found so far)")
                    
            except sqlite3.OperationalError as e:
                # Encoding error - this row is corrupted
                encoding_errors += 1
                try:
                    # Try to at least get the rowid and mark it as corrupted
                    corrupted_rows.append({
                        "rowid": rowid,
                        "ts": None,
                        "bank_id": "<encoding_error>",
                        "power": None,
                        "cell": None,
                        "issues": [f"encoding_error: {str(e)}"]
                    })
                except:
                    # If even that fails, just count it
                    pass
            except Exception as e:
                # Other errors - mark as corrupted
                encoding_errors += 1
                corrupted_rows.append({
                    "rowid": rowid,
                    "ts": None,
                    "bank_id": "<error>",
                    "power": None,
                    "cell": None,
                    "issues": [f"error: {str(e)[:50]}"]
                })
    
    conn.close()
    
    print(f"\nScan complete: {processed} rows processed, {len(corrupted_rows)} corrupted found")
    
    return {
        "total_rows": total_count,
        "valid_rows": valid_rows,
        "corrupted_rows": corrupted_rows,
        "corrupted_count": len(corrupted_rows),
        "encoding_errors": encoding_errors
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

