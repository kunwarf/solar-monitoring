#!/usr/bin/env python3
"""
Database Timezone Migration Utility

This script handles two main tasks:
1. Removes timezone columns from all tables (no longer needed since we convert to configured timezone)
2. Converts all existing UTC timestamps in energy_samples.ts column to the configured timezone

Usage:
    python database_timezone_migration.py [--dry-run] [--backup] [--db-path PATH]
    
Options:
    --dry-run    Show what would be done without making changes
    --backup     Create a backup before migration
    --db-path    Path to database file (default: solarhub.db)
"""

import sqlite3
import argparse
import shutil
import os
import sys
from datetime import datetime, timezone
import pytz
import logging

# Add solarhub to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'solarhub'))

# Avoid hard dependency on internal timezone utils to keep this script portable

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

class DatabaseTimezoneMigrator:
    def __init__(self, db_path: str, dry_run: bool = False, create_backup: bool = False):
        self.db_path = db_path
        self.dry_run = dry_run
        self.create_backup = create_backup
        self.configured_tz = None
        
    def initialize_timezone(self):
        """Initialize the configured timezone from config if available, else default to Asia/Karachi."""
        tz_name = None
        
        # Try loading via ConfigurationManager
        try:
            from solarhub.config_manager import ConfigurationManager
            cfg_mgr = ConfigurationManager()
            cfg = cfg_mgr.load_config()
            tz_name = getattr(cfg, 'timezone', None)
        except Exception as e:
            log.info(f"ConfigurationManager not available or failed: {e}")
        
        # Try reading YAML config directly as fallback
        if not tz_name:
            try:
                import yaml
                # Common locations: project config.yaml or ~/.solarhub/config.yaml
                candidate_paths = [
                    os.path.join(os.getcwd(), 'config.yaml'),
                    os.path.expanduser('~/.solarhub/config.yaml')
                ]
                for path in candidate_paths:
                    if os.path.exists(path):
                        with open(path, 'r', encoding='utf-8') as f:
                            data = yaml.safe_load(f) or {}
                            tz_name = data.get('timezone') or data.get('tz')
                            if tz_name:
                                log.info(f"Loaded timezone from {path}: {tz_name}")
                                break
            except Exception as e:
                log.info(f"YAML config read failed: {e}")
        
        # Default
        if not tz_name:
            tz_name = 'Asia/Karachi'
            log.info("Using default timezone: Asia/Karachi")
        
        try:
            self.configured_tz = pytz.timezone(tz_name)
            log.info(f"Configured timezone resolved: {self.configured_tz.zone}")
        except Exception:
            log.warning(f"Invalid timezone '{tz_name}', falling back to Asia/Karachi")
            self.configured_tz = pytz.timezone('Asia/Karachi')
    
    def create_backup_if_needed(self):
        """Create a backup of the database if requested."""
        if not self.create_backup:
            return
            
        if not os.path.exists(self.db_path):
            log.warning(f"Database file {self.db_path} does not exist, skipping backup")
            return
            
        backup_path = f"{self.db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            shutil.copy2(self.db_path, backup_path)
            log.info(f"Database backup created: {backup_path}")
        except Exception as e:
            log.error(f"Failed to create backup: {e}")
            raise
    
    def get_table_schema(self, cursor, table_name):
        """Get the current schema of a table."""
        cursor.execute(f"PRAGMA table_info({table_name})")
        return cursor.fetchall()
    
    def get_all_tables(self, cursor):
        """Get all table names in the database."""
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in cursor.fetchall()]
    
    def has_timezone_column(self, schema):
        """Check if a table has a timezone column."""
        return any(column[1] == 'timezone' for column in schema)

    def _indexes_using_column(self, cursor, table: str, column: str) -> list[str]:
        """Return list of index names on a table that include a given column."""
        try:
            idx_names = []
            cursor.execute(f"PRAGMA index_list('{table}')")
            idx_rows = cursor.fetchall() or []
            for row in idx_rows:
                # row: (seq, name, unique, origin, partial) across versions
                idx_name = row[1]
                cursor.execute(f"PRAGMA index_info('{idx_name}')")
                info_rows = cursor.fetchall() or []
                cols = [r[2] for r in info_rows if len(r) >= 3]
                if column in cols:
                    idx_names.append(idx_name)
            return idx_names
        except Exception:
            return []
    
    def remove_timezone_columns(self, cursor):
        """Remove timezone columns from all tables using ALTER TABLE DROP COLUMN (no table drops)."""
        log.info("=== Removing timezone columns from all tables ===")

        # Detect SQLite version for DROP COLUMN support (>= 3.35.0)
        cursor.execute("SELECT sqlite_version()")
        version_str = cursor.fetchone()[0]
        log.info(f"SQLite version: {version_str}")
        try:
            major, minor, patch = (int(x) for x in version_str.split(".")[:3])
        except Exception:
            major = minor = patch = 0
        supports_drop_column = (major, minor, patch) >= (3, 35, 0)

        if not supports_drop_column:
            log.error("SQLite version does not support ALTER TABLE DROP COLUMN. Please upgrade SQLite to >= 3.35.0 or run a manual migration. Skipping timezone column removal.")
            return

        tables = self.get_all_tables(cursor)
        tables_to_modify = []

        # Find tables that have timezone columns
        for table in tables:
            schema = self.get_table_schema(cursor, table)
            if self.has_timezone_column(schema):
                tables_to_modify.append(table)
                log.info(f"Table '{table}' has timezone column - will be removed")

        if not tables_to_modify:
            log.info("No tables found with timezone columns")
            return

        for table in tables_to_modify:
            log.info(f"Removing timezone column from table '{table}' using ALTER TABLE DROP COLUMN")

            if self.dry_run:
                log.info(f"[DRY RUN] Would run: ALTER TABLE {table} DROP COLUMN timezone")
                continue

            try:
                # Drop dependent indexes first (those using timezone column)
                idx_to_drop = self._indexes_using_column(cursor, table, 'timezone')
                for idx in idx_to_drop:
                    log.info(f"Dropping index '{idx}' on {table} (references timezone)")
                    cursor.execute(f"DROP INDEX IF EXISTS '{idx}'")

                # Now drop the column
                cursor.execute(f"ALTER TABLE {table} DROP COLUMN timezone")
                log.info(f"Successfully removed timezone column from {table}")
            except Exception as e:
                log.error(f"Failed to remove timezone column from {table}: {e}")
                raise
    
    def convert_utc_timestamps_to_configured(self, cursor):
        """Convert all UTC timestamps in energy_samples.ts to configured timezone."""
        log.info("=== Converting UTC timestamps to configured timezone ===")
        
        # Check if energy_samples table exists
        tables = self.get_all_tables(cursor)
        if 'energy_samples' not in tables:
            log.warning("energy_samples table not found, skipping timestamp conversion")
            return
        
        # Get count of records to convert
        cursor.execute("SELECT COUNT(*) FROM energy_samples WHERE ts IS NOT NULL")
        total_records = cursor.fetchone()[0]
        
        if total_records == 0:
            log.info("No records found in energy_samples table")
            return
        
        log.info(f"Found {total_records} records to convert")
        
        # Process in batches to avoid memory issues
        batch_size = 1000
        processed = 0
        errors = 0
        
        while processed < total_records:
            # Get batch of records
            cursor.execute("""
                SELECT rowid, ts 
                FROM energy_samples 
                WHERE ts IS NOT NULL 
                ORDER BY rowid 
                LIMIT ? OFFSET ?
            """, (batch_size, processed))
            
            batch = cursor.fetchall()
            if not batch:
                break
            
            log.info(f"Processing batch {processed//batch_size + 1}: records {processed + 1} to {processed + len(batch)}")
            
            # Convert timestamps in this batch
            updates = []
            for rowid, ts_str in batch:
                try:
                    # Parse the timestamp string
                    if 'T' in ts_str and ('Z' in ts_str or '+' in ts_str or ts_str.endswith('00:00')):
                        # ISO format with timezone info
                        if ts_str.endswith('Z'):
                            ts_str = ts_str[:-1] + '+00:00'
                        dt_utc = datetime.fromisoformat(ts_str)
                    else:
                        # Assume UTC if no timezone info
                        dt_utc = datetime.fromisoformat(ts_str)
                        if dt_utc.tzinfo is None:
                            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                    
                    # Convert to configured timezone
                    if dt_utc.tzinfo != self.configured_tz:
                        dt_configured = dt_utc.astimezone(self.configured_tz)
                    else:
                        dt_configured = dt_utc
                    
                    # Format as ISO string
                    new_ts = dt_configured.isoformat()
                    updates.append((new_ts, rowid))
                    
                except Exception as e:
                    log.error(f"Error converting timestamp '{ts_str}' for rowid {rowid}: {e}")
                    errors += 1
                    continue
            
            # Update the batch
            if updates and not self.dry_run:
                cursor.executemany("UPDATE energy_samples SET ts = ? WHERE rowid = ?", updates)
            
            if self.dry_run:
                log.info(f"[DRY RUN] Would update {len(updates)} records in this batch")
            
            processed += len(batch)
        
        if errors > 0:
            log.warning(f"Encountered {errors} errors during conversion")
        
        log.info(f"Timestamp conversion completed. Processed: {processed}, Errors: {errors}")
    
    def verify_migration(self, cursor):
        """Verify that the migration was successful."""
        log.info("=== Verifying migration ===")
        
        # Check that no tables have timezone columns
        tables = self.get_all_tables(cursor)
        for table in tables:
            schema = self.get_table_schema(cursor, table)
            if self.has_timezone_column(schema):
                log.error(f"Table '{table}' still has timezone column!")
                return False
        
        log.info("✓ No tables have timezone columns")
        
        # Check energy_samples timestamps
        if 'energy_samples' in tables:
            cursor.execute("SELECT ts FROM energy_samples WHERE ts IS NOT NULL LIMIT 5")
            sample_timestamps = cursor.fetchall()
            
            log.info("Sample timestamps after conversion:")
            for ts_str, in sample_timestamps:
                try:
                    dt = datetime.fromisoformat(ts_str)
                    log.info(f"  {ts_str} (timezone: {dt.tzinfo})")
                except Exception as e:
                    log.error(f"  {ts_str} - Error parsing: {e}")
        
        log.info("✓ Migration verification completed")
        return True
    
    def run_migration(self):
        """Run the complete migration process."""
        log.info("Starting database timezone migration...")
        log.info(f"Database path: {self.db_path}")
        log.info(f"Dry run: {self.dry_run}")
        log.info(f"Create backup: {self.create_backup}")
        
        # Initialize timezone
        self.initialize_timezone()
        
        # Create backup if requested
        if not self.dry_run:
            self.create_backup_if_needed()
        
        # Connect to database
        if not os.path.exists(self.db_path):
            log.error(f"Database file {self.db_path} does not exist!")
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Start transaction
            cursor.execute("BEGIN TRANSACTION")
            
            try:
                # Step 1: Remove timezone columns
                self.remove_timezone_columns(cursor)
                
                # Step 2: Convert UTC timestamps to configured timezone
                self.convert_utc_timestamps_to_configured(cursor)
                
                # Commit transaction
                if not self.dry_run:
                    cursor.execute("COMMIT")
                    log.info("Migration completed successfully!")
                else:
                    cursor.execute("ROLLBACK")
                    log.info("Dry run completed - no changes made")
                
                # Verify migration
                if not self.dry_run:
                    self.verify_migration(cursor)
                
            except Exception as e:
                cursor.execute("ROLLBACK")
                log.error(f"Migration failed, rolling back: {e}")
                raise
            
        except Exception as e:
            log.error(f"Database error: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
        
        return True

def main():
    parser = argparse.ArgumentParser(description='Database timezone migration utility')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without making changes')
    parser.add_argument('--backup', action='store_true',
                       help='Create a backup before migration')
    # Default DB path points to server location ~/.solarhub/solarhub.db
    default_db_path = os.path.expanduser('~/.solarhub/solarhub.db')
    parser.add_argument('--db-path', default=default_db_path,
                       help=f'Path to database file (default: {default_db_path})')
    
    args = parser.parse_args()
    
    migrator = DatabaseTimezoneMigrator(
        db_path=args.db_path,
        dry_run=args.dry_run,
        create_backup=args.backup
    )
    
    success = migrator.run_migration()
    
    if success:
        log.info("Migration completed successfully!")
        sys.exit(0)
    else:
        log.error("Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
