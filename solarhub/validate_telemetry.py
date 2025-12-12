"""
Validation script to check telemetry table data integrity.
Checks if all expected tables are being populated with data.
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

log = logging.getLogger(__name__)


class TelemetryValidator:
    """Validates telemetry data in the database."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
    
    def validate_all(self) -> Dict[str, Any]:
        """Run all validation checks."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "database_path": self.db_path,
            "checks": {}
        }
        
        # Check table existence
        results["checks"]["table_existence"] = self.check_table_existence()
        
        # Check inverter telemetry
        results["checks"]["inverter_telemetry"] = self.check_inverter_telemetry()
        
        # Check battery telemetry
        results["checks"]["battery_telemetry"] = self.check_battery_telemetry()
        
        # Check meter telemetry
        results["checks"]["meter_telemetry"] = self.check_meter_telemetry()
        
        # Check hourly energy aggregation
        results["checks"]["hourly_energy"] = self.check_hourly_energy()
        
        # Check daily energy aggregation
        results["checks"]["daily_energy"] = self.check_daily_energy()
        
        # Check battery cells data (hierarchy definition)
        results["checks"]["battery_cells"] = self.check_battery_cells()
        
        # Check battery unit samples
        results["checks"]["battery_units"] = self.check_battery_units()
        
        # Check battery cell samples
        results["checks"]["battery_cell_samples"] = self.check_battery_cell_samples()
        
        # Check complete hierarchy data
        results["checks"]["hierarchy_data"] = self.check_hierarchy_data()
        
        # Check recent data (last 24 hours)
        results["checks"]["recent_data"] = self.check_recent_data()
        
        # Summary
        results["summary"] = self.generate_summary(results["checks"])
        
        return results
    
    def check_table_existence(self) -> Dict[str, Any]:
        """Check if all expected telemetry tables exist."""
        expected_tables = [
            "energy_samples",  # Inverter telemetry
            "battery_bank_samples",  # Battery pack telemetry
            "meter_samples",  # Meter telemetry
            "battery_cells",  # Battery cell data
            "hourly_energy",  # Aggregated hourly energy
            "array_hourly_energy",  # Array-level hourly energy
            "system_hourly_energy",  # System-level hourly energy
            "battery_bank_hourly",  # Battery pack hourly energy
            "meter_hourly_energy",  # Meter hourly energy
            "daily_summary",  # Inverter daily energy summaries
            "array_daily_summary",  # Array-level daily energy
            "system_daily_summary",  # System-level daily energy
            "battery_bank_daily",  # Battery pack daily energy
            "meter_daily",  # Meter daily energy
        ]
        
        self.cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in self.cur.fetchall()}
        
        missing_tables = [t for t in expected_tables if t not in existing_tables]
        extra_tables = existing_tables - set(expected_tables)
        
        return {
            "status": "ok" if not missing_tables else "error",
            "expected_tables": expected_tables,
            "existing_tables": list(existing_tables),
            "missing_tables": missing_tables,
            "extra_tables": list(extra_tables),
        }
    
    def check_inverter_telemetry(self) -> Dict[str, Any]:
        """Check inverter telemetry data."""
        try:
            # Get all inverters from hierarchy
            self.cur.execute("SELECT DISTINCT inverter_id FROM inverters")
            expected_inverters = [row[0] for row in self.cur.fetchall()]
            
            # Check energy_samples table
            self.cur.execute("SELECT DISTINCT inverter_id FROM energy_samples")
            inverters_with_data = [row[0] for row in self.cur.fetchall()]
            
            missing_inverters = [inv for inv in expected_inverters if inv not in inverters_with_data]
            
            # Get sample counts
            sample_counts = {}
            for inv_id in expected_inverters:
                self.cur.execute(
                    "SELECT COUNT(*) FROM energy_samples WHERE inverter_id = ?",
                    (inv_id,)
                )
                sample_counts[inv_id] = self.cur.fetchone()[0]
            
            # Get latest sample timestamp
            latest_samples = {}
            for inv_id in expected_inverters:
                self.cur.execute(
                    "SELECT MAX(ts) FROM energy_samples WHERE inverter_id = ?",
                    (inv_id,)
                )
                result = self.cur.fetchone()[0]
                latest_samples[inv_id] = result
            
            return {
                "status": "ok" if not missing_inverters else "warning",
                "expected_inverters": expected_inverters,
                "inverters_with_data": inverters_with_data,
                "missing_inverters": missing_inverters,
                "sample_counts": sample_counts,
                "latest_samples": latest_samples,
            }
        except sqlite3.OperationalError as e:
            return {
                "status": "error",
                "error": str(e),
            }
    
    def check_battery_telemetry(self) -> Dict[str, Any]:
        """Check battery pack telemetry data."""
        try:
            # Get all battery packs from hierarchy
            self.cur.execute("SELECT DISTINCT pack_id FROM battery_packs")
            expected_packs = [row[0] for row in self.cur.fetchall()]
            
            # Check battery_bank_samples table
            self.cur.execute("SELECT DISTINCT bank_id FROM battery_bank_samples")
            packs_with_data = [row[0] for row in self.cur.fetchall()]
            
            missing_packs = [pack for pack in expected_packs if pack not in packs_with_data]
            
            # Get sample counts
            sample_counts = {}
            for pack_id in expected_packs:
                self.cur.execute(
                    "SELECT COUNT(*) FROM battery_bank_samples WHERE bank_id = ?",
                    (pack_id,)
                )
                sample_counts[pack_id] = self.cur.fetchone()[0]
            
            # Get latest sample timestamp
            latest_samples = {}
            for pack_id in expected_packs:
                self.cur.execute(
                    "SELECT MAX(ts) FROM battery_bank_samples WHERE bank_id = ?",
                    (pack_id,)
                )
                result = self.cur.fetchone()[0]
                latest_samples[pack_id] = result
            
            return {
                "status": "ok" if not missing_packs else "warning",
                "expected_packs": expected_packs,
                "packs_with_data": packs_with_data,
                "missing_packs": missing_packs,
                "sample_counts": sample_counts,
                "latest_samples": latest_samples,
            }
        except sqlite3.OperationalError as e:
            return {
                "status": "error",
                "error": str(e),
            }
    
    def check_meter_telemetry(self) -> Dict[str, Any]:
        """Check meter telemetry data."""
        try:
            # Get all meters from hierarchy
            self.cur.execute("SELECT DISTINCT meter_id FROM meters")
            expected_meters = [row[0] for row in self.cur.fetchall()]
            
            # Check meter_samples table
            self.cur.execute("SELECT DISTINCT meter_id FROM meter_samples")
            meters_with_data = [row[0] for row in self.cur.fetchall()]
            
            missing_meters = [meter for meter in expected_meters if meter not in meters_with_data]
            
            # Get sample counts
            sample_counts = {}
            for meter_id in expected_meters:
                self.cur.execute(
                    "SELECT COUNT(*) FROM meter_samples WHERE meter_id = ?",
                    (meter_id,)
                )
                sample_counts[meter_id] = self.cur.fetchone()[0]
            
            # Get latest sample timestamp
            latest_samples = {}
            for meter_id in expected_meters:
                self.cur.execute(
                    "SELECT MAX(ts) FROM meter_samples WHERE meter_id = ?",
                    (meter_id,)
                )
                result = self.cur.fetchone()[0]
                latest_samples[meter_id] = result
            
            return {
                "status": "ok" if not missing_meters else "warning",
                "expected_meters": expected_meters,
                "meters_with_data": meters_with_data,
                "missing_meters": missing_meters,
                "sample_counts": sample_counts,
                "latest_samples": latest_samples,
            }
        except sqlite3.OperationalError as e:
            return {
                "status": "error",
                "error": str(e),
            }
    
    def check_hourly_energy(self) -> Dict[str, Any]:
        """Check hourly energy aggregation."""
        try:
            # Check inverter hourly energy
            self.cur.execute("SELECT COUNT(DISTINCT inverter_id) FROM hourly_energy")
            inverter_count = self.cur.fetchone()[0]
            
            # Check array hourly energy
            self.cur.execute("SELECT COUNT(DISTINCT array_id) FROM array_hourly_energy")
            array_count = self.cur.fetchone()[0]
            
            # Check system hourly energy
            self.cur.execute("SELECT COUNT(DISTINCT system_id) FROM system_hourly_energy")
            system_count = self.cur.fetchone()[0]
            
            # Check battery pack hourly energy
            self.cur.execute("SELECT COUNT(DISTINCT pack_id) FROM battery_bank_hourly")
            battery_count = self.cur.fetchone()[0]
            
            # Check meter hourly energy
            self.cur.execute("SELECT COUNT(DISTINCT meter_id) FROM meter_hourly_energy")
            meter_count = self.cur.fetchone()[0]
            
            # Get latest hourly records
            latest_hourly = {}
            for table in ["hourly_energy", "array_hourly_energy", "system_hourly_energy", "battery_bank_hourly", "meter_hourly_energy"]:
                try:
                    self.cur.execute(f"SELECT MAX(date || ' ' || hour) FROM {table}")
                    result = self.cur.fetchone()[0]
                    latest_hourly[table] = result
                except sqlite3.OperationalError:
                    latest_hourly[table] = None
            
            return {
                "status": "ok",
                "inverter_hourly_count": inverter_count,
                "array_hourly_count": array_count,
                "system_hourly_count": system_count,
                "battery_hourly_count": battery_count,
                "meter_hourly_count": meter_count,
                "latest_hourly_records": latest_hourly,
            }
        except sqlite3.OperationalError as e:
            return {
                "status": "error",
                "error": str(e),
            }
    
    def check_daily_energy(self) -> Dict[str, Any]:
        """Check daily energy aggregation."""
        try:
            # Check daily energy tables (using actual table names from schema)
            daily_tables = ["daily_summary", "array_daily_summary", "system_daily_summary", "battery_bank_daily", "meter_daily"]
            daily_counts = {}
            latest_daily = {}
            
            for table in daily_tables:
                try:
                    self.cur.execute(f"SELECT COUNT(*) FROM {table}")
                    daily_counts[table] = self.cur.fetchone()[0]
                    
                    self.cur.execute(f"SELECT MAX(date) FROM {table}")
                    result = self.cur.fetchone()[0]
                    latest_daily[table] = result
                except sqlite3.OperationalError:
                    daily_counts[table] = 0
                    latest_daily[table] = None
            
            return {
                "status": "ok",
                "daily_record_counts": daily_counts,
                "latest_daily_records": latest_daily,
            }
        except sqlite3.OperationalError as e:
            return {
                "status": "error",
                "error": str(e),
            }
    
    def check_battery_cells(self) -> Dict[str, Any]:
        """Check battery cell data."""
        try:
            # Get all batteries from hierarchy
            self.cur.execute("""
                SELECT DISTINCT b.battery_id, bp.pack_id
                FROM batteries b
                JOIN battery_packs bp ON b.pack_id = bp.pack_id
            """)
            expected_batteries = [(row[0], row[1]) for row in self.cur.fetchall()]
            
            # Check battery_cells table
            self.cur.execute("SELECT DISTINCT battery_id FROM battery_cells")
            batteries_with_cells = [row[0] for row in self.cur.fetchall()]
            
            missing_batteries = [b[0] for b in expected_batteries if b[0] not in batteries_with_cells]
            
            # Get cell counts per battery
            cell_counts = {}
            for battery_id, pack_id in expected_batteries:
                self.cur.execute(
                    "SELECT COUNT(DISTINCT cell_index) FROM battery_cells WHERE battery_id = ?",
                    (battery_id,)
                )
                cell_counts[battery_id] = self.cur.fetchone()[0]
            
            return {
                "status": "ok" if not missing_batteries else "warning",
                "expected_batteries": [b[0] for b in expected_batteries],
                "batteries_with_cells": batteries_with_cells,
                "missing_batteries": missing_batteries,
                "cell_counts": cell_counts,
            }
        except sqlite3.OperationalError as e:
            return {
                "status": "error",
                "error": str(e),
            }
    
    def check_recent_data(self, hours: int = 24) -> Dict[str, Any]:
        """Check if data exists in the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff_time.strftime("%Y-%m-%d %H:%M:%S")
        
        recent_data = {}
        
        # Check recent inverter samples
        try:
            self.cur.execute(
                "SELECT COUNT(*) FROM energy_samples WHERE ts >= ?",
                (cutoff_str,)
            )
            recent_data["inverter_samples"] = self.cur.fetchone()[0]
        except sqlite3.OperationalError:
            recent_data["inverter_samples"] = 0
        
        # Check recent battery samples
        try:
            self.cur.execute(
                "SELECT COUNT(*) FROM battery_bank_samples WHERE ts >= ?",
                (cutoff_str,)
            )
            recent_data["battery_samples"] = self.cur.fetchone()[0]
        except sqlite3.OperationalError:
            recent_data["battery_samples"] = 0
        
        # Check recent meter samples
        try:
            self.cur.execute(
                "SELECT COUNT(*) FROM meter_samples WHERE ts >= ?",
                (cutoff_str,)
            )
            recent_data["meter_samples"] = self.cur.fetchone()[0]
        except sqlite3.OperationalError:
            recent_data["meter_samples"] = 0
        
        # Check recent battery unit samples
        try:
            self.cur.execute(
                "SELECT COUNT(*) FROM battery_unit_samples WHERE ts >= ?",
                (cutoff_str,)
            )
            recent_data["battery_unit_samples"] = self.cur.fetchone()[0]
        except sqlite3.OperationalError:
            recent_data["battery_unit_samples"] = 0
        
        # Check recent battery cell samples
        try:
            self.cur.execute(
                "SELECT COUNT(*) FROM battery_cell_samples WHERE ts >= ?",
                (cutoff_str,)
            )
            recent_data["battery_cell_samples"] = self.cur.fetchone()[0]
        except sqlite3.OperationalError:
            recent_data["battery_cell_samples"] = 0
        
        return {
            "status": "ok",
            "hours_checked": hours,
            "cutoff_time": cutoff_str,
            "recent_sample_counts": recent_data,
        }
    
    def generate_summary(self, checks: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of validation results."""
        issues = []
        warnings = []
        
        # Check table existence
        if checks.get("table_existence", {}).get("status") == "error":
            issues.append(f"Missing tables: {checks['table_existence'].get('missing_tables', [])}")
        
        # Check inverter telemetry
        inv_check = checks.get("inverter_telemetry", {})
        if inv_check.get("status") == "error":
            issues.append(f"Inverter telemetry check failed: {inv_check.get('error')}")
        elif inv_check.get("missing_inverters"):
            warnings.append(f"Inverters without data: {inv_check.get('missing_inverters')}")
        
        # Check battery telemetry
        bat_check = checks.get("battery_telemetry", {})
        if bat_check.get("status") == "error":
            issues.append(f"Battery telemetry check failed: {bat_check.get('error')}")
        elif bat_check.get("missing_packs"):
            warnings.append(f"Battery packs without data: {bat_check.get('missing_packs')}")
        
        # Check meter telemetry
        meter_check = checks.get("meter_telemetry", {})
        if meter_check.get("status") == "error":
            issues.append(f"Meter telemetry check failed: {meter_check.get('error')}")
        elif meter_check.get("missing_meters"):
            warnings.append(f"Meters without data: {meter_check.get('missing_meters')}")
        
        # Check battery cells
        cells_check = checks.get("battery_cells", {})
        if cells_check.get("status") == "error":
            issues.append(f"Battery cells check failed: {cells_check.get('error')}")
        elif cells_check.get("missing_batteries"):
            warnings.append(f"Batteries without cell data: {cells_check.get('missing_batteries')}")
        
        return {
            "total_issues": len(issues),
            "total_warnings": len(warnings),
            "issues": issues,
            "warnings": warnings,
            "overall_status": "error" if issues else ("warning" if warnings else "ok"),
        }
    
    def close(self):
        """Close database connection."""
        self.conn.close()


def validate_telemetry(db_path: str) -> Dict[str, Any]:
    """Main function to validate telemetry data."""
    validator = TelemetryValidator(db_path)
    try:
        results = validator.validate_all()
        return results
    finally:
        validator.close()


if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python validate_telemetry.py <db_path>")
        sys.exit(1)
    
    db_path = sys.argv[1]
    results = validate_telemetry(db_path)
    print(json.dumps(results, indent=2))

