#!/usr/bin/env python3
"""
Daily data aggregation for solar monitoring system.
Creates daily summaries and handles seasonal learning.
"""

import sqlite3
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import numpy as np

log = logging.getLogger(__name__)

class DailyAggregator:
    """Handles daily data aggregation and seasonal learning."""
    
    def __init__(self, db_path: str, tz: str = "Asia/Karachi"):
        self.db_path = db_path
        self.tz = tz
    
    def create_daily_summary_table(self) -> None:
        """Create daily summary table for aggregated data."""
        con = sqlite3.connect(self.db_path)
        cursor = con.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_summary (
                    date TEXT NOT NULL,
                    inverter_id TEXT NOT NULL,
                    day_of_year INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    -- PV data
                    pv_energy_kwh REAL,
                    pv_max_power_w REAL,
                    pv_avg_power_w REAL,
                    pv_peak_hour INTEGER,
                    -- Load data  
                    load_energy_kwh REAL,
                    load_max_power_w REAL,
                    load_avg_power_w REAL,
                    load_peak_hour INTEGER,
                    -- Battery data
                    battery_min_soc_pct REAL,
                    battery_max_soc_pct REAL,
                    battery_avg_soc_pct REAL,
                    battery_cycles REAL,
                    -- Grid data
                    grid_energy_imported_kwh REAL,
                    grid_energy_exported_kwh REAL,
                    grid_max_import_w REAL,
                    grid_max_export_w REAL,
                    -- Weather correlation
                    weather_factor REAL,
                    -- Metadata
                    sample_count INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (date, inverter_id)
                )
            """)
            
            # Create indexes for efficient queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_daily_summary_doy 
                ON daily_summary(day_of_year, inverter_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_daily_summary_date 
                ON daily_summary(date DESC, inverter_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_daily_summary_year_doy 
                ON daily_summary(year, day_of_year, inverter_id)
            """)
            
            con.commit()
            log.info("Daily summary table created successfully")
            
        except Exception as e:
            log.error(f"Failed to create daily summary table: {e}")
            con.rollback()
        finally:
            con.close()
    
    def aggregate_daily_data(self, date: str, inverter_id: str) -> Optional[Dict]:
        """
        Aggregate daily data for a specific date and inverter.
        
        Args:
            date: Date in YYYY-MM-DD format
            inverter_id: Inverter identifier
            
        Returns:
            Dictionary with aggregated daily data or None if no data
        """
        con = sqlite3.connect(self.db_path)
        
        try:
            # Get all data for the specific date and inverter
            query = """
                SELECT ts, pv_power_w, load_power_w, battery_soc, 
                       grid_power_w, battery_voltage_v, battery_current_a
                FROM energy_samples 
                WHERE DATE(ts) = ? AND inverter_id = ?
                ORDER BY ts
            """
            
            df = pd.read_sql_query(query, con, params=[date, inverter_id])
            
            if df.empty:
                return None
            
            # Convert timestamps stored as ISO strings (configured timezone, e.g., +05:00)
            # Prefer robust ISO8601 parsing and preserve original tz offsets
            df['ts'] = pd.to_datetime(df['ts'], format='ISO8601', errors='coerce')
            # Fallback parsing if any failed
            if df['ts'].isna().any():
                df.loc[df['ts'].isna(), 'ts'] = pd.to_datetime(df.loc[df['ts'].isna(), 'ts'], errors='coerce')
            # If any entries are still naive, assume configured timezone
            if df['ts'].dt.tz is None:
                try:
                    from solarhub.timezone_utils import get_configured_timezone
                    df['ts'] = df['ts'].dt.tz_localize(get_configured_timezone())
                except Exception:
                    df['ts'] = df['ts'].dt.tz_localize(None)
            df['hour'] = df['ts'].dt.hour
            
            # Calculate daily aggregations
            summary = {
                'date': date,
                'inverter_id': inverter_id,
                'day_of_year': pd.Timestamp(date).dayofyear,
                'year': pd.Timestamp(date).year,
                'sample_count': len(df)
            }
            
            # PV aggregations
            pv_data = df['pv_power_w'].dropna()
            if not pv_data.empty:
                summary['pv_energy_kwh'] = float(pv_data.sum() / 1000.0)  # Convert W to kW, then to kWh (assuming 2-second intervals)
                summary['pv_max_power_w'] = float(pv_data.max())
                summary['pv_avg_power_w'] = float(pv_data.mean())
                # Find peak hour
                hourly_pv = df.groupby('hour')['pv_power_w'].mean()
                summary['pv_peak_hour'] = int(hourly_pv.idxmax()) if not hourly_pv.empty else None
            
            # Load aggregations
            load_data = df['load_power_w'].dropna()
            if not load_data.empty:
                summary['load_energy_kwh'] = float(load_data.sum() / 1000.0)
                summary['load_max_power_w'] = float(load_data.max())
                summary['load_avg_power_w'] = float(load_data.mean())
                # Find peak hour
                hourly_load = df.groupby('hour')['load_power_w'].mean()
                summary['load_peak_hour'] = int(hourly_load.idxmax()) if not hourly_load.empty else None
            
            # Battery aggregations
            soc_data = df['battery_soc'].dropna()
            if not soc_data.empty:
                summary['battery_min_soc_pct'] = float(soc_data.min())
                summary['battery_max_soc_pct'] = float(soc_data.max())
                summary['battery_avg_soc_pct'] = float(soc_data.mean())
                # Estimate cycles (rough calculation)
                soc_changes = soc_data.diff().abs().sum()
                summary['battery_cycles'] = float(soc_changes / 200.0)  # Rough estimate
            
            # Grid aggregations
            grid_data = df['grid_power_w'].dropna()
            if not grid_data.empty:
                # Separate import (positive) and export (negative)
                import_data = grid_data[grid_data > 0]
                export_data = grid_data[grid_data < 0]
                
                summary['grid_energy_imported_kwh'] = float(import_data.sum() / 1000.0) if not import_data.empty else 0.0
                summary['grid_energy_exported_kwh'] = float(abs(export_data.sum()) / 1000.0) if not export_data.empty else 0.0
                summary['grid_max_import_w'] = float(import_data.max()) if not import_data.empty else 0.0
                summary['grid_max_export_w'] = float(abs(export_data.min())) if not export_data.empty else 0.0
            
            # Weather factor (placeholder - could be enhanced with actual weather data)
            summary['weather_factor'] = 1.0  # Default, could be calculated from weather correlation
            
            return summary
            
        except Exception as e:
            log.error(f"Failed to aggregate daily data for {date}, {inverter_id}: {e}")
            return None
        finally:
            con.close()
    
    def store_daily_summary(self, summary: Dict) -> bool:
        """Store daily summary in database."""
        con = sqlite3.connect(self.db_path)
        cursor = con.cursor()
        
        try:
            # Insert or replace daily summary
            cursor.execute("""
                INSERT OR REPLACE INTO daily_summary 
                (date, inverter_id, day_of_year, year, pv_energy_kwh, pv_max_power_w, pv_avg_power_w, pv_peak_hour,
                 load_energy_kwh, load_max_power_w, load_avg_power_w, load_peak_hour,
                 battery_min_soc_pct, battery_max_soc_pct, battery_avg_soc_pct, battery_cycles,
                 grid_energy_imported_kwh, grid_energy_exported_kwh, grid_max_import_w, grid_max_export_w,
                 weather_factor, sample_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                summary['date'], summary['inverter_id'], summary['day_of_year'], summary['year'],
                summary.get('pv_energy_kwh'), summary.get('pv_max_power_w'), summary.get('pv_avg_power_w'), summary.get('pv_peak_hour'),
                summary.get('load_energy_kwh'), summary.get('load_max_power_w'), summary.get('load_avg_power_w'), summary.get('load_peak_hour'),
                summary.get('battery_min_soc_pct'), summary.get('battery_max_soc_pct'), summary.get('battery_avg_soc_pct'), summary.get('battery_cycles'),
                summary.get('grid_energy_imported_kwh'), summary.get('grid_energy_exported_kwh'), summary.get('grid_max_import_w'), summary.get('grid_max_export_w'),
                summary.get('weather_factor'), summary.get('sample_count')
            ))
            
            con.commit()
            return True
            
        except Exception as e:
            log.error(f"Failed to store daily summary: {e}")
            con.rollback()
            return False
        finally:
            con.close()
    
    def get_seasonal_data(self, day_of_year: int, inverter_id: str, years_back: int = 3) -> List[Dict]:
        """
        Get seasonal data for the same day-of-year from previous years.
        
        Args:
            day_of_year: Day of year (1-366)
            inverter_id: Inverter identifier
            years_back: Number of years to look back
            
        Returns:
            List of daily summaries for the same day-of-year
        """
        con = sqlite3.connect(self.db_path)
        
        try:
            # Get data for the same day-of-year from previous years
            from solarhub.timezone_utils import now_configured
            current_year = now_configured().year
            year_range = list(range(current_year - years_back, current_year))
            
            placeholders = ','.join(['?' for _ in year_range])
            query = f"""
                SELECT * FROM daily_summary 
                WHERE day_of_year = ? AND inverter_id = ? AND year IN ({placeholders})
                ORDER BY year DESC
            """
            
            params = [day_of_year, inverter_id] + year_range
            df = pd.read_sql_query(query, con, params=params)
            
            return df.to_dict('records') if not df.empty else []
            
        except Exception as e:
            log.error(f"Failed to get seasonal data: {e}")
            return []
        finally:
            con.close()
    
    def get_recent_data(self, inverter_id: str, days_back: int = 60) -> List[Dict]:
        """
        Get recent daily summaries.
        
        Args:
            inverter_id: Inverter identifier
            days_back: Number of recent days to retrieve
            
        Returns:
            List of recent daily summaries
        """
        con = sqlite3.connect(self.db_path)
        
        try:
            from solarhub.timezone_utils import now_configured
            cutoff_date = (now_configured() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            query = """
                SELECT * FROM daily_summary 
                WHERE inverter_id = ? AND date >= ?
                ORDER BY date DESC
            """
            
            df = pd.read_sql_query(query, con, params=[inverter_id, cutoff_date])
            return df.to_dict('records') if not df.empty else []
            
        except Exception as e:
            log.error(f"Failed to get recent data: {e}")
            return []
        finally:
            con.close()
    
    def process_missing_days(self, inverter_id: str, days_back: int = 7) -> int:
        """
        Process and aggregate any missing daily summaries.
        
        Args:
            inverter_id: Inverter identifier
            days_back: Number of days to check for missing summaries
            
        Returns:
            Number of days processed
        """
        processed = 0
        
        for i in range(days_back):
            from solarhub.timezone_utils import now_configured
            date = (now_configured() - timedelta(days=i)).strftime('%Y-%m-%d')
            
            # Check if summary already exists
            con = sqlite3.connect(self.db_path)
            cursor = con.cursor()
            
            try:
                cursor.execute("""
                    SELECT COUNT(*) FROM daily_summary 
                    WHERE date = ? AND inverter_id = ?
                """, (date, inverter_id))
                
                if cursor.fetchone()[0] == 0:
                    # Missing summary, create it
                    summary = self.aggregate_daily_data(date, inverter_id)
                    if summary:
                        if self.store_daily_summary(summary):
                            processed += 1
                            log.info(f"Processed missing daily summary for {date}, {inverter_id}")
                
            finally:
                con.close()
        
        return processed

def initialize_daily_aggregation(db_path: str, tz: str = "Asia/Karachi") -> DailyAggregator:
    """Initialize daily aggregation system."""
    aggregator = DailyAggregator(db_path, tz)
    aggregator.create_daily_summary_table()
    return aggregator

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
        aggregator = initialize_daily_aggregation(db_path)
        
        # Process missing days for all inverters
        # This would need to be adapted based on your inverter configuration
        print("Daily aggregation system initialized")
    else:
        print("Usage: python daily_aggregator.py <db_path>")

