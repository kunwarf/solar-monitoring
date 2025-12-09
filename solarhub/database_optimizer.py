#!/usr/bin/env python3
"""
Database optimization utilities for solar monitoring system.
Creates indexes and provides data retention management.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional

log = logging.getLogger(__name__)

class DatabaseOptimizer:
    """Handles database optimization and maintenance tasks."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def create_indexes(self) -> None:
        """Create database indexes for optimal query performance."""
        con = sqlite3.connect(self.db_path)
        cursor = con.cursor()
        
        try:
            # Index for BiasLearner queries (inverter_id + timestamp)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_energy_samples_inverter_ts 
                ON energy_samples(inverter_id, ts DESC)
            """)
            
            # Index for LoadLearner queries (timestamp)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_energy_samples_ts 
                ON energy_samples(ts DESC)
            """)
            
            # Index for general timestamp queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_energy_samples_timestamp 
                ON energy_samples(ts)
            """)
            
            con.commit()
            log.info("Database indexes created successfully")
            
        except Exception as e:
            log.error(f"Failed to create database indexes: {e}")
            con.rollback()
        finally:
            con.close()
    
    def cleanup_old_data(self, days_to_keep: int = 365) -> int:
        """
        Remove old data to prevent database from growing indefinitely.
        
        Args:
            days_to_keep: Number of days of data to retain (default: 1 year)
            
        Returns:
            Number of records deleted
        """
        con = sqlite3.connect(self.db_path)
        cursor = con.cursor()
        
        try:
            # Calculate cutoff date
            from solarhub.timezone_utils import now_configured
            cutoff_date = (now_configured() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d %H:%M:%S')
            
            # Count records to be deleted
            cursor.execute("SELECT COUNT(*) FROM energy_samples WHERE ts < ?", (cutoff_date,))
            count_to_delete = cursor.fetchone()[0]
            
            if count_to_delete > 0:
                # Delete old records
                cursor.execute("DELETE FROM energy_samples WHERE ts < ?", (cutoff_date,))
                con.commit()
                log.info(f"Cleaned up {count_to_delete} old records (older than {days_to_keep} days)")
                
                # Vacuum database to reclaim space
                cursor.execute("VACUUM")
                con.commit()
                log.info("Database vacuumed to reclaim space")
            
            return count_to_delete
            
        except Exception as e:
            log.error(f"Failed to cleanup old data: {e}")
            con.rollback()
            return 0
        finally:
            con.close()
    
    def get_database_stats(self) -> dict:
        """Get database statistics for monitoring."""
        con = sqlite3.connect(self.db_path)
        cursor = con.cursor()
        
        try:
            # Total records
            cursor.execute("SELECT COUNT(*) FROM energy_samples")
            total_records = cursor.fetchone()[0]
            
            # Date range
            cursor.execute("SELECT MIN(ts), MAX(ts) FROM energy_samples")
            min_ts, max_ts = cursor.fetchone()
            
            # Database size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size_bytes = cursor.fetchone()[0]
            
            return {
                "total_records": total_records,
                "oldest_record": min_ts,
                "newest_record": max_ts,
                "database_size_mb": round(db_size_bytes / (1024 * 1024), 2)
            }
            
        except Exception as e:
            log.error(f"Failed to get database stats: {e}")
            return {}
        finally:
            con.close()
    
    def optimize_database(self) -> None:
        """Run full database optimization."""
        log.info("Starting database optimization...")
        
        # Create indexes
        self.create_indexes()
        
        # Get stats before cleanup
        stats_before = self.get_database_stats()
        log.info(f"Database stats before cleanup: {stats_before}")
        
        # Cleanup old data (keep 1 year)
        deleted_count = self.cleanup_old_data(days_to_keep=365)
        
        # Get stats after cleanup
        stats_after = self.get_database_stats()
        log.info(f"Database stats after cleanup: {stats_after}")
        
        log.info("Database optimization completed")

def optimize_database_if_needed(db_path: str, force: bool = False) -> None:
    """
    Optimize database if it hasn't been done recently or if forced.
    
    Args:
        db_path: Path to the database file
        force: Force optimization even if done recently
    """
    optimizer = DatabaseOptimizer(db_path)
    
    # Check if optimization is needed
    stats = optimizer.get_database_stats()
    total_records = stats.get("total_records", 0)
    
    # Optimize if:
    # - Forced
    # - More than 100k records (indicates significant data)
    # - Database is larger than 50MB
    if (force or 
        total_records > 100000 or 
        stats.get("database_size_mb", 0) > 50):
        
        optimizer.optimize_database()
    else:
        log.info("Database optimization not needed at this time")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
        force = "--force" in sys.argv
        optimize_database_if_needed(db_path, force)
    else:
        print("Usage: python database_optimizer.py <db_path> [--force]")

