import threading
import logging
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from solarhub.energy_calculator import EnergyCalculator
from solarhub.billing_engine import (
    simulate_billing_year,
    estimate_capacity_status,
    forecast_next_billing,
)

# Get the main application logger
log = logging.getLogger(__name__)


def _make_json_serializable(obj: Any, visited: Optional[set] = None) -> Any:
    """
    Recursively convert object to JSON-serializable format.
    Handles circular references and non-serializable types.
    
    Args:
        obj: Object to make JSON-serializable
        visited: Set of object IDs already visited (to detect circular references)
    """
    if visited is None:
        visited = set()
    
    # Handle circular references by tracking visited objects
    # Use object ID for mutable types (dict, list), value for immutable types
    if isinstance(obj, (dict, list)):
        obj_id = id(obj)
        if obj_id in visited:
            return "<circular reference>"
        visited.add(obj_id)
    
    try:
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                # Ensure key is string
                key = str(k) if not isinstance(k, str) else k
                result[key] = _make_json_serializable(v, visited.copy())
            return result
        elif isinstance(obj, (list, tuple)):
            return [_make_json_serializable(item, visited.copy()) for item in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            # Try to serialize, fallback to string representation
            try:
                json.dumps(obj)
                return obj
            except (TypeError, ValueError):
                # Non-serializable type - convert to string
                return str(obj)
    finally:
        # Clean up visited set for mutable types
        if isinstance(obj, (dict, list)):
            visited.discard(id(obj))


def _now_iso() -> str:
    from solarhub.timezone_utils import now_configured_iso
    return now_configured_iso()


def create_api(solar_app) -> FastAPI:
    """
    Create a FastAPI app bound to the running SolarApp instance.
    Exposes minimal REST endpoints used by the React UI.
    """
    app = FastAPI(title="SolarHub API")
    
    # Add CORS middleware to allow requests from any origin
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request, call_next):
        log.debug(f"API request: {request.method} {request.url}")
        try:
            response = await call_next(request)
            log.info(f"API response: {response.status_code}")
            return response
        except Exception as e:
            log.error(f"API request failed: {e}", exc_info=True)
            raise

    @app.get("/api/health")
    def api_health() -> Dict[str, Any]:
        """Health check endpoint to test if API server is working."""
        return {"status": "ok", "message": "API server is running", "timestamp": _now_iso()}
    
    @app.get("/api/test")
    def api_test() -> Dict[str, Any]:
        """Test endpoint to verify API server functionality."""
        try:
            return {
                "status": "ok", 
                "solar_app_type": str(type(solar_app)), 
                "has_get_now": hasattr(solar_app, 'get_now'),
                "timestamp": _now_iso()
            }
        except Exception as e:
            log.error(f"Error in test endpoint: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    @app.get("/api/battery/now")
    def api_battery_now(bank_id: str = None) -> Dict[str, Any]:
        """Return latest battery bank telemetry.
        
        If bank_id is provided, returns data for that specific bank.
        If bank_id is 'all' or not provided, returns all available battery banks.
        """
        try:
            # Get all configured battery banks from config
            all_configured_banks = []
            
            # Legacy: battery_bank (single)
            if solar_app and hasattr(solar_app, 'cfg') and hasattr(solar_app.cfg, 'battery_bank') and solar_app.cfg.battery_bank:
                bank_cfg = solar_app.cfg.battery_bank
                # Legacy config always has single adapter
                adapter_cfg = bank_cfg.adapter if hasattr(bank_cfg, 'adapter') else None
                all_configured_banks.append({
                    "id": bank_cfg.id,
                    "name": getattr(bank_cfg, "name", None),
                    "adapter_type": adapter_cfg.type if adapter_cfg else None,
                    "manufacturer": getattr(adapter_cfg, "manufacturer", None) if adapter_cfg else None,
                    "model": getattr(adapter_cfg, "model", None) if adapter_cfg else None,
                })
            
            # New: battery_banks (list)
            if solar_app and hasattr(solar_app, 'cfg') and hasattr(solar_app.cfg, 'battery_banks') and solar_app.cfg.battery_banks:
                for bank_cfg in solar_app.cfg.battery_banks:
                    # Avoid duplicates if same bank is in both legacy and new config
                    if not any(b.get("id") == bank_cfg.id for b in all_configured_banks):
                        # Handle both single adapter and failover adapters
                        if hasattr(bank_cfg, 'adapters') and bank_cfg.adapters:
                            # Failover adapter - use the first (primary) adapter
                            adapter_cfg = bank_cfg.adapters[0].adapter
                            adapter_type = "failover"
                        elif hasattr(bank_cfg, 'adapter') and bank_cfg.adapter:
                            # Single adapter
                            adapter_cfg = bank_cfg.adapter
                            adapter_type = adapter_cfg.type
                        else:
                            adapter_cfg = None
                            adapter_type = None
                        
                        all_configured_banks.append({
                            "id": bank_cfg.id,
                            "name": getattr(bank_cfg, "name", None),
                            "adapter_type": adapter_type,
                            "manufacturer": getattr(adapter_cfg, "manufacturer", None) if adapter_cfg else None,
                            "model": getattr(adapter_cfg, "model", None) if adapter_cfg else None,
                        })
            
            # Get active battery bank telemetry
            all_banks = []
            battery_last = getattr(solar_app, "battery_last", None)
            
            log.debug(f"API /api/battery/now: battery_last type={type(battery_last)}, value={battery_last}")
            
            # Handle new structure: battery_last is a dict {bank_id: telemetry}
            if isinstance(battery_last, dict):
                log.info(f"API /api/battery/now: Found {len(battery_last)} banks in battery_last dict: {list(battery_last.keys())}")
                for bank_id_key, tel in battery_last.items():
                    try:
                        data = tel.model_dump()
                        # Ensure the 'id' field matches the dictionary key (bank_id_key)
                        # This is critical for frontend matching
                        data['id'] = bank_id_key
                        data['bank_id'] = bank_id_key  # Also set bank_id for compatibility
                        devices_count = len(data.get('devices', [])) if data.get('devices') else 0
                        log.info(f"API /api/battery/now: Bank {bank_id_key} - id={data.get('id')}, devices={devices_count}, soc={data.get('soc')}, voltage={data.get('voltage')}, has_devices_key={'devices' in data}")
                    except Exception as e:
                        log.warning(f"API /api/battery/now: Error converting bank {bank_id_key} to dict: {e}")
                        try:
                            data = tel.dict()  # pydantic v1 fallback
                            # Ensure the 'id' field matches the dictionary key
                            data['id'] = bank_id_key
                            data['bank_id'] = bank_id_key  # Also set bank_id for compatibility
                            devices_count = len(data.get('devices', [])) if data.get('devices') else 0
                            log.info(f"API /api/battery/now: Bank {bank_id_key} (using dict()) - id={data.get('id')}, devices={devices_count}, soc={data.get('soc')}, voltage={data.get('voltage')}")
                        except Exception as e2:
                            log.error(f"API /api/battery/now: Failed to convert bank {bank_id_key}: {e2}")
                            continue
                    all_banks.append(data)
            # Handle legacy structure: battery_last is a single telemetry object
            elif battery_last:
                try:
                    data = battery_last.model_dump()
                except Exception:
                    data = battery_last.dict()  # pydantic v1 fallback
                
                # Debug logging for cells data
                if hasattr(battery_last, 'cells_data') and battery_last.cells_data:
                    log.info(f"API returning battery data with {len(battery_last.cells_data)} batteries' cell data")
                    for i, entry in enumerate(battery_last.cells_data):
                        cells_count = len(entry.get('cells', [])) if entry.get('cells') else 0
                        log.info(f"  Battery {entry.get('power', i)}: {cells_count} cells")
                else:
                    log.warning("API returning battery data with NO cells_data")
                
                # Debug logging for SOH and cycles in devices
                if hasattr(battery_last, 'devices') and battery_last.devices:
                    log.info(f"API returning battery data with {len(battery_last.devices)} battery units")
                    for device in battery_last.devices:
                        log.info(f"  Battery unit {device.power}: soh={device.soh}, cycles={device.cycles}")
                
                all_banks.append(data)
            
            # If bank_id is specified (and not "all"), return only that bank
            if bank_id and bank_id != "all":
                matching_bank = next((b for b in all_banks if b.get("id") == bank_id), None)
                if matching_bank:
                    return {"status": "ok", "battery": matching_bank, "banks": all_banks, "configured_banks": all_configured_banks}
                else:
                    # Bank not active, but might be configured
                    matching_config = next((b for b in all_configured_banks if b.get("id") == bank_id), None)
                    if matching_config:
                        return {"status": "ok", "battery": None, "banks": all_banks, "configured_banks": all_configured_banks, "message": f"Bank '{bank_id}' is configured but not currently active"}
                    return {"status": "ok", "battery": None, "banks": all_banks, "configured_banks": all_configured_banks}
            
            # Return all banks (or first one for backward compatibility)
            log.info(f"API /api/battery/now: Returning {len(all_banks)} active banks, {len(all_configured_banks)} configured banks")
            if all_banks:
                # For backward compatibility, return first bank as "battery"
                # But also include all banks in response
                result = {"status": "ok", "battery": all_banks[0] if len(all_banks) == 1 else None, "banks": all_banks, "configured_banks": all_configured_banks}
                log.info(f"API /api/battery/now: Response includes banks: {[b.get('id', 'UNKNOWN') for b in all_banks]}")
                # Log device counts for debugging
                for bank in all_banks:
                    devices_count = len(bank.get('devices', [])) if bank.get('devices') else 0
                    log.info(f"API /api/battery/now: Bank {bank.get('id', 'UNKNOWN')} has {devices_count} devices, has_soc={bank.get('soc') is not None}, has_voltage={bank.get('voltage') is not None}")
                return result
            else:
                log.warning(f"API /api/battery/now: No battery telemetry available (battery_last={battery_last}, configured_banks={len(all_configured_banks)})")
                return {"status": "ok", "battery": None, "banks": [], "configured_banks": all_configured_banks}
        except Exception as e:
            log.error(f"Error in /api/battery/now: {e}", exc_info=True)
            return {"status": "error", "error": str(e), "battery": None, "banks": [], "configured_banks": []}
    
    @app.get("/api/battery/configured_banks")
    def api_configured_battery_banks() -> Dict[str, Any]:
        """Return a list of all configured battery banks (from config.yaml)."""
        try:
            configured_banks_list = []
            
            # Legacy: battery_bank (single)
            if solar_app and hasattr(solar_app, 'cfg') and hasattr(solar_app.cfg, 'battery_bank') and solar_app.cfg.battery_bank:
                bank_cfg = solar_app.cfg.battery_bank
                # Legacy config always has single adapter
                adapter_cfg = bank_cfg.adapter if hasattr(bank_cfg, 'adapter') else None
                configured_banks_list.append({
                    "id": bank_cfg.id,
                    "name": bank_cfg.name,
                    "manufacturer": getattr(adapter_cfg, "manufacturer", None) if adapter_cfg else None,
                    "model": getattr(adapter_cfg, "model", None) if adapter_cfg else None,
                    "type": adapter_cfg.type if adapter_cfg else None,
                    "serial_port": getattr(adapter_cfg, "serial_port", None) if adapter_cfg else None,
                })
            
            # New: battery_banks (list)
            if solar_app and hasattr(solar_app, 'cfg') and hasattr(solar_app.cfg, 'battery_banks') and solar_app.cfg.battery_banks:
                for bank_cfg in solar_app.cfg.battery_banks:
                    # Avoid duplicates if same bank is in both legacy and new config
                    if not any(b.get("id") == bank_cfg.id for b in configured_banks_list):
                        # Handle both single adapter and failover adapters
                        if hasattr(bank_cfg, 'adapters') and bank_cfg.adapters:
                            # Failover adapter - use the first (primary) adapter
                            adapter_cfg = bank_cfg.adapters[0].adapter
                        elif hasattr(bank_cfg, 'adapter') and bank_cfg.adapter:
                            # Single adapter
                            adapter_cfg = bank_cfg.adapter
                        else:
                            adapter_cfg = None
                        
                        configured_banks_list.append({
                            "id": bank_cfg.id,
                            "name": bank_cfg.name,
                            "manufacturer": getattr(adapter_cfg, "manufacturer", None) if adapter_cfg else None,
                            "model": getattr(adapter_cfg, "model", None) if adapter_cfg else None,
                            "type": adapter_cfg.type if adapter_cfg else None,
                            "serial_port": getattr(adapter_cfg, "serial_port", None) if adapter_cfg else None,
                        })
            
            return {"status": "ok", "configured_banks": configured_banks_list}
        except Exception as e:
            log.error(f"Error in /api/battery/configured_banks: {e}", exc_info=True)
            return {"status": "error", "error": str(e), "configured_banks": []}
    
    @app.get("/api/meters")
    def api_meters() -> Dict[str, Any]:
        """Return list of configured meters."""
        try:
            if not solar_app or not hasattr(solar_app, 'cfg') or not solar_app.cfg.meters:
                return {"status": "ok", "meters": []}
            
            meter_ids = [meter.id for meter in solar_app.cfg.meters]
            return {"status": "ok", "meters": meter_ids}
        except Exception as e:
            log.error(f"Error in /api/meters: {e}", exc_info=True)
            return {"status": "error", "error": str(e), "meters": []}
    
    @app.get("/api/meter/now")
    def api_meter_now(meter_id: str = "all") -> Dict[str, Any]:
        """Return latest meter telemetry.
        If meter_id is 'all' or not provided, returns the first available meter.
        If a specific meter_id is provided, returns data for that meter only.
        """
        try:
            meter_last = getattr(solar_app, "meter_last", None)
            if not meter_last:
                log.debug("No meter telemetry available")
                return {"status": "ok", "meter": None}
            
            # If 'all' or empty, get first available meter
            if meter_id in ("all", "", None):
                if len(meter_last) > 0:
                    # Get first meter
                    first_meter_id = list(meter_last.keys())[0]
                    tel = meter_last[first_meter_id]
                else:
                    return {"status": "ok", "meter": None}
            else:
                # Get specific meter
                tel = meter_last.get(meter_id)
                if not tel:
                    return {"status": "error", "error": f"Meter '{meter_id}' not found", "meter": None}
            
            try:
                data = tel.model_dump()
            except Exception:
                data = tel.dict()  # pydantic v1 fallback
            
            return {"status": "ok", "meter": _make_json_serializable(data)}
        except Exception as e:
            log.error(f"Error in /api/meter/now: {e}", exc_info=True)
            return {"status": "error", "error": str(e), "meter": None}
    
    @app.get("/api/meter/{meter_id}/summary")
    def api_meter_summary(
        meter_id: str,
        period: str = "today",  # today, yesterday, week, this_month, last_month, this_year, last_year, custom
        start_date: Optional[str] = None,  # YYYY-MM-DD format
        end_date: Optional[str] = None,  # YYYY-MM-DD format
        group_by: str = "day"  # day, week, month, year
    ) -> Dict[str, Any]:
        """Get meter energy summary with date filters.
        
        Period options:
        - today: Today's data
        - yesterday: Yesterday's data
        - week: Last 7 days
        - this_month: Current month
        - last_month: Previous month
        - this_year: Current year
        - last_year: Previous year
        - custom: Use start_date and end_date parameters
        """
        try:
            from datetime import datetime, timedelta
            from solarhub.timezone_utils import now_configured, get_configured_date_string
            
            if not solar_app or not hasattr(solar_app, 'logger'):
                return {"status": "error", "error": "Logger not available"}
            
            # Calculate date range based on period
            now = now_configured()
            today = now.date()
            
            if period == "today":
                start_date_str = today.strftime('%Y-%m-%d')
                end_date_str = today.strftime('%Y-%m-%d')
            elif period == "yesterday":
                yesterday = today - timedelta(days=1)
                start_date_str = yesterday.strftime('%Y-%m-%d')
                end_date_str = yesterday.strftime('%Y-%m-%d')
            elif period == "week":
                week_start = today - timedelta(days=6)
                start_date_str = week_start.strftime('%Y-%m-%d')
                end_date_str = today.strftime('%Y-%m-%d')
            elif period == "this_month":
                month_start = today.replace(day=1)
                start_date_str = month_start.strftime('%Y-%m-%d')
                end_date_str = today.strftime('%Y-%m-%d')
            elif period == "last_month":
                first_day_this_month = today.replace(day=1)
                last_day_last_month = first_day_this_month - timedelta(days=1)
                first_day_last_month = last_day_last_month.replace(day=1)
                start_date_str = first_day_last_month.strftime('%Y-%m-%d')
                end_date_str = last_day_last_month.strftime('%Y-%m-%d')
            elif period == "this_year":
                year_start = today.replace(month=1, day=1)
                start_date_str = year_start.strftime('%Y-%m-%d')
                end_date_str = today.strftime('%Y-%m-%d')
            elif period == "last_year":
                year_start = today.replace(month=1, day=1)
                last_year_start = year_start.replace(year=year_start.year - 1)
                last_year_end = year_start - timedelta(days=1)
                start_date_str = last_year_start.strftime('%Y-%m-%d')
                end_date_str = last_year_end.strftime('%Y-%m-%d')
            elif period == "custom":
                if not start_date or not end_date:
                    return {"status": "error", "error": "start_date and end_date required for custom period"}
                start_date_str = start_date
                end_date_str = end_date
            else:
                return {"status": "error", "error": f"Invalid period: {period}"}
            
            # Get daily summaries from database
            daily_data = solar_app.logger.get_meter_daily_summary(meter_id, start_date_str, end_date_str)
            
            # Group by requested period if needed
            if group_by == "day":
                grouped_data = daily_data
            elif group_by == "week":
                # Group by week
                grouped_data = {}
                for entry in daily_data:
                    date_obj = datetime.strptime(entry["day"], "%Y-%m-%d").date()
                    week_start = date_obj - timedelta(days=date_obj.weekday())
                    week_key = week_start.strftime('%Y-%m-%d')
                    if week_key not in grouped_data:
                        grouped_data[week_key] = {
                            "period_start": week_key,
                            "period_end": (week_start + timedelta(days=6)).strftime('%Y-%m-%d'),
                            "import_energy_kwh": 0.0,
                            "export_energy_kwh": 0.0,
                            "net_energy_kwh": 0.0,
                            "max_import_power_w": None,
                            "max_export_power_w": None,
                            "days": []
                        }
                    grouped_data[week_key]["import_energy_kwh"] += entry["import_energy_kwh"]
                    grouped_data[week_key]["export_energy_kwh"] += entry["export_energy_kwh"]
                    grouped_data[week_key]["net_energy_kwh"] += entry["net_energy_kwh"]
                    if entry["max_import_power_w"]:
                        if grouped_data[week_key]["max_import_power_w"] is None:
                            grouped_data[week_key]["max_import_power_w"] = entry["max_import_power_w"]
                        else:
                            grouped_data[week_key]["max_import_power_w"] = max(
                                grouped_data[week_key]["max_import_power_w"], entry["max_import_power_w"]
                            )
                    if entry["max_export_power_w"]:
                        if grouped_data[week_key]["max_export_power_w"] is None:
                            grouped_data[week_key]["max_export_power_w"] = entry["max_export_power_w"]
                        else:
                            grouped_data[week_key]["max_export_power_w"] = max(
                                grouped_data[week_key]["max_export_power_w"], entry["max_export_power_w"]
                            )
                    grouped_data[week_key]["days"].append(entry["day"])
                grouped_data = list(grouped_data.values())
            elif group_by == "month":
                # Group by month
                grouped_data = {}
                for entry in daily_data:
                    date_obj = datetime.strptime(entry["day"], "%Y-%m-%d").date()
                    month_key = date_obj.strftime('%Y-%m')
                    if month_key not in grouped_data:
                        grouped_data[month_key] = {
                            "period": month_key,
                            "import_energy_kwh": 0.0,
                            "export_energy_kwh": 0.0,
                            "net_energy_kwh": 0.0,
                            "max_import_power_w": None,
                            "max_export_power_w": None,
                            "days": []
                        }
                    grouped_data[month_key]["import_energy_kwh"] += entry["import_energy_kwh"]
                    grouped_data[month_key]["export_energy_kwh"] += entry["export_energy_kwh"]
                    grouped_data[month_key]["net_energy_kwh"] += entry["net_energy_kwh"]
                    if entry["max_import_power_w"]:
                        if grouped_data[month_key]["max_import_power_w"] is None:
                            grouped_data[month_key]["max_import_power_w"] = entry["max_import_power_w"]
                        else:
                            grouped_data[month_key]["max_import_power_w"] = max(
                                grouped_data[month_key]["max_import_power_w"], entry["max_import_power_w"]
                            )
                    if entry["max_export_power_w"]:
                        if grouped_data[month_key]["max_export_power_w"] is None:
                            grouped_data[month_key]["max_export_power_w"] = entry["max_export_power_w"]
                        else:
                            grouped_data[month_key]["max_export_power_w"] = max(
                                grouped_data[month_key]["max_export_power_w"], entry["max_export_power_w"]
                            )
                    grouped_data[month_key]["days"].append(entry["day"])
                grouped_data = list(grouped_data.values())
            elif group_by == "year":
                # Group by year
                grouped_data = {}
                for entry in daily_data:
                    date_obj = datetime.strptime(entry["day"], "%Y-%m-%d").date()
                    year_key = str(date_obj.year)
                    if year_key not in grouped_data:
                        grouped_data[year_key] = {
                            "period": year_key,
                            "import_energy_kwh": 0.0,
                            "export_energy_kwh": 0.0,
                            "net_energy_kwh": 0.0,
                            "max_import_power_w": None,
                            "max_export_power_w": None,
                            "days": []
                        }
                    grouped_data[year_key]["import_energy_kwh"] += entry["import_energy_kwh"]
                    grouped_data[year_key]["export_energy_kwh"] += entry["export_energy_kwh"]
                    grouped_data[year_key]["net_energy_kwh"] += entry["net_energy_kwh"]
                    if entry["max_import_power_w"]:
                        if grouped_data[year_key]["max_import_power_w"] is None:
                            grouped_data[year_key]["max_import_power_w"] = entry["max_import_power_w"]
                        else:
                            grouped_data[year_key]["max_import_power_w"] = max(
                                grouped_data[year_key]["max_import_power_w"], entry["max_import_power_w"]
                            )
                    if entry["max_export_power_w"]:
                        if grouped_data[year_key]["max_export_power_w"] is None:
                            grouped_data[year_key]["max_export_power_w"] = entry["max_export_power_w"]
                        else:
                            grouped_data[year_key]["max_export_power_w"] = max(
                                grouped_data[year_key]["max_export_power_w"], entry["max_export_power_w"]
                            )
                    grouped_data[year_key]["days"].append(entry["day"])
                grouped_data = list(grouped_data.values())
            else:
                grouped_data = daily_data
            
            # Calculate totals
            total_import = sum(d.get("import_energy_kwh", 0) for d in grouped_data)
            total_export = sum(d.get("export_energy_kwh", 0) for d in grouped_data)
            total_net = total_import - total_export
            
            return {
                "status": "ok",
                "meter_id": meter_id,
                "period": period,
                "start_date": start_date_str,
                "end_date": end_date_str,
                "group_by": group_by,
                "data": grouped_data,
                "totals": {
                    "import_energy_kwh": round(total_import, 2),
                    "export_energy_kwh": round(total_export, 2),
                    "net_energy_kwh": round(total_net, 2)
                }
            }
        except Exception as e:
            log.error(f"Error in /api/meter/{meter_id}/summary: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    @app.get("/api/meter/{meter_id}/comparison")
    def api_meter_comparison(
        meter_id: str,
        months: int = 12  # Number of months to compare
    ) -> Dict[str, Any]:
        """Get month-over-month comparison for the last N months.
        Returns this month vs same month last year for each of the last N months.
        """
        try:
            from datetime import datetime, timedelta
            from solarhub.timezone_utils import now_configured
            
            if not solar_app or not hasattr(solar_app, 'logger'):
                return {"status": "error", "error": "Logger not available"}
            
            now = now_configured()
            today = now.date()
            
            comparison_data = []
            
            # Get data for last N months
            for i in range(months):
                # Calculate target month (going backwards)
                target_date = today.replace(day=1) - timedelta(days=32 * i)
                target_month = target_date.month
                target_year = target_date.year
                
                # This year's month
                this_year_start = f"{target_year}-{target_month:02d}-01"
                # Calculate last day of month
                if target_month == 12:
                    this_year_end = f"{target_year}-12-31"
                else:
                    next_month = target_date.replace(month=target_month + 1, day=1)
                    last_day = next_month - timedelta(days=1)
                    this_year_end = last_day.strftime('%Y-%m-%d')
                
                # Last year's same month
                last_year_start = f"{target_year - 1}-{target_month:02d}-01"
                if target_month == 12:
                    last_year_end = f"{target_year - 1}-12-31"
                else:
                    next_month = target_date.replace(month=target_month + 1, day=1, year=target_year - 1)
                    last_day = next_month - timedelta(days=1)
                    last_year_end = last_day.strftime('%Y-%m-%d')
                
                # Get this year's data
                this_year_data = solar_app.logger.get_meter_daily_summary(meter_id, this_year_start, this_year_end)
                this_year_import = sum(d.get("import_energy_kwh", 0) for d in this_year_data)
                this_year_export = sum(d.get("export_energy_kwh", 0) for d in this_year_data)
                this_year_net = this_year_import - this_year_export
                
                # Get last year's data
                last_year_data = solar_app.logger.get_meter_daily_summary(meter_id, last_year_start, last_year_end)
                last_year_import = sum(d.get("import_energy_kwh", 0) for d in last_year_data)
                last_year_export = sum(d.get("export_energy_kwh", 0) for d in last_year_data)
                last_year_net = last_year_import - last_year_export
                
                comparison_data.append({
                    "month": f"{target_year}-{target_month:02d}",
                    "month_name": target_date.strftime('%B %Y'),
                    "this_year": {
                        "import_energy_kwh": round(this_year_import, 2),
                        "export_energy_kwh": round(this_year_export, 2),
                        "net_energy_kwh": round(this_year_net, 2)
                    },
                    "last_year": {
                        "import_energy_kwh": round(last_year_import, 2),
                        "export_energy_kwh": round(last_year_export, 2),
                        "net_energy_kwh": round(last_year_net, 2)
                    },
                    "difference": {
                        "import_energy_kwh": round(this_year_import - last_year_import, 2),
                        "export_energy_kwh": round(this_year_export - last_year_export, 2),
                        "net_energy_kwh": round(this_year_net - last_year_net, 2)
                    },
                    "percent_change": {
                        "import_energy_kwh": round(((this_year_import - last_year_import) / last_year_import * 100) if last_year_import > 0 else 0, 1),
                        "export_energy_kwh": round(((this_year_export - last_year_export) / last_year_export * 100) if last_year_export > 0 else 0, 1),
                        "net_energy_kwh": round(((this_year_net - last_year_net) / abs(last_year_net) * 100) if last_year_net != 0 else 0, 1)
                    }
                })
            
            return {
                "status": "ok",
                "meter_id": meter_id,
                "months": months,
                "comparison": comparison_data
            }
        except Exception as e:
            log.error(f"Error in /api/meter/{meter_id}/comparison: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    @app.get("/api/arrays")
    def api_arrays() -> Dict[str, Any]:
        """List all arrays with membership and active battery packs."""
        try:
            arrays = []
            if solar_app and hasattr(solar_app, 'cfg') and solar_app.cfg.arrays:
                from solarhub.config_migration import build_array_runtime_objects, build_pack_runtime_objects
                array_objs = build_array_runtime_objects(solar_app.cfg)
                pack_objs = build_pack_runtime_objects(solar_app.cfg)
                
                for array_cfg in solar_app.cfg.arrays:
                    array_obj = array_objs.get(array_cfg.id)
                    array_data = {
                        "id": array_cfg.id,
                        "name": array_cfg.name,
                        "inverter_ids": array_cfg.inverter_ids,
                        "inverter_count": len(array_cfg.inverter_ids),
                        "attached_pack_ids": array_obj.attached_pack_ids if array_obj else [],
                        "pack_count": len(array_obj.attached_pack_ids) if array_obj else 0,
                    }
                    arrays.append(array_data)
            
            return {"status": "ok", "arrays": arrays}
        except Exception as e:
            log.error(f"Error in /api/arrays: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    @app.get("/api/arrays/{array_id}/now")
    def api_array_now(array_id: str, system_id: Optional[str] = None) -> Dict[str, Any]:
        """Get consolidated 'now' telemetry for an array with hierarchy structure."""
        try:
            from solarhub.array_aggregator import ArrayAggregator
            from solarhub.config_migration import build_array_runtime_objects, build_pack_runtime_objects
            
            # Use hierarchy if available
            inv_array = None
            target_system_id = system_id
            inverter_ids = []
            
            if hasattr(solar_app, 'hierarchy_systems') and solar_app.hierarchy_systems:
                # Find array in hierarchy
                for sys_id, system in solar_app.hierarchy_systems.items():
                    if system_id and sys_id != system_id:
                        continue
                    for arr in system.inverter_arrays:
                        if arr.array_id == array_id:
                            inv_array = arr
                            target_system_id = sys_id
                            inverter_ids = arr.inverter_ids
                            break
                    if inv_array:
                        break
            
            # Fallback to config
            if not inv_array:
                if solar_app and hasattr(solar_app, 'cfg') and solar_app.cfg.arrays:
                    array_cfg = next((a for a in solar_app.cfg.arrays if a.id == array_id), None)
                    if array_cfg:
                        inverter_ids = array_cfg.inverter_ids
                    else:
                        return {"status": "error", "error": f"Array '{array_id}' not found"}
                else:
                    return {"status": "error", "error": f"Array '{array_id}' not found"}
            
            # Get inverter telemetry for this array
            inverter_telemetry = {}
            for inv_id in inverter_ids:
                tel_dict = solar_app.get_now(inv_id)
                if tel_dict:
                    from solarhub.models import Telemetry
                    tel = Telemetry(**tel_dict)
                    inverter_telemetry[inv_id] = tel
            
            # Get pack telemetry if available - use hierarchy if available
            pack_telemetry = {}
            pack_configs = {}
            
            if inv_array and inv_array.attached_battery_array_id:
                # Use hierarchy battery array
                for sys in solar_app.hierarchy_systems.values():
                    for bat_array in sys.battery_arrays:
                        if bat_array.battery_array_id == inv_array.attached_battery_array_id:
                            for pack in bat_array.battery_packs:
                                pack_id = pack.pack_id
                                if pack.nominal_kwh:
                                    pack_configs[pack_id] = {
                                        "nominal_kwh": pack.nominal_kwh,
                                        "max_charge_kw": pack.max_charge_kw or 0.0,
                                        "max_discharge_kw": pack.max_discharge_kw or 0.0,
                                    }
                                
                                # Get battery telemetry
                                if hasattr(solar_app, 'battery_last') and solar_app.battery_last:
                                    if isinstance(solar_app.battery_last, dict):
                                        bank_tel = solar_app.battery_last.get(pack_id)
                                    else:
                                        bank_tel = solar_app.battery_last  # Legacy
                                    
                                    if bank_tel:
                                        from solarhub.array_models import BatteryPackTelemetry
                                        pack_tel = BatteryPackTelemetry(
                                            pack_id=pack_id,
                                            array_id=array_id,
                                            ts=bank_tel.ts,
                                            soc_pct=bank_tel.soc,
                                            voltage_v=bank_tel.voltage,
                                            current_a=bank_tel.current,
                                            power_w=bank_tel.voltage * bank_tel.current if bank_tel.voltage and bank_tel.current else None,
                                            temperature_c=bank_tel.temperature,
                                        )
                                        pack_telemetry[pack_id] = pack_tel
                            break
            elif solar_app.cfg.battery_packs and solar_app.cfg.attachments:
                # Fallback to config-based approach
                pack_objs = build_pack_runtime_objects(solar_app.cfg)
                for att in solar_app.cfg.attachments:
                    if att.array_id == array_id and att.detached_at is None:
                        pack_id = att.pack_id
                        pack_cfg = next((p for p in solar_app.cfg.battery_packs if p.id == pack_id), None)
                        if pack_cfg:
                            pack_configs[pack_id] = {
                                "nominal_kwh": pack_cfg.nominal_kwh,
                                "max_charge_kw": pack_cfg.max_charge_kw,
                                "max_discharge_kw": pack_cfg.max_discharge_kw,
                            }
                            # Get pack telemetry from battery adapter if available
                            if hasattr(solar_app, 'battery_last') and solar_app.battery_last:
                                from solarhub.array_models import BatteryPackTelemetry
                                bank_tel = solar_app.battery_last
                                pack_tel = BatteryPackTelemetry(
                                    pack_id=pack_id,
                                    array_id=array_id,
                                    ts=bank_tel.ts,
                                    soc_pct=bank_tel.soc,
                                    voltage_v=bank_tel.voltage,
                                    current_a=bank_tel.current,
                                    power_w=bank_tel.voltage * bank_tel.current if bank_tel.voltage and bank_tel.current else None,
                                    temperature_c=bank_tel.temperature,
                                )
                                pack_telemetry[pack_id] = pack_tel
            
            # Aggregate array telemetry
            aggregator = ArrayAggregator()
            array_tel = aggregator.aggregate_array_telemetry(
                array_id, inverter_telemetry, pack_telemetry, pack_configs
            )
            
            array_dict = array_tel.model_dump()
            array_dict["system_id"] = target_system_id
            if inv_array:
                array_dict["array_name"] = inv_array.name
            
            return {
                "status": "ok",
                "array_id": array_id,
                "system_id": target_system_id,
                "now": array_dict
            }
        except Exception as e:
            log.error(f"Error in /api/arrays/{array_id}/now: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    @app.get("/api/arrays/{array_id}/energy/hourly")
    def api_array_energy_hourly(array_id: str, date: str = None) -> Dict[str, Any]:
        """Get hourly energy data for an array."""
        try:
            from datetime import datetime, timedelta
            from solarhub.timezone_utils import now_configured, parse_iso_to_configured
            
            # Get array configuration
            array_cfg = None
            if solar_app and hasattr(solar_app, 'cfg') and solar_app.cfg.arrays:
                array_cfg = next((a for a in solar_app.cfg.arrays if a.id == array_id), None)
            
            if not array_cfg:
                return {"status": "error", "error": f"Array '{array_id}' not found"}
            
            # Parse date or use today
            if date:
                try:
                    target_date = parse_iso_to_configured(datetime.fromisoformat(date))
                except Exception:
                    target_date = now_configured().replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                target_date = now_configured().replace(hour=0, minute=0, second=0, microsecond=0)
            
            start_time = target_date
            end_time = target_date + timedelta(days=1)
            
            # Get hourly energy data for array
            energy_calc = EnergyCalculator(solar_app.logger.path)
            hourly_data = energy_calc.get_array_hourly_energy_data(
                array_id=array_id,
                inverter_ids=array_cfg.inverter_ids,
                start_time=start_time,
                end_time=end_time
            )
            
            return {
                "status": "ok",
                "array_id": array_id,
                "date": target_date.strftime('%Y-%m-%d'),
                "hourly_data": hourly_data,
                "source": "energy_calculator"
            }
        except Exception as e:
            log.error(f"Error in /api/arrays/{array_id}/energy/hourly: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    @app.get("/api/arrays/{array_id}/energy/daily")
    def api_array_energy_daily(array_id: str, date: str = None) -> Dict[str, Any]:
        """Get daily energy summary for an array."""
        try:
            from datetime import datetime
            from solarhub.timezone_utils import now_configured, parse_iso_to_configured
            
            # Get array configuration
            array_cfg = None
            if solar_app and hasattr(solar_app, 'cfg') and solar_app.cfg.arrays:
                array_cfg = next((a for a in solar_app.cfg.arrays if a.id == array_id), None)
            
            if not array_cfg:
                return {"status": "error", "error": f"Array '{array_id}' not found"}
            
            # Parse date or use today
            if date:
                try:
                    target_date = parse_iso_to_configured(datetime.fromisoformat(date))
                except Exception:
                    target_date = now_configured().date()
            else:
                target_date = now_configured().date()
            
            # Get daily energy summary for array
            energy_calc = EnergyCalculator(solar_app.logger.path)
            daily_summary = energy_calc.get_array_daily_energy_summary(
                array_id=array_id,
                inverter_ids=array_cfg.inverter_ids,
                date=target_date
            )
            
            return {
                "status": "ok",
                "array_id": array_id,
                "date": target_date.strftime('%Y-%m-%d'),
                "daily_summary": daily_summary,
                "source": "energy_calculator"
            }
        except Exception as e:
            log.error(f"Error in /api/arrays/{array_id}/energy/daily: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    @app.get("/api/arrays/{array_id}/scheduler/plan")
    def api_array_scheduler_plan(array_id: str) -> Dict[str, Any]:
        """Get the current power splitting plan for an array."""
        try:
            if not solar_app or not hasattr(solar_app, 'smart_schedulers'):
                return {"status": "error", "error": "Scheduler not available"}
            
            scheduler = solar_app.smart_schedulers.get(array_id)
            if not scheduler:
                return {"status": "error", "error": f"Scheduler not found for array {array_id}"}
            
            plan = getattr(scheduler, '_last_split_plan', None)
            if not plan:
                return {"status": "ok", "plan": None, "message": "No split plan available yet"}
            
            return {"status": "ok", "plan": _make_json_serializable(plan)}
        except Exception as e:
            log.error(f"Error in /api/arrays/{array_id}/scheduler/plan: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    @app.get("/api/arrays/{array_id}/forecast")
    def api_array_forecast(array_id: str) -> Dict[str, Any]:
        """Get PV forecast data for a specific array."""
        return api_forecast(inverter_id="all", array_id=array_id)
    
    @app.get("/api/home/now")
    def api_home_now(
        period: str = "today",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        system_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get aggregated system-level telemetry (all arrays and system-attached meters).
        
        Args:
            period: Time period filter ('today', 'week', 'month', 'year', 'custom')
            start_date: Start date for custom period (YYYY-MM-DD)
            end_date: End date for custom period (YYYY-MM-DD)
            system_id: System ID to query (defaults to first system or 'system')
        """
        try:
            from solarhub.array_aggregator import ArrayAggregator
            from solarhub.config_migration import build_array_runtime_objects
            
            if not solar_app or not hasattr(solar_app, 'cfg'):
                return {"status": "error", "error": "Solar app not available"}
            
            # Determine system_id - use hierarchy if available, otherwise default
            target_system_id = system_id or "system"
            if hasattr(solar_app, 'hierarchy_systems') and solar_app.hierarchy_systems:
                if not system_id:
                    # Use first system if no system_id specified
                    target_system_id = next(iter(solar_app.hierarchy_systems.keys()))
                elif system_id not in solar_app.hierarchy_systems:
                    return {"status": "error", "error": f"System '{system_id}' not found"}
            
            # Get all array telemetry - use hierarchy if available
            array_telemetry = {}
            aggregator = ArrayAggregator()
            
            # Use hierarchy if available
            if hasattr(solar_app, 'hierarchy_systems') and solar_app.hierarchy_systems and target_system_id in solar_app.hierarchy_systems:
                system = solar_app.hierarchy_systems[target_system_id]
                
                for inv_array in system.inverter_arrays:
                    # Get inverter telemetry for this array
                    inverter_telemetry = {}
                    for inverter in inv_array.inverters:
                        tel_dict = solar_app.get_now(inverter.inverter_id)
                        if tel_dict:
                            from solarhub.models import Telemetry
                            tel = Telemetry(**tel_dict)
                            inverter_telemetry[inverter.inverter_id] = tel
                    
                    # Get pack telemetry if available
                    pack_telemetry = {}
                    pack_configs = {}
                    if inv_array.attached_battery_array_id:
                        # Find attached battery array
                        for bat_array in system.battery_arrays:
                            if bat_array.battery_array_id == inv_array.attached_battery_array_id:
                                for pack in bat_array.battery_packs:
                                    pack_id = pack.pack_id
                                    if pack.nominal_kwh:
                                        pack_configs[pack_id] = {
                                            "nominal_kwh": pack.nominal_kwh,
                                            "max_charge_kw": pack.max_charge_kw or 0.0,
                                            "max_discharge_kw": pack.max_discharge_kw or 0.0,
                                        }
                                    
                                    # Get battery telemetry
                                    if hasattr(solar_app, 'battery_last') and solar_app.battery_last:
                                        if isinstance(solar_app.battery_last, dict):
                                            battery_tel = solar_app.battery_last.get(pack_id)
                                            if battery_tel:
                                                from solarhub.array_models import BatteryPackTelemetry
                                                pack_tel = BatteryPackTelemetry(
                                                    pack_id=pack_id,
                                                    array_id=inv_array.array_id,
                                                    ts=battery_tel.ts,
                                                    soc_pct=battery_tel.soc,
                                                    voltage_v=battery_tel.voltage,
                                                    current_a=battery_tel.current,
                                                    power_w=battery_tel.voltage * battery_tel.current if battery_tel.voltage and battery_tel.current else None,
                                                    temperature_c=battery_tel.temperature,
                                                )
                                                pack_telemetry[pack_id] = pack_tel
                                break
                    
                    # Aggregate array telemetry
                    if inverter_telemetry:
                        array_tel = aggregator.aggregate_array_telemetry(
                            inv_array.array_id, inverter_telemetry, pack_telemetry, pack_configs
                        )
                        array_telemetry[inv_array.array_id] = array_tel
            
            # Fallback to config-based approach
            elif solar_app.cfg.arrays:
                array_objs = build_array_runtime_objects(solar_app.cfg)
                
                for array_cfg in solar_app.cfg.arrays:
                    # Get inverter telemetry for this array
                    inverter_telemetry = {}
                    for inv_id in array_cfg.inverter_ids:
                        tel_dict = solar_app.get_now(inv_id)
                        if tel_dict:
                            from solarhub.models import Telemetry
                            tel = Telemetry(**tel_dict)
                            inverter_telemetry[inv_id] = tel
                    
                    # Get pack telemetry if available
                    pack_telemetry = {}
                    pack_configs = {}
                    if solar_app.cfg.battery_packs and solar_app.cfg.attachments:
                        from solarhub.config_migration import build_pack_runtime_objects
                        pack_objs = build_pack_runtime_objects(solar_app.cfg)
                        for att in solar_app.cfg.attachments:
                            if att.array_id == array_cfg.id and att.detached_at is None:
                                pack_id = att.pack_id
                                pack_cfg = next((p for p in solar_app.cfg.battery_packs if p.id == pack_id), None)
                                if pack_cfg:
                                    pack_configs[pack_id] = {
                                        "nominal_kwh": pack_cfg.nominal_kwh,
                                        "max_charge_kw": pack_cfg.max_charge_kw,
                                        "max_discharge_kw": pack_cfg.max_discharge_kw,
                                    }
                    
                    # Aggregate array telemetry
                    if inverter_telemetry:
                        array_tel = aggregator.aggregate_array_telemetry(
                            array_cfg.id, inverter_telemetry, pack_telemetry, pack_configs
                        )
                        array_telemetry[array_cfg.id] = array_tel
            
            # Get home-attached meters (attachment_target == "home" OR array_id == "home")
            # Support both field names for backward compatibility
            meter_telemetry = {}
            meter_configs = {}  # Store configs for meters even if telemetry is missing
            if solar_app.cfg.meters:
                for meter_cfg in solar_app.cfg.meters:
                    attachment_target = getattr(meter_cfg, 'attachment_target', None)
                    array_id = getattr(meter_cfg, 'array_id', None)
                    # Check both attachment_target and array_id for "home"
                    is_home_meter = (attachment_target == "home") or (array_id == "home")
                    
                    if is_home_meter:
                        meter_id = meter_cfg.id
                        # Store config even if telemetry is missing (for fallback display)
                        meter_configs[meter_id] = meter_cfg
                        
                        if hasattr(solar_app, 'meter_last') and solar_app.meter_last:
                            meter_tel = solar_app.meter_last.get(meter_id)
                            if meter_tel:
                                meter_telemetry[meter_id] = meter_tel
            
            # Get all battery bank telemetry for aggregation
            battery_bank_telemetry = {}
            if hasattr(solar_app, 'battery_last') and solar_app.battery_last:
                if isinstance(solar_app.battery_last, dict):
                    battery_bank_telemetry = solar_app.battery_last
                elif solar_app.battery_last:
                    # Legacy: single battery bank
                    battery_bank_telemetry["legacy"] = solar_app.battery_last
            
            # Get meter energy data from database if available
            meter_energy_data = {}
            if solar_app.logger:
                try:
                    # Get daily energy summaries for meters
                    from solarhub.timezone_utils import now_configured
                    today = now_configured().date().isoformat()
                    for meter_id in meter_configs.keys():
                        try:
                            daily_summary = solar_app.logger.get_meter_daily_summary(meter_id, today, today)
                            if daily_summary:
                                meter_energy_data[meter_id] = {
                                    "import_energy_kwh": float(daily_summary[0].get("import_energy_kwh", 0) or 0),
                                    "export_energy_kwh": float(daily_summary[0].get("export_energy_kwh", 0) or 0),
                                }
                        except Exception as e:
                            log.debug(f"Could not get meter energy data for {meter_id}: {e}")
                except Exception as e:
                    log.debug(f"Error getting meter energy data: {e}")
            
            # Aggregate home telemetry
            aggregator = ArrayAggregator()
            home_tel = aggregator.aggregate_home_telemetry(
                array_telemetry, meter_telemetry, battery_bank_telemetry, 
                meter_configs=meter_configs, meter_energy_data=meter_energy_data
            )
            
            # Calculate date range based on period
            from solarhub.timezone_utils import get_configured_start_of_day, get_configured_date_string, now_configured
            from datetime import datetime, timedelta
            
            if period == "custom" and start_date and end_date:
                try:
                    start = datetime.fromisoformat(start_date).date()
                    end = datetime.fromisoformat(end_date).date()
                except ValueError:
                    start = now_configured().date()
                    end = now_configured().date()
            elif period == "today":
                start = now_configured().date()
                end = now_configured().date()
            elif period == "week":
                today = now_configured().date()
                start = today - timedelta(days=today.weekday())
                end = today
            elif period == "month":
                today = now_configured().date()
                start = today.replace(day=1)
                end = today
            elif period == "year":
                today = now_configured().date()
                start = today.replace(month=1, day=1)
                end = today
            else:
                # Default to today
                start = now_configured().date()
                end = now_configured().date()
            
            # Get daily energy statistics for home (aggregated over period)
            daily_energy = {
                "solar_energy_kwh": 0.0,
                "load_energy_kwh": 0.0,
                "battery_charge_energy_kwh": 0.0,
                "battery_discharge_energy_kwh": 0.0,
                "grid_import_energy_kwh": 0.0,
                "grid_export_energy_kwh": 0.0,
            }
            
            # Aggregate daily energy from all inverters in all arrays for the date range
            if solar_app.cfg.arrays:
                from solarhub.energy_calculator import EnergyCalculator
                
                if solar_app.logger and hasattr(solar_app.logger, 'path'):
                    energy_calc = EnergyCalculator(solar_app.logger.path)
                    
                    # Iterate through each day in the range
                    current_date = start
                    while current_date <= end:
                        date_str = current_date.isoformat()
                        
                        for array_cfg in solar_app.cfg.arrays:
                            for inv_id in array_cfg.inverter_ids:
                                try:
                                    inv_daily = energy_calc.get_daily_energy_summary(inv_id, current_date)
                                    daily_energy["solar_energy_kwh"] += inv_daily.get('total_solar_kwh', 0.0) or 0.0
                                    daily_energy["load_energy_kwh"] += inv_daily.get('total_load_kwh', 0.0) or 0.0
                                    daily_energy["battery_charge_energy_kwh"] += inv_daily.get('total_battery_charge_kwh', 0.0) or 0.0
                                    daily_energy["battery_discharge_energy_kwh"] += inv_daily.get('total_battery_discharge_kwh', 0.0) or 0.0
                                    daily_energy["grid_import_energy_kwh"] += inv_daily.get('total_grid_import_kwh', 0.0) or 0.0
                                    daily_energy["grid_export_energy_kwh"] += inv_daily.get('total_grid_export_kwh', 0.0) or 0.0
                                except Exception as e:
                                    log.debug(f"Error getting daily energy for inverter {inv_id} on {date_str}: {e}")
                        
                        current_date += timedelta(days=1)
            
            # Get meter daily summaries for home-attached meters for the date range
            if solar_app.cfg.meters and solar_app.logger:
                start_str = start.isoformat()
                end_str = end.isoformat()
                
                for meter_cfg in solar_app.cfg.meters:
                    if getattr(meter_cfg, 'attachment_target', None) == "home":
                        meter_id = meter_cfg.id
                        try:
                            meter_daily_list = solar_app.logger.get_meter_daily_summary(meter_id, start_str, end_str)
                            for day_data in meter_daily_list:
                                # Add meter import/export to grid totals
                                daily_energy["grid_import_energy_kwh"] += float(day_data.get("import_energy_kwh", 0) or 0)
                                daily_energy["grid_export_energy_kwh"] += float(day_data.get("export_energy_kwh", 0) or 0)
                        except Exception as e:
                            log.debug(f"Error getting meter daily summary for {meter_id}: {e}")
            
            # Round values
            for key in daily_energy:
                daily_energy[key] = round(daily_energy[key], 2)
            
            # Calculate monthly energy and financial/environmental metrics using existing billing scheduler
            monthly_energy = {
                "solar_energy_kwh": 0.0,
                "grid_import_energy_kwh": 0.0,
                "grid_export_energy_kwh": 0.0,
            }
            financial_metrics = {
                "total_bill_pkr": 0.0,
                "total_saved_pkr": 0.0,
                "co2_prevented_kg": 0.0,
            }
            
            # Get billing config for calculations
            billing_cfg = getattr(solar_app.cfg, 'billing', None) if solar_app and hasattr(solar_app, 'cfg') else None
            log.debug(f"API /api/home/now: billing_cfg = {billing_cfg is not None}, has arrays = {bool(solar_app.cfg.arrays if solar_app and hasattr(solar_app, 'cfg') else False)}, has logger = {bool(solar_app.logger if solar_app else False)}")
            
            # Use existing billing scheduler to get current month's bill
            try:
                if solar_app and hasattr(solar_app, 'cfg') and solar_app.cfg.arrays and solar_app.logger and hasattr(solar_app.logger, 'path'):
                    from datetime import date as date_type
                    from solarhub.billing_scheduler import _compute_daily_snapshot, _get_current_billing_month
                    from solarhub.timezone_utils import now_configured, get_configured_timezone
                    from solarhub.billing_engine import _aggregate_hourly_for_billing_month
                    import sqlite3
                    
                    now = now_configured()
                    today = now.date()
                    today_str = today.isoformat()
                    
                    # Try to get today's snapshot from billing_daily table first (if scheduler already ran)
                    snapshot = None
                    if billing_cfg:
                        try:
                            conn = sqlite3.connect(solar_app.logger.path)
                            cur = conn.cursor()
                            # Query by home_id if available, otherwise fallback to site_id
                            home_id = solar_app.cfg.home.id if solar_app.cfg.home else "home"
                            cur.execute("""
                                SELECT bill_final_rs_to_date, import_off_kwh, export_off_kwh, 
                                       import_peak_kwh, export_peak_kwh, billing_month_id
                                FROM billing_daily
                                WHERE (home_id = ? OR (home_id IS NULL AND site_id = ?)) AND date = ?
                                ORDER BY generated_at_ts DESC
                                LIMIT 1
                            """, (home_id, "default", today_str))
                            row = cur.fetchone()
                            conn.close()
                            
                            if row:
                                # Use data from database (scheduler already calculated today)
                                bill_final, import_off, export_off, import_peak, export_peak, month_id = row
                                financial_metrics["total_bill_pkr"] = round(bill_final or 0.0, 2)
                                monthly_energy["grid_import_energy_kwh"] = round((import_off or 0.0) + (import_peak or 0.0), 2)
                                monthly_energy["grid_export_energy_kwh"] = round((export_off or 0.0) + (export_peak or 0.0), 2)
                                log.debug(f"API /api/home/now: Using billing_daily snapshot from DB - bill: {financial_metrics['total_bill_pkr']} PKR")
                            else:
                                # No snapshot in DB yet, compute it using scheduler logic
                                log.debug("API /api/home/now: No billing_daily snapshot found, computing...")
                                from solarhub.billing_scheduler import _compute_daily_snapshot
                                home_id = solar_app.cfg.home.id if solar_app.cfg.home else "home"
                                snapshot = _compute_daily_snapshot(
                                    solar_app.logger.path,
                                    billing_cfg,
                                    today,
                                    home_id=home_id,
                                    hub_cfg=solar_app.cfg,
                                    site_id="default"
                                )
                                
                                if snapshot:
                                    financial_metrics["total_bill_pkr"] = round(snapshot.bill_final_rs_to_date, 2)
                                    monthly_energy["grid_import_energy_kwh"] = round(
                                        snapshot.import_off_kwh + snapshot.import_peak_kwh, 2
                                    )
                                    monthly_energy["grid_export_energy_kwh"] = round(
                                        snapshot.export_off_kwh + snapshot.export_peak_kwh, 2
                                    )
                                    log.debug(f"API /api/home/now: Computed billing snapshot - bill: {financial_metrics['total_bill_pkr']} PKR")
                        except Exception as e:
                            log.debug(f"Error reading from billing_daily table: {e}, computing snapshot...")
                            # Fallback: compute snapshot
                            if billing_cfg:
                                from solarhub.billing_scheduler import _compute_daily_snapshot
                                home_id = solar_app.cfg.home.id if solar_app.cfg.home else "home"
                                snapshot = _compute_daily_snapshot(
                                    solar_app.logger.path,
                                    billing_cfg,
                                    today,
                                    home_id=home_id,
                                    hub_cfg=solar_app.cfg,
                                    site_id="default"
                                )
                                if snapshot:
                                    financial_metrics["total_bill_pkr"] = round(snapshot.bill_final_rs_to_date, 2)
                                    monthly_energy["grid_import_energy_kwh"] = round(
                                        snapshot.import_off_kwh + snapshot.import_peak_kwh, 2
                                    )
                                    monthly_energy["grid_export_energy_kwh"] = round(
                                        snapshot.export_off_kwh + snapshot.export_peak_kwh, 2
                                    )
                    
                    # Get solar energy from billing calculation (month_energy_to_date.solar_kwh)
                    # This is needed for savings and CO2 calculations
                    if billing_cfg:
                        try:
                            tz = get_configured_timezone()
                            month_start, month_end, month_label = _get_current_billing_month(today, billing_cfg.anchor_day, tz)
                            month_start_local = month_start
                            target_datetime = tz.localize(datetime.combine(today, datetime.max.time()))
                            
                            energy_calc = EnergyCalculator(solar_app.logger.path)
                            month_energy_to_date = _aggregate_hourly_for_billing_month(
                                energy_calc=energy_calc,
                                inverter_id="all",
                                start=month_start_local,
                                end=target_datetime + timedelta(seconds=1),
                                billing_cfg=billing_cfg,
                            )
                            monthly_energy["solar_energy_kwh"] = round(month_energy_to_date.solar_kwh, 2)
                            
                            log.debug(f"API /api/home/now: Solar energy from billing calculation: {monthly_energy['solar_energy_kwh']} kWh")
                        except Exception as e:
                            log.debug(f"Error getting solar energy from billing calculation: {e}")
                            # Fallback: calculate solar separately
                            try:
                                tz = get_configured_timezone()
                                month_start, month_end, month_label = _get_current_billing_month(today, billing_cfg.anchor_day, tz)
                                month_start_date = month_start.date()
                                current_date = month_start_date
                                energy_calc = EnergyCalculator(solar_app.logger.path)
                                while current_date <= today:
                                    for array_cfg in solar_app.cfg.arrays:
                                        for inv_id in array_cfg.inverter_ids:
                                            try:
                                                inv_daily = energy_calc.get_daily_energy_summary(inv_id, current_date)
                                                monthly_energy["solar_energy_kwh"] += inv_daily.get('total_solar_kwh', 0.0) or 0.0
                                            except Exception as e:
                                                log.debug(f"Error getting solar energy for inverter {inv_id} on {current_date}: {e}")
                                    current_date += timedelta(days=1)
                                monthly_energy["solar_energy_kwh"] = round(monthly_energy["solar_energy_kwh"], 2)
                            except Exception as e2:
                                log.debug(f"Error in fallback solar calculation: {e2}")
                    else:
                        log.debug("API /api/home/now: No billing config found")
                    
                    # Calculate savings and CO2 prevention
                    if monthly_energy["solar_energy_kwh"] > 0:
                        # Get tariff rates for savings calculation
                        if billing_cfg:
                            import_price = getattr(billing_cfg, 'price_offpeak_import', 50.0)  # Default 50 PKR/kWh
                            export_price = getattr(billing_cfg, 'price_offpeak_settlement', 22.0)  # Default 22 PKR/kWh
                        else:
                            import_price = 50.0  # Default 50 PKR/kWh
                            export_price = 22.0  # Default 22 PKR/kWh
                        
                        # Total saved = (Solar Energy * Import Price) - (Grid Export * Export Price)
                        # This represents money saved by using solar instead of buying from grid
                        total_saved = (monthly_energy["solar_energy_kwh"] * import_price) - (monthly_energy["grid_export_energy_kwh"] * export_price)
                        financial_metrics["total_saved_pkr"] = round(total_saved, 2)
                        
                        # Calculate CO2 prevention
                        # Default CO2 emission factor: 0.5 kg CO2 per kWh (typical for grid electricity)
                        co2_emission_factor = 0.5  # kg CO2 per kWh
                        co2_prevented = monthly_energy["solar_energy_kwh"] * co2_emission_factor
                        financial_metrics["co2_prevented_kg"] = round(co2_prevented, 2)
                        
                        log.debug(f"API /api/home/now: Financial metrics - bill: {financial_metrics['total_bill_pkr']} PKR, saved: {financial_metrics['total_saved_pkr']} PKR, CO2: {financial_metrics['co2_prevented_kg']} kg")
                else:
                    log.debug("API /api/home/now: Skipping monthly energy calculation - missing arrays, logger, or logger.path")
            except Exception as e:
                log.error(f"API /api/home/now: Error calculating monthly energy and financial metrics: {e}", exc_info=True)
            
            home_dict = home_tel.model_dump()
            home_dict["daily_energy"] = daily_energy
            home_dict["monthly_energy"] = monthly_energy
            home_dict["financial_metrics"] = financial_metrics
            
            # Add hierarchy information
            target_system_id = "system"  # Default
            if hasattr(solar_app, 'hierarchy_systems') and solar_app.hierarchy_systems:
                target_system_id = next(iter(solar_app.hierarchy_systems.keys()))
                system = solar_app.hierarchy_systems[target_system_id]
                home_dict["system_id"] = target_system_id
                home_dict["system_name"] = system.name
                home_dict["system_description"] = system.description
                home_dict["timezone"] = system.timezone
                
                # Build proper hierarchy structure with nested arrays
                inverter_arrays_hierarchy = []
                battery_arrays_hierarchy = []
                
                # Build inverter arrays with nested inverters
                for inv_array in system.inverter_arrays:
                    # Get array telemetry if available
                    array_tel = array_telemetry.get(inv_array.array_id)
                    
                    # Build inverters list for this array
                    inverters_list = []
                    for inverter in inv_array.inverters:
                        inv_tel_dict = solar_app.get_now(inverter.inverter_id) if hasattr(solar_app, 'get_now') else None
                        inverter_data = {
                            "inverter_id": inverter.inverter_id,
                            "name": inverter.name,
                            "array_id": inverter.array_id,
                            "system_id": inverter.system_id,
                            "model": inverter.model,
                            "serial_number": inverter.serial_number,
                            "vendor": inverter.vendor,
                            "phase_type": inverter.phase_type,
                        }
                        # Add telemetry if available
                        if inv_tel_dict:
                            inverter_data["telemetry"] = inv_tel_dict
                        inverters_list.append(inverter_data)
                    
                    # Build inverter array structure
                    inv_array_data = {
                        "array_id": inv_array.array_id,
                        "name": inv_array.name,
                        "system_id": inv_array.system_id,
                        "inverters": inverters_list,
                        "attached_battery_array_id": inv_array.attached_battery_array_id,
                    }
                    # Add array telemetry if available
                    if array_tel:
                        inv_array_data["telemetry"] = array_tel.model_dump() if hasattr(array_tel, 'model_dump') else array_tel
                    inverter_arrays_hierarchy.append(inv_array_data)
                
                # Build battery arrays with nested battery packs
                for bat_array in system.battery_arrays:
                    # Build battery packs list for this array
                    battery_packs_list = []
                    for pack in bat_array.battery_packs:
                        pack_id = pack.pack_id
                        # Get battery telemetry if available
                        pack_tel = None
                        if hasattr(solar_app, 'battery_last') and solar_app.battery_last:
                            if isinstance(solar_app.battery_last, dict):
                                pack_tel = solar_app.battery_last.get(pack_id)
                        
                        pack_data = {
                            "pack_id": pack.pack_id,
                            "name": pack.name,
                            "battery_array_id": pack.battery_array_id,
                            "system_id": pack.system_id,
                            "chemistry": pack.chemistry,
                            "nominal_kwh": pack.nominal_kwh,
                            "max_charge_kw": pack.max_charge_kw,
                            "max_discharge_kw": pack.max_discharge_kw,
                        }
                        # Add telemetry if available
                        if pack_tel:
                            pack_data["telemetry"] = {
                                "soc": pack_tel.soc,
                                "voltage": pack_tel.voltage,
                                "current": pack_tel.current,
                                "power": pack_tel.voltage * pack_tel.current if pack_tel.voltage and pack_tel.current else None,
                                "temperature": pack_tel.temperature,
                                "ts": pack_tel.ts,
                            }
                        battery_packs_list.append(pack_data)
                    
                    # Build battery array structure
                    bat_array_data = {
                        "battery_array_id": bat_array.battery_array_id,
                        "name": bat_array.name,
                        "system_id": bat_array.system_id,
                        "battery_packs": battery_packs_list,
                        "attached_inverter_array_id": bat_array.attached_inverter_array_id,
                    }
                    battery_arrays_hierarchy.append(bat_array_data)
                
                # Add hierarchy structure to response
                home_dict["inverter_arrays"] = inverter_arrays_hierarchy
                home_dict["battery_arrays"] = battery_arrays_hierarchy
                
                # Keep the flat arrays list for backward compatibility, but add hierarchy info
                if "arrays" in home_dict and isinstance(home_dict["arrays"], list):
                    for array_data in home_dict["arrays"]:
                        if "array_id" in array_data:
                            array_id = array_data["array_id"]
                            array_data["system_id"] = target_system_id
                            # Find matching inverter array and add hierarchy info
                            for inv_array in system.inverter_arrays:
                                if inv_array.array_id == array_id:
                                    array_data["system_id"] = inv_array.system_id
                                    array_data["array_name"] = inv_array.name
                                    array_data["inverter_ids"] = inv_array.inverter_ids
                                    array_data["attached_battery_array_id"] = inv_array.attached_battery_array_id
                                    break
            else:
                # Fallback: ensure arrays have basic info
                if "arrays" in home_dict and isinstance(home_dict["arrays"], list):
                    for array_data in home_dict["arrays"]:
                        if "array_id" in array_data:
                            array_data["system_id"] = target_system_id
            
            return {
                "status": "ok",
                "system": home_dict  # Changed from "home" to "system" to reflect hierarchy
            }
        except Exception as e:
            log.error(f"Error in /api/home/now: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    @app.get("/api/now")
    def api_now(inverter_id: str = None, array_id: Optional[str] = None) -> Dict[str, Any]:
        """Get current telemetry data. 
        If inverter_id is None, empty string, or 'all', returns consolidated sums across all inverters.
        If a specific inverter_id is provided, returns data for that inverter only.
        If array_id is provided, filters by array."""
        try:
            # Default to "all" if None or empty
            if inverter_id is None or inverter_id == "":
                inverter_id = "all"
                
            log.debug(f"API /api/now called for inverter_id: {inverter_id}")
            log.debug(f"solar_app type: {type(solar_app)}")
            log.debug(f"solar_app has get_now: {hasattr(solar_app, 'get_now')}")
            
            # Filter by array_id if provided
            if array_id:
                # Get inverters for this array
                if solar_app and hasattr(solar_app, 'cfg') and solar_app.cfg.arrays:
                    array_cfg = next((a for a in solar_app.cfg.arrays if a.id == array_id), None)
                    if array_cfg:
                        inverter_ids = array_cfg.inverter_ids
                    else:
                        return {"status": "error", "error": f"Array '{array_id}' not found"}
                else:
                    return {"status": "error", "error": "No arrays configured"}
            
            # Aggregated mode
            if inverter_id in ("all", "ALL"):
                inverter_ids: List[str] = []
                if solar_app and getattr(solar_app, 'cfg', None) and getattr(solar_app.cfg, 'inverters', None):
                    # If array_id filter is set, use it; otherwise get all inverters
                    if array_id:
                        # Already filtered above
                        pass
                    else:
                        inverter_ids = [inv.id for inv in solar_app.cfg.inverters if getattr(inv, 'id', None)]
                # Fallback to DB if needed
                if not inverter_ids and solar_app and getattr(solar_app, 'logger', None) and getattr(solar_app.logger, 'path', None):
                    import sqlite3
                    try:
                        conn = sqlite3.connect(solar_app.logger.path)
                        cur = conn.cursor()
                        cur.execute("SELECT DISTINCT inverter_id FROM energy_samples ORDER BY inverter_id")
                        rows = cur.fetchall()
                        inverter_ids = [r[0] for r in rows if r and r[0]]
                    finally:
                        try:
                            conn.close()
                        except Exception:
                            pass

                totals: Dict[str, Any] = {
                    "pv_power_w": 0.0,
                    "load_power_w": 0.0,
                    "grid_power_w": 0.0,
                    "batt_power_w": 0.0,
                    "batt_voltage_v": 0.0,
                    "batt_current_a": 0.0,
                    "batt_soc_pct": 0.0,
                    "inverter_mode": "Unknown",
                    "today_energy": 0.0,
                    "today_load_energy": 0.0,
                    "today_import_energy": 0.0,
                    "today_export_energy": 0.0,
                    "today_battery_charge_energy": 0.0,
                    "today_battery_discharge_energy": 0.0,
                    "today_peak_power": 0.0,
                }
                last_tel: Dict[str, Any] = {}
                for inv in inverter_ids:
                    tel_i = solar_app.get_now(inv) or {}
                    last_tel = tel_i or last_tel
                    totals["pv_power_w"] += float(tel_i.get("pv_power_w", 0) or 0)
                    totals["load_power_w"] += float(tel_i.get("load_power_w", 0) or 0)
                    totals["grid_power_w"] += float(tel_i.get("grid_power_w", 0) or 0)
                    
                    # Battery voltage and current - use average for aggregated view
                    bv = tel_i.get("batt_voltage_v")
                    ba = tel_i.get("batt_current_a")
                    if bv is not None:
                        totals["batt_voltage_v"] += float(bv)
                    if ba is not None:
                        totals["batt_current_a"] += float(ba)
                    
                    # Battery SOC - use average
                    soc = tel_i.get("batt_soc_pct")
                    if soc is not None:
                        totals["batt_soc_pct"] += float(soc)
                    
                    # Inverter mode - use the last non-unknown mode
                    mode = tel_i.get("inverter_mode")
                    if mode and mode != "Unknown":
                        totals["inverter_mode"] = mode
                    
                    # Peak power - use maximum
                    peak = tel_i.get("today_peak_power")
                    if peak is not None:
                        totals["today_peak_power"] = max(totals["today_peak_power"], float(peak))
                    
                    # prefer batt_power_w if present, else derive from voltage/current if available
                    if "batt_power_w" in tel_i and tel_i.get("batt_power_w") is not None:
                        totals["batt_power_w"] += float(tel_i.get("batt_power_w") or 0)
                    else:
                        if bv is not None and ba is not None:
                            totals["batt_power_w"] += float(bv) * float(ba)
                    # energy fields from common keys or extra map
                    ex = (tel_i.get("extra", {}) or {})
                    totals["today_energy"] += float(ex.get("today_energy", tel_i.get("today_energy", 0)) or 0)
                    # Total load should include both inverter's today_load_energy and EPS/load-to-backup (daily_energy_to_eps)
                    load_main = float(ex.get("today_load_energy", tel_i.get("today_load_energy", 0)) or 0)
                    load_eps = float(ex.get("daily_energy_to_eps", tel_i.get("daily_energy_to_eps", 0)) or 0)
                    totals["today_load_energy"] += (load_main + load_eps)
                    totals["today_import_energy"] += float(ex.get("today_import_energy", tel_i.get("today_import_energy", 0)) or 0)
                    totals["today_export_energy"] += float(ex.get("today_export_energy", tel_i.get("today_export_energy", 0)) or 0)
                    # battery charge/discharge energy may have different keys
                    bc = ex.get("battery_daily_charge_energy", ex.get("today_battery_charge_energy", tel_i.get("today_battery_charge_energy", 0)))
                    bd = ex.get("battery_daily_discharge_energy", ex.get("today_battery_discharge_energy", tel_i.get("today_battery_discharge_energy", 0)))
                    totals["today_battery_charge_energy"] += float(bc or 0)
                    totals["today_battery_discharge_energy"] += float(bd or 0)

                # Calculate averages for voltage, current, and SOC
                inv_count = len(inverter_ids) if inverter_ids else 1
                avg_voltage = totals["batt_voltage_v"] / inv_count if inv_count > 0 else 0
                avg_current = totals["batt_current_a"] / inv_count if inv_count > 0 else 0
                avg_soc = totals["batt_soc_pct"] / inv_count if inv_count > 0 else 0
                
                # Compose consolidated telemetry
                consolidated = {
                    "ts": last_tel.get("ts"),
                    "pv_power_w": round(totals["pv_power_w"], 2),
                    "load_power_w": round(totals["load_power_w"], 2),
                    "grid_power_w": round(totals["grid_power_w"], 2),
                    "batt_power_w": round(totals["batt_power_w"], 2),
                    "batt_voltage_v": round(avg_voltage, 2),
                    "batt_current_a": round(avg_current, 2),
                    "batt_soc_pct": round(avg_soc, 2),
                    "inverter_mode": totals["inverter_mode"],
                    "today_energy": round(totals["today_energy"], 2),
                    "today_load_energy": round(totals["today_load_energy"], 2),
                    "today_import_energy": round(totals["today_import_energy"], 2),
                    "today_export_energy": round(totals["today_export_energy"], 2),
                    "today_battery_charge_energy": round(totals["today_battery_charge_energy"], 2),
                    "today_battery_discharge_energy": round(totals["today_battery_discharge_energy"], 2),
                    "today_peak_power": round(totals["today_peak_power"], 2),
                    "extra": {"today_energy": round(totals["today_energy"], 2)}
                }
                
                # Add inverter metadata for consolidated view
                from solarhub.inverter_metadata import InverterMetadata
                metadata = InverterMetadata(
                    phase_type=None,  # Mixed phase types in array - set to None
                    inverter_count=inv_count
                )
                consolidated["_metadata"] = metadata.to_dict()
                
                # Add hierarchy information
                if array_id:
                    consolidated["array_id"] = array_id
                    # Find system_id from hierarchy
                    if hasattr(solar_app, 'hierarchy_systems') and solar_app.hierarchy_systems:
                        for system in solar_app.hierarchy_systems.values():
                            for inv_array in system.inverter_arrays:
                                if inv_array.array_id == array_id:
                                    consolidated["system_id"] = inv_array.system_id
                                    break
                else:
                    # For "all" without array filter, try to determine from inverters
                    if inverter_ids and hasattr(solar_app, 'hierarchy_systems') and solar_app.hierarchy_systems:
                        # Get system_id from first inverter
                        for system in solar_app.hierarchy_systems.values():
                            for inv_array in system.inverter_arrays:
                                for inv in inv_array.inverters:
                                    if inv.inverter_id in inverter_ids:
                                        consolidated["system_id"] = inv.system_id
                                        consolidated["array_id"] = inv.array_id
                                        break
                                if "system_id" in consolidated:
                                    break
                            if "system_id" in consolidated:
                                break
                
                return {"inverter_id": "all", "now": consolidated}

            # Get telemetry from solar_app (already converted to dict) for a single inverter
            tel = solar_app.get_now(inverter_id)
            log.debug(f"get_now returned: {type(tel)} - {tel is not None}")
            
            if not tel:
                return {
                    "inverter_id": inverter_id,
                    "now": None,
                    "error": "No telemetry data available"
                }
            
            # Get all available telemetry data
            extra = tel.get("extra", {}) or {}
            
            # Try to use mapper if available from adapter (for consistency)
            # Get adapter from solar_app to access mapper
            adapter = None
            mapper = None
            if inverter_id != "all":
                for rt in solar_app.inverters:
                    if rt.cfg.id == inverter_id:
                        adapter = rt.adapter
                        if hasattr(adapter, 'mapper') and adapter.mapper:
                            mapper = adapter.mapper
                        break
            
            # Debug: Log what we have in tel and extra for troubleshooting
            log.debug(f"API /api/now - tel type: {type(tel)}")
            log.debug(f"API /api/now - tel keys: {list(tel.keys()) if isinstance(tel, dict) else 'not dict'}")
            log.debug(f"API /api/now - extra type: {type(extra)}, extra keys: {list(extra.keys()) if extra else 'empty'}")
            if extra:
                log.debug(f"API /api/now - Sample extra values: inverter_mode={extra.get('inverter_mode')}, "
                         f"battery_power_w={extra.get('battery_power_w')}, "
                         f"device_serial_number={extra.get('device_serial_number')}, "
                         f"rated_power_w={extra.get('rated_power_w')}, "
                         f"battery_temp_c={extra.get('battery_temp_c')}")
            # Check direct tel fields
            log.debug(f"API /api/now - Direct tel fields: batt_power_w={tel.get('batt_power_w')}, "
                     f"inverter_mode={tel.get('inverter_mode')}")
            if mapper:
                log.debug(f"API /api/now - Using TelemetryMapper with {len(mapper.device_to_standard)} mappings")
            
            # Get adapter type for driver detection
            adapter_type = None
            if inverter_id != "all":
                for rt in solar_app.inverters:
                    if rt.cfg.id == inverter_id:
                        adapter_type = getattr(rt.adapter, '__class__', None)
                        if adapter_type:
                            adapter_name = adapter_type.__name__.lower()
                            if "powdrive" in adapter_name:
                                adapter_type = "Powdrive"
                            elif "senergy" in adapter_name:
                                adapter_type = "Senergy"
                            else:
                                adapter_type = None
                        break
            
            # Normalize keys expected by UI with comprehensive telemetry
            # If mapper is available, use it to ensure standardized field names
            # Otherwise, use manual normalization with fallbacks for backward compatibility
            normalized = {
                # Timestamp
                "ts": tel.get("ts") or _now_iso(),
                
                # Power flows - prefer standardized IDs
                "pv_power_w": tel.get("pv_power_w") or extra.get("pv_power_w") or extra.get("pv_power") or tel.get("pv_power"),
                "pv1_power_w": extra.get("pv1_power_w") or extra.get("mppt1_power_w") or extra.get("mppt1_power"),
                "pv2_power_w": extra.get("pv2_power_w") or extra.get("mppt2_power_w") or extra.get("mppt2_power"),
                "load_power_w": tel.get("load_power_w") or extra.get("load_power_w") or tel.get("phase_r_watt_of_load"),
                "grid_power_w": tel.get("grid_power_w") or extra.get("grid_power_w") or tel.get("phase_r_watt_of_grid"),
                
                # Three-phase Load data
                "load_l1_power_w": extra.get("load_l1_power_w"),
                "load_l2_power_w": extra.get("load_l2_power_w"),
                "load_l3_power_w": extra.get("load_l3_power_w"),
                "load_l1_voltage_v": extra.get("load_l1_voltage_v"),
                "load_l2_voltage_v": extra.get("load_l2_voltage_v"),
                "load_l3_voltage_v": extra.get("load_l3_voltage_v"),
                "load_l1_current_a": extra.get("load_l1_current_a"),
                "load_l2_current_a": extra.get("load_l2_current_a"),
                "load_l3_current_a": extra.get("load_l3_current_a"),
                "load_frequency_hz": extra.get("load_frequency_hz"),
                
                # Three-phase Grid data
                "grid_l1_power_w": extra.get("grid_l1_power_w"),
                "grid_l2_power_w": extra.get("grid_l2_power_w"),
                "grid_l3_power_w": extra.get("grid_l3_power_w"),
                "grid_l1_voltage_v": extra.get("grid_l1_voltage_v"),
                "grid_l2_voltage_v": extra.get("grid_l2_voltage_v"),
                "grid_l3_voltage_v": extra.get("grid_l3_voltage_v"),
                "grid_l1_current_a": extra.get("grid_l1_current_a"),
                "grid_l2_current_a": extra.get("grid_l2_current_a"),
                "grid_l3_current_a": extra.get("grid_l3_current_a"),
                "grid_frequency_hz": extra.get("grid_frequency_hz"),
                "grid_line_voltage_ab_v": extra.get("grid_line_voltage_ab_v"),
                "grid_line_voltage_bc_v": extra.get("grid_line_voltage_bc_v"),
                "grid_line_voltage_ca_v": extra.get("grid_line_voltage_ca_v"),
                
                # Battery data - prefer standardized IDs
                "batt_soc_pct": tel.get("batt_soc_pct") or tel.get("battery_soc_pct") or tel.get("battery_soc") or extra.get("battery_soc_pct") or extra.get("battery_soc"),
                "batt_voltage_v": tel.get("batt_voltage_v") or extra.get("battery_voltage_v") or extra.get("battery_voltage"),
                "batt_current_a": tel.get("batt_current_a") or extra.get("battery_current_a") or extra.get("battery_current"),
                "batt_temp_c": extra.get("battery_temp_c") or extra.get("battery_temperature"),
                "batt_power_w": tel.get("batt_power_w") or extra.get("battery_power_w") or extra.get("battery_power") or tel.get("battery_power_w") or tel.get("battery_power"),
                
                # Inverter data - prefer standardized IDs
                "inverter_mode": tel.get("inverter_mode") or extra.get("inverter_mode") or extra.get("hybrid_work_mode") or tel.get("hybrid_work_mode"),
                "inverter_temp_c": tel.get("inverter_temp_c") or extra.get("inverter_temp_c") or extra.get("inner_temperature"),
                "error_code": extra.get("error_code"),
                
                # Device info - normalize to consistent field names for all adapters
                # Keep both original and normalized names for backward compatibility
                "device_model": extra.get("device_model"),
                "device_serial_number": extra.get("device_serial_number"),
                "rated_power_w": extra.get("rated_power_w") or extra.get("rated_power"),
                # Normalized field names for frontend (consistent across all adapters)
                "model_name": extra.get("device_model"),  # Normalized name
                "serial_number": extra.get("device_serial_number"),  # Normalized name
                "max_ac_output_power_w": extra.get("rated_power_w") or extra.get("rated_power"),  # Normalized name
                # Driver - detect from adapter type, extra, or inverter_id
                "driver": extra.get("driver") or adapter_type or (
                    "Powdrive" if inverter_id and "powdrive" in inverter_id.lower() else "Senergy"
                ),
                # Production type and grid_phases will be set after metadata is created (see below)
                # MPPT connections - get from extra
                "mppt_connections": extra.get("mppt_connections") or extra.get("mppt_count") or None,
                
                # Energy totals
                "today_energy": extra.get("today_energy"),
                "total_energy": extra.get("total_energy"),
                "today_peak_power": extra.get("today_peak_power"),
                # Include both reported load totals if available
                "today_load_energy": (
                    (extra.get("today_load_energy") or 0)
                    + (extra.get("daily_energy_to_eps") or 0)
                ),
                "today_import_energy": extra.get("today_import_energy") or extra.get("today_grid_import_energy"),
                "today_export_energy": extra.get("today_export_energy") or extra.get("today_grid_export_energy"),
                "today_battery_charge_energy": extra.get("battery_daily_charge_energy"),
                "today_battery_discharge_energy": extra.get("battery_daily_discharge_energy"),
                
                # Configuration
                "grid_charge": extra.get("grid_charge"),
                "maximum_grid_charger_power": extra.get("maximum_grid_charger_power"),
                "maximum_charger_power": extra.get("maximum_charger_power"),
                "maximum_discharger_power": extra.get("maximum_discharger_power"),
                "maximum_feed_in_grid_power": extra.get("maximum_feed_in_grid_power") or extra.get("zero_export_power_w"),
                "off_grid_mode": extra.get("off_grid_mode"),
                "off_grid_start_up_battery_capacity": extra.get("off_grid_start_up_battery_capacity"),
                
                # TOU Windows
                "charge_start_time_1": extra.get("charge_start_time_1"),
                "charge_end_time_1": extra.get("charge_end_time_1"),
                "charge_power_1": extra.get("charge_power_1"),
                "charger_end_soc_1": extra.get("charger_end_soc_1"),
                "discharge_start_time_1": extra.get("discharge_start_time_1"),
                "discharge_end_time_1": extra.get("discharge_end_time_1"),
                "discharge_power_1": extra.get("discharge_power_1"),
                "discharge_end_soc_1": extra.get("discharge_end_soc_1"),
                
                # Include extra dict for any additional fields - make it JSON-serializable
                "extra": _make_json_serializable(extra),
            }
            
            # If mapper is available, ensure all standardized fields are present
            if mapper:
                # Get all standardized field names from mapper
                for standard_field in mapper.get_all_standard_fields():
                    # If standard field not in normalized, try to get from extra using device-specific keys
                    if standard_field not in normalized or normalized[standard_field] is None:
                        device_fields = mapper.get_device_fields(standard_field)
                        for device_field in device_fields:
                            if device_field in extra and extra[device_field] is not None:
                                normalized[standard_field] = extra[device_field]
                                log.debug(f"API /api/now - Mapped {device_field} -> {standard_field}")
                                break
            
            # Add inverter metadata (phase type, inverter count)
            from solarhub.inverter_metadata import get_inverter_metadata
            
            # Get inverter count
            inverter_count = 1 if inverter_id != "all" else len(solar_app.inverters) if solar_app.inverters else 1
            
            # Get phase type from config or detect from telemetry
            config_phase_type = None
            if inverter_id != "all":
                for rt in solar_app.inverters:
                    if rt.cfg.id == inverter_id:
                        config_phase_type = getattr(rt.cfg, 'phase_type', None)
                        break
            
            # Get phase type from extra or config for use in normalization
            phase_type_from_extra = extra.get("phase_type")
            phase_type_to_use = phase_type_from_extra or config_phase_type
            
            # Now update normalized fields with proper phase type information
            if not normalized.get("grid_phases"):
                if phase_type_to_use == "three" or phase_type_to_use == "3-phase":
                    normalized["grid_phases"] = 3
                elif phase_type_to_use == "single" or phase_type_to_use == "1-phase":
                    normalized["grid_phases"] = 1
            
            if not normalized.get("production_type"):
                if phase_type_to_use == "three" or phase_type_to_use == "3-phase":
                    normalized["production_type"] = "3-Phase Hybrid"
                elif extra.get("inverter_type") in (3, 5):
                    normalized["production_type"] = "Hybrid"
            
            metadata = get_inverter_metadata(normalized, config_phase_type, inverter_count)
            normalized["_metadata"] = metadata.to_dict()
            
            # Update grid_phases and production_type from metadata if not already set
            if not normalized.get("grid_phases") and metadata.phase_type:
                if metadata.phase_type == "three":
                    normalized["grid_phases"] = 3
                elif metadata.phase_type == "single":
                    normalized["grid_phases"] = 1
            
            if not normalized.get("production_type") and metadata.phase_type:
                if metadata.phase_type == "three":
                    normalized["production_type"] = "3-Phase Hybrid"
                else:
                    normalized["production_type"] = "Hybrid"
            
            # Make the entire normalized dict JSON-serializable to prevent circular references
            normalized = _make_json_serializable(normalized)
            
            # Add hierarchy information to response
            if hasattr(solar_app, 'hierarchy_systems') and solar_app.hierarchy_systems:
                for system in solar_app.hierarchy_systems.values():
                    for inv_array in system.inverter_arrays:
                        for inv in inv_array.inverters:
                            if inv.inverter_id == inverter_id:
                                normalized["system_id"] = inv.system_id
                                normalized["array_id"] = inv.array_id
                                break
                        if "system_id" in normalized:
                            break
                    if "system_id" in normalized:
                        break
            elif hasattr(solar_app, '_hierarchy_inverters') and inverter_id in solar_app._hierarchy_inverters:
                inv = solar_app._hierarchy_inverters[inverter_id]
                normalized["system_id"] = inv.system_id
                normalized["array_id"] = inv.array_id
            
            return {"inverter_id": inverter_id, "now": normalized}
            
        except Exception as e:
            log.error(f"Error in /api/now: {e}", exc_info=True)
            return {
                "inverter_id": inverter_id,
                "now": None,
                "error": str(e)
            }

    @app.get("/api/forecast")
    def api_forecast(inverter_id: str = "senergy1", array_id: Optional[str] = None) -> Dict[str, Any]:
        """Get PV forecast data for today. If inverter_id is 'all', sum forecasts across inverters.
        If array_id is provided, returns forecast for that array."""
        try:
            log.info(f"API /api/forecast called for inverter_id: {inverter_id}, array_id: {array_id}")
            
            # If array_id is provided, use the array's scheduler
            scheduler = None
            if array_id:
                scheduler = solar_app.smart_schedulers.get(array_id) if hasattr(solar_app, 'smart_schedulers') else None
                if not scheduler:
                    return {"status": "error", "error": f"Array '{array_id}' not found or has no scheduler"}
            else:
                # Use legacy scheduler or first available array scheduler
                scheduler = solar_app.smart if hasattr(solar_app, 'smart') and solar_app.smart else None
                if not scheduler and hasattr(solar_app, 'smart_schedulers') and solar_app.smart_schedulers:
                    scheduler = next(iter(solar_app.smart_schedulers.values()))
            
            # Try to get real forecast data from smart scheduler
            if scheduler and hasattr(scheduler, 'weather'):
                import asyncio
                import pandas as pd
                
                # Get current time in the scheduler's timezone
                tznow = pd.Timestamp.now(scheduler.tz)
                
                # Get weather factors and enhanced forecast
                try:
                    # Run async function in sync context
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Get weather factors
                    factors = loop.run_until_complete(scheduler.weather.day_factors())
                    
                    # Get enhanced forecast if available
                    enhanced_forecast = None
                    if hasattr(scheduler.weather, 'get_enhanced_forecast'):
                        enhanced_forecast = loop.run_until_complete(scheduler.weather.get_enhanced_forecast(days=1))
                    
                    loop.close()
                    
                    # Generate hourly forecast data
                    data = []
                    today_str = tznow.strftime('%Y-%m-%d')
                    today_weather = enhanced_forecast.get(today_str) if enhanced_forecast else None
                    
                    # Get PV estimators for the inverter(s)
                    # If array_id is provided, filter by array; otherwise use all or specified inverter
                    inverter_ids: List[str] = []
                    if array_id:
                        # Get inverters in this array
                        array_cfg = next((a for a in (solar_app.cfg.arrays or []) if a.id == array_id), None)
                        if array_cfg:
                            inverter_ids = [inv_id for inv_id in array_cfg.inverter_ids if inv_id in scheduler.inv_estimators]
                        else:
                            return {"status": "error", "error": f"Array '{array_id}' not found"}
                    elif inverter_id in (None, "", "all", "ALL"):
                        inverter_ids = list(scheduler.inv_estimators.keys())
                    else:
                        inverter_ids = [inverter_id] if inverter_id in scheduler.inv_estimators else []
                    
                    for hour in range(6, 19):  # 6 AM to 6 PM
                        time_str = f"{hour:02d}:00"
                        
                        # Calculate solar position factor (simplified)
                        import math
                        hour_of_day = hour - 6
                        solar_factor = math.sin((hour_of_day / 12) * math.pi) if hour_of_day >= 0 else 0
                        
                        # Get forecast from estimators across selected inverters
                        predicted_power = 0
                        for inv in inverter_ids:
                            inverter_estimators = scheduler.inv_estimators.get(inv, [])
                            for estimator in inverter_estimators:
                                if hasattr(estimator, 'estimate_hourly_pv_kw'):
                                    try:
                                        hourly_kw = estimator.estimate_hourly_pv_kw(
                                            hour, factors.get("today", 1.0), enhanced_weather=today_weather
                                        )
                                        predicted_power += hourly_kw * 1000  # Convert to watts
                                    except:
                                        # Fallback to simple calculation
                                        predicted_power += 5000 * solar_factor * factors.get("today", 1.0)
                                else:
                                    # Fallback calculation
                                    predicted_power += 5000 * solar_factor * factors.get("today", 1.0)
                        
                        # Get actual generation if available
                        actual_power = 0
                        if hour <= tznow.hour:
                            # Get current telemetry for actual data (sum if 'all')
                            if inverter_id in (None, "", "all", "ALL"):
                                actual_power = 0
                                for inv in inverter_ids:
                                    tel = solar_app.get_now(inv)
                                    if tel and hour == tznow.hour:
                                        actual_power += tel.get("pv_power_w", 0) or 0
                            else:
                                tel = solar_app.get_now(inverter_id)
                                if tel:
                                    if hour == tznow.hour:
                                        actual_power = tel.get("pv_power_w", 0)
                                    else:
                                        actual_power = 0
                        
                        # Get cloud cover from enhanced weather if available
                        cloud_cover = 20  # Default
                        if today_weather and 'hourly' in today_weather:
                            hourly_data = today_weather['hourly']
                            if hour < len(hourly_data):
                                cloud_cover = hourly_data[hour].get('cloud_cover', 20)
                        
                        data.append({
                            "time": time_str,
                            "generated": round(actual_power),
                            "predicted": round(predicted_power),
                            "cloudCover": round(cloud_cover)
                        })
                    
                    # Get total daily generation from telemetry (sum for 'all')
                    total_daily_generation = 0
                    try:
                        if array_id or inverter_id in (None, "", "all", "ALL"):
                            for inv in inverter_ids:
                                tel = solar_app.get_now(inv)
                                if tel:
                                    total_daily_generation += tel.get("today_energy", 0) or 0
                        else:
                            tel = solar_app.get_now(inverter_id)
                            log.debug(f"Forecast endpoint - telemetry data: {tel}")
                            if tel:
                                total_daily_generation = tel.get("today_energy", 0)  # in kWh
                                log.debug(f"Forecast endpoint - total_daily_generation: {total_daily_generation}")
                    except Exception as e:
                        log.error(f"Error getting telemetry in forecast endpoint: {e}")
                        pass
                    
                    result = {
                        "inverter_id": inverter_id if not array_id else None,
                        "array_id": array_id,
                        "forecast": data,
                        "weather_factor": factors.get("today", 1.0),
                        "source": "smart_scheduler",
                        "total_daily_generation_kwh": total_daily_generation
                    }
                    return result
                    
                except Exception as inner_e:
                    log.error(f"Error in forecast calculation: {inner_e}")
                    import traceback
                    log.error(f"Traceback: {traceback.format_exc()}")
                    # Fall back to mock data - this will be handled by the outer fallback
                    pass
                    
        except Exception as e:
            log.error(f"Error getting smart scheduler forecast: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
            # Fall back to mock data
            pass
        
        # Fallback to mock data if smart scheduler is not available
        import random
        from datetime import datetime, timedelta
        
        data = []
        from solarhub.timezone_utils import now_configured
        now = now_configured()
        start_hour = 6
        end_hour = 18
        
        for hour in range(start_hour, end_hour + 1):
            time_str = f"{hour:02d}:00"
            hour_of_day = hour - start_hour
            max_power = 20000
            
            # Generate realistic solar curve
            import math
            solar_factor = math.sin((hour_of_day / (end_hour - start_hour)) * math.pi)
            generated = max(0, solar_factor * max_power * 0.7)
            predicted = max(0, solar_factor * max_power * 0.85)
            cloud_cover = random.uniform(10, 40)
            
            data.append({
                "time": time_str,
                "generated": round(generated),
                "predicted": round(predicted),
                "cloudCover": round(cloud_cover)
            })
        
        # Get total daily generation from telemetry even in fallback mode
        total_daily_generation = 0
        try:
            tel = solar_app.get_now(inverter_id)
            if tel:
                total_daily_generation = tel.get("today_energy", 0)  # in kWh
        except:
            pass
        
        return {
            "inverter_id": inverter_id, 
            "forecast": data, 
            "source": "mock",
            "total_daily_generation_kwh": total_daily_generation
        }

    @app.get("/api/overview")
    def api_overview(inverter_id: str = "senergy1", hours: int = 24) -> Dict[str, Any]:
        """Get overview data for the last N hours from database. Supports aggregation when inverter_id='all'."""
        try:
            log.info(f"API /api/overview called for inverter_id: {inverter_id}, hours: {hours}")
            if solar_app.logger and hasattr(solar_app.logger, 'path'):
                import sqlite3
                from datetime import datetime, timedelta
                
                # Calculate time range
                from solarhub.timezone_utils import now_configured
                end_time = now_configured()
                start_time = end_time - timedelta(hours=hours)
                
                # Determine inverter list for aggregation
                inverter_ids: List[str] = []
                if inverter_id in (None, "", "all", "ALL"):
                    # Get all inverters from config or DB
                    if solar_app and getattr(solar_app, 'cfg', None) and getattr(solar_app.cfg, 'inverters', None):
                        inverter_ids = [inv.id for inv in solar_app.cfg.inverters if getattr(inv, 'id', None)]
                    # Fallback to DB
                    if not inverter_ids:
                        try:
                            conn = sqlite3.connect(solar_app.logger.path)
                            cur = conn.cursor()
                            cur.execute("SELECT DISTINCT inverter_id FROM energy_samples ORDER BY inverter_id")
                            rows = cur.fetchall()
                            inverter_ids = [r[0] for r in rows if r and r[0]]
                        finally:
                            try:
                                conn.close()
                            except Exception:
                                pass
                else:
                    inverter_ids = [inverter_id]
                
                # Query database for historical data
                conn = sqlite3.connect(solar_app.logger.path)
                cursor = conn.cursor()
                
                if inverter_id in (None, "", "all", "ALL"):
                    # Aggregate across all inverters
                    query = """
                    SELECT 
                        ts,
                        pv_power_w,
                        load_power_w,
                        soc,
                        batt_voltage_v,
                        batt_current_a,
                        grid_power_w
                    FROM energy_samples 
                    WHERE ts >= ? AND ts <= ?
                    AND (pv_power_w IS NOT NULL OR load_power_w IS NOT NULL OR grid_power_w IS NOT NULL)
                    ORDER BY ts
                    """
                    cursor.execute(query, (start_time.isoformat(), end_time.isoformat()))
                else:
                    # Single inverter
                    query = """
                    SELECT 
                        ts,
                        pv_power_w,
                        load_power_w,
                        soc,
                        batt_voltage_v,
                        batt_current_a,
                        grid_power_w
                    FROM energy_samples 
                    WHERE inverter_id = ? AND ts >= ? AND ts <= ?
                    AND (pv_power_w IS NOT NULL OR load_power_w IS NOT NULL OR grid_power_w IS NOT NULL)
                    ORDER BY ts
                    """
                    cursor.execute(query, (inverter_id, start_time.isoformat(), end_time.isoformat()))
                
                rows = cursor.fetchall()
                conn.close()
                
                # Process data into hourly buckets
                hourly_data = {}
                for row in rows:
                    ts_str, pv_power_w, load_power_w, soc, batt_voltage_v, batt_current_a, grid_power_w = row
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    hour_key = ts.strftime('%H:00')
                    
                    if hour_key not in hourly_data:
                        hourly_data[hour_key] = {
                            'solar': [],
                            'load': [],
                            'battery': [],
                            'grid': []
                        }
                    
                    # Convert kW to W and collect data
                    if pv_power_w is not None:
                        hourly_data[hour_key]['solar'].append(pv_power_w)
                    if load_power_w is not None:
                        hourly_data[hour_key]['load'].append(load_power_w)
                    if batt_voltage_v is not None and batt_current_a is not None:
                        battery_power_w = batt_voltage_v * batt_current_a; hourly_data[hour_key]['battery'].append(battery_power_w)
                    if grid_power_w is not None:
                        hourly_data[hour_key]['grid'].append(grid_power_w)
                
                # Calculate average power for each hour
                data = []
                for hour in range(24):
                    hour_str = f"{hour:02d}:00"
                    if hour_str in hourly_data:
                        hour_data = hourly_data[hour_str]
                        avg_solar = sum(hour_data['solar']) / len(hour_data['solar']) if hour_data['solar'] else 0
                        avg_load = sum(hour_data['load']) / len(hour_data['load']) if hour_data['load'] else 0
                        avg_battery = sum(hour_data['battery']) / len(hour_data['battery']) if hour_data['battery'] else 0
                        avg_grid = sum(hour_data['grid']) / len(hour_data['grid']) if hour_data['grid'] else 0
                        
                        data.append({
                            "time": hour_str,
                            "solar": round(avg_solar),
                            "load": round(avg_load),
                            "battery": round(avg_battery),
                            "grid": round(avg_grid)
                        })
                    else:
                        # No data for this hour, use zeros
                        data.append({
                            "time": hour_str,
                            "solar": 0,
                            "load": 0,
                            "battery": 0,
                            "grid": 0
                        })
                
                return {
                    "inverter_id": inverter_id,
                    "overview": data,
                    "source": "database"
                }
                
        except Exception as e:
            log.error(f"Error getting overview data from database: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
        
        # Fallback to mock data if database is not available
        import random
        from datetime import datetime, timedelta
        
        data = []
        from solarhub.timezone_utils import now_configured
        now = now_configured()
        
        for i in range(hours):
            time = now - timedelta(hours=hours-1-i)
            hour = time.hour
            from solarhub.timezone_utils import now_configured
            time_str = now_configured().strftime("%H:%M")
            
            # Solar generation (only during daylight hours)
            solar = 0
            if 6 <= hour <= 18:
                hour_of_day = hour - 6
                max_power = 10000
                import math
                solar_factor = math.sin((hour_of_day / 12) * math.pi)
                solar = max(0, solar_factor * max_power)
            
            # Load consumption
            load = 2000
            if 6 <= hour <= 22:
                load += random.uniform(1000, 4000)
            else:
                load += random.uniform(0, 500)
            
            # Battery power
            battery = 0
            if solar > load:
                battery = min(solar - load, 3000)
            elif solar < load:
                battery = max(solar - load, -5000)
            
            # Grid power
            grid = load - solar - battery
            
            data.append({
                "time": time_str,
                "solar": round(solar),
                "load": round(load),
                "battery": round(battery),
                "grid": round(grid)
            })
        
        return {"inverter_id": inverter_id, "overview": data, "source": "mock"}

    @app.get("/api/solar-history")
    def api_solar_history(inverter_id: str = "senergy1", hours: int = 24) -> Dict[str, Any]:
        """Get historical solar generation data from database."""
        try:
            log.info(f"API /api/solar-history called for inverter_id: {inverter_id}, hours: {hours}")
            if solar_app.logger and hasattr(solar_app.logger, 'path'):
                import sqlite3
                from datetime import datetime, timedelta
                
                # Calculate time range
                from solarhub.timezone_utils import now_configured
                end_time = now_configured()
                start_time = end_time - timedelta(hours=hours)
                
                # Query database for solar generation data
                conn = sqlite3.connect(solar_app.logger.path)
                cursor = conn.cursor()
                
                query = """
                SELECT 
                    ts,
                    pv_power_w
                FROM energy_samples 
                WHERE ts >= ? AND ts <= ?
                AND pv_power_w IS NOT NULL
                ORDER BY ts
                """
                
                cursor.execute(query, (start_time.isoformat(), end_time.isoformat()))
                rows = cursor.fetchall()
                conn.close()
                
                # Process data into hourly buckets
                hourly_data = {}
                for row in rows:
                    ts_str, pv_power_w = row
                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    hour_key = ts.strftime('%H:00')
                    
                    # Convert pv_power_w to kW
                    power_kw = pv_power_w / 1000.0 if pv_power_w else 0
                    
                    if hour_key not in hourly_data:
                        hourly_data[hour_key] = []
                    hourly_data[hour_key].append(power_kw)
                
                # Calculate average power for each hour
                data = []
                for hour in range(24):
                    hour_str = f"{hour:02d}:00"
                    if hour_str in hourly_data:
                        avg_power = sum(hourly_data[hour_str]) / len(hourly_data[hour_str])
                        data.append({
                            "time": hour_str,
                            "power": round(avg_power * 1000, 0)  # Convert back to watts
                        })
                    else:
                        data.append({
                            "time": hour_str,
                            "power": 0
                        })
                
                return {
                    "inverter_id": inverter_id,
                    "solar_history": data,
                    "source": "database"
                }
                
        except Exception as e:
            log.error(f"Error getting solar history from database: {e}")
            import traceback
            log.error(f"Traceback: {traceback.format_exc()}")
        
        # Fallback to mock data
        import random
        from datetime import datetime
        
        data = []
        for hour in range(24):
            hour_str = f"{hour:02d}:00"
            # Generate realistic solar curve
            if 6 <= hour <= 18:
                import math
                hour_of_day = hour - 6
                solar_factor = math.sin((hour_of_day / 12) * math.pi)
                power = max(0, solar_factor * 10000 * random.uniform(0.7, 1.0))
            else:
                power = 0
            
            data.append({
                "time": hour_str,
                "power": round(power)
            })
        
        return {
            "inverter_id": inverter_id,
            "solar_history": data,
            "source": "mock"
        }

    @app.get("/api/energy/overview")
    def api_energy_overview(inverter_id: str = "senergy1", hours: int = 24) -> Dict[str, Any]:
        """Get energy overview data using proper energy calculations."""
        try:
            log.info(f"API /api/energy/overview called for inverter_id: {inverter_id}, hours: {hours}")
            
            if not solar_app.logger or not hasattr(solar_app.logger, 'path'):
                return {
                    "inverter_id": inverter_id,
                    "overview": [],
                    "source": "error",
                    "error": "No database available"
                }
            
            # Calculate time range
            from solarhub.timezone_utils import now_configured
            end_time = now_configured()
            start_time = end_time - timedelta(hours=hours)
            
            # Use energy calculator to get hourly energy data
            energy_calc = EnergyCalculator(solar_app.logger.path)
            data = energy_calc.get_hourly_energy_data(inverter_id, start_time, end_time)
            
            
            # Format data for API response
            formatted_data = []
            for hour in range(24):
                hour_str = f"{hour:02d}:00"
                # Find data for this hour
                hour_data = next((d for d in data if d['time'] == hour_str), None)
                
                if hour_data:
                    formatted_data.append({
                        "time": hour_str,
                        "solar_energy_kwh": hour_data['solar'],
                        "load_energy_kwh": hour_data['load'],
                        "battery_charge_energy_kwh": hour_data['battery_charge'],
                        "battery_discharge_energy_kwh": hour_data['battery_discharge'],
                        "grid_import_energy_kwh": hour_data['grid_import'],
                        "grid_export_energy_kwh": hour_data['grid_export'],
                        "avg_solar_power_w": hour_data['avg_solar_power_w'],
                        "avg_load_power_w": hour_data['avg_load_power_w'],
                        "avg_battery_power_w": hour_data['avg_battery_power_w'],
                        "avg_grid_power_w": hour_data['avg_grid_power_w']
                    })
                else:
                    # No data for this hour, use zeros
                    formatted_data.append({
                        "time": hour_str,
                        "solar_energy_kwh": 0,
                        "load_energy_kwh": 0,
                        "battery_charge_energy_kwh": 0,
                        "battery_discharge_energy_kwh": 0,
                        "grid_import_energy_kwh": 0,
                        "grid_export_energy_kwh": 0,
                        "avg_solar_power_w": 0,
                        "avg_load_power_w": 0,
                        "avg_battery_power_w": 0,
                        "avg_grid_power_w": 0
                    })
            
            return {
                "inverter_id": inverter_id,
                "overview": formatted_data,
                "source": "energy_calculator"
            }
            
        except Exception as e:
            log.error(f"Error getting energy overview data: {e}", exc_info=True)
            return {
                "inverter_id": inverter_id,
                "overview": [],
                "source": "error",
                "error": str(e)
            }

    @app.get("/api/energy/daily")
    def api_energy_daily(inverter_id: str = None, date: str = None) -> Dict[str, Any]:
        """Get daily energy summary for a specific date.
        If inverter_id is None, empty string, or 'all', aggregates data from all inverters.
        Otherwise returns data for the specific inverter."""
        try:
            log.info(f"API /api/energy/daily called for inverter_id: {inverter_id}, date: {date}")
            
            if not solar_app.logger or not hasattr(solar_app.logger, 'path'):
                return {
                    "inverter_id": inverter_id or "all",
                    "daily_summary": {},
                    "source": "error",
                    "error": "No database available"
                }
            
            # Parse date or use today in PKST
            from solarhub.timezone_utils import parse_iso_to_configured, get_configured_start_of_day
            
            if date:
                target_date = parse_iso_to_configured(date)
            else:
                target_date = get_configured_start_of_day()
            
            # Get daily energy summary with timezone handling
            energy_calc = EnergyCalculator(solar_app.logger.path)
            
            # Handle aggregation for "all" or None
            if inverter_id in (None, "", "all", "ALL"):
                # Get list of all inverters
                inverter_ids: List[str] = []
                # Prefer configured list
                if solar_app and getattr(solar_app, 'cfg', None) and getattr(solar_app.cfg, 'inverters', None):
                    inverter_ids = [inv.id for inv in solar_app.cfg.inverters if getattr(inv, 'id', None)]
                # Fallback to DB if needed
                if not inverter_ids:
                    import sqlite3
                    try:
                        conn = sqlite3.connect(solar_app.logger.path)
                        cur = conn.cursor()
                        cur.execute("SELECT DISTINCT inverter_id FROM hourly_energy ORDER BY inverter_id")
                        rows = cur.fetchall()
                        inverter_ids = [r[0] for r in rows if r and r[0]]
                    finally:
                        try:
                            conn.close()
                        except Exception:
                            pass
                
                # Aggregate data from all inverters
                aggregated_data = {
                    'total_solar_kwh': 0.0,
                    'total_load_kwh': 0.0,
                    'total_battery_charge_kwh': 0.0,
                    'total_battery_discharge_kwh': 0.0,
                    'total_grid_import_kwh': 0.0,
                    'total_grid_export_kwh': 0.0,
                    'avg_solar_power_w': 0.0,
                    'avg_load_power_w': 0.0,
                    'avg_battery_power_w': 0.0,
                    'avg_grid_power_w': 0.0,
                    'total_samples': 0
                }
                for inv_id in inverter_ids:
                    inv_data = energy_calc.get_daily_energy_summary(inv_id, target_date)
                    # Sum all energy values
                    aggregated_data['total_solar_kwh'] += inv_data.get('total_solar_kwh', 0.0)
                    aggregated_data['total_load_kwh'] += inv_data.get('total_load_kwh', 0.0)
                    aggregated_data['total_battery_charge_kwh'] += inv_data.get('total_battery_charge_kwh', 0.0)
                    aggregated_data['total_battery_discharge_kwh'] += inv_data.get('total_battery_discharge_kwh', 0.0)
                    aggregated_data['total_grid_import_kwh'] += inv_data.get('total_grid_import_kwh', 0.0)
                    aggregated_data['total_grid_export_kwh'] += inv_data.get('total_grid_export_kwh', 0.0)
                    # For averages, we'll sum them (representing total array power)
                    aggregated_data['avg_solar_power_w'] += inv_data.get('avg_solar_power_w', 0.0)
                    aggregated_data['avg_load_power_w'] += inv_data.get('avg_load_power_w', 0.0)
                    aggregated_data['avg_battery_power_w'] += inv_data.get('avg_battery_power_w', 0.0)
                    aggregated_data['avg_grid_power_w'] += inv_data.get('avg_grid_power_w', 0.0)
                    aggregated_data['total_samples'] += inv_data.get('total_samples', 0)
                
                daily_data = aggregated_data
                inverter_id = "all"
            else:
                # Get data for specific inverter
                daily_data = energy_calc.get_daily_energy_summary(inverter_id, target_date)
            
            return {
                "inverter_id": inverter_id or "all",
                "date": target_date.strftime('%Y-%m-%d'),
                "daily_summary": daily_data,
                "source": "energy_calculator"
            }
            
        except Exception as e:
            log.error(f"Error getting daily energy summary: {e}", exc_info=True)
            return {
                "inverter_id": inverter_id or "all",
                "daily_summary": {},
                "source": "error",
                "error": str(e)
            }

    @app.get("/api/inverters")
    def api_inverters() -> Dict[str, Any]:
        """List available inverters (ID and name) from config or database."""
        try:
            inverters: List[Dict[str, Any]] = []
            # Prefer configured inverters if available
            if solar_app and getattr(solar_app, 'cfg', None) and getattr(solar_app.cfg, 'inverters', None):
                inverters = [
                    {"id": inv.id, "name": getattr(inv, 'name', None) or inv.id}
                    for inv in solar_app.cfg.inverters if getattr(inv, 'id', None)
                ]

            # Fallback to database distinct inverter_id
            if (not inverters) and solar_app and getattr(solar_app, 'logger', None) and getattr(solar_app.logger, 'path', None):
                try:
                    conn = sqlite3.connect(solar_app.logger.path)
                    cur = conn.cursor()
                    cur.execute("SELECT DISTINCT inverter_id FROM energy_samples ORDER BY inverter_id")
                    rows = cur.fetchall()
                    inverters = [{"id": r[0], "name": r[0]} for r in rows if r and r[0]]
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass

            return {
                "inverters": inverters,
                "source": "config" if inverters else "database"
            }
        except Exception as e:
            log.error(f"Error listing inverters: {e}", exc_info=True)
            return {"inverters": [], "source": "error", "error": str(e)}

    @app.get("/api/inverter/capabilities")
    def api_inverter_capabilities(inverter_id: str = "senergy1") -> Dict[str, Any]:
        """Get inverter capabilities, especially TOU window format."""
        try:
            # Find the inverter adapter
            adapter = None
            for rt in solar_app.inverters:
                if rt.cfg.id == inverter_id:
                    adapter = rt.adapter
                    break
            
            if not adapter:
                return {
                    "inverter_id": inverter_id,
                    "capabilities": None,
                    "error": "Inverter not found"
                }
            
            # Get TOU window capability
            capability = adapter.get_tou_window_capability() if hasattr(adapter, 'get_tou_window_capability') else {
                "max_windows": 3,
                "bidirectional": False,
                "separate_charge_discharge": True,
                "max_charge_windows": 3,
                "max_discharge_windows": 3
            }
            
            # Add adapter type
            adapter_type = rt.cfg.adapter.type if rt else None
            capability["adapter_type"] = adapter_type
            
            return {
                "inverter_id": inverter_id,
                "capabilities": capability
            }
        except Exception as e:
            log.error(f"Error getting inverter capabilities: {e}", exc_info=True)
            return {
                "inverter_id": inverter_id,
                "capabilities": None,
                "error": str(e)
            }

    @app.get("/api/inverter/tou-windows")
    async def api_get_tou_windows(inverter_id: str = "senergy1") -> Dict[str, Any]:
        """Get current TOU window values for an inverter."""
        try:
            # Get current telemetry data
            tel = solar_app.get_now(inverter_id)
            if not tel:
                return {
                    "inverter_id": inverter_id,
                    "windows": [],
                    "error": "No telemetry data available"
                }
            
            extra = tel.get("extra", {}) or {}
            
            # Get adapter capabilities
            adapter = None
            for rt in solar_app.inverters:
                if rt.cfg.id == inverter_id:
                    adapter = rt.adapter
                    break
            
            capability = adapter.get_tou_window_capability() if adapter and hasattr(adapter, 'get_tou_window_capability') else {
                "max_windows": 3,
                "bidirectional": False,
                "separate_charge_discharge": True,
                "max_charge_windows": 3,
                "max_discharge_windows": 3
            }
            
            windows = []
            
            if capability.get("bidirectional", False):
                # Powdrive-style: bidirectional windows (up to 6)
                max_windows = capability.get("max_windows", 6)

                # Helper to convert HHMM integer (e.g. 2359) to "23:59"
                def _fmt_hhmm(val: Any) -> str:
                    try:
                        iv = int(val)
                        h = max(0, min(23, iv // 100))
                        m = max(0, min(59, iv % 100))
                        return f"{h:02d}:{m:02d}"
                    except Exception:
                        s = str(val or "")
                        if ":" in s and len(s) >= 4:
                            return s
                        return "00:00"

                # Get battery mode source from telemetry (don't call read_by_ident from API server to avoid client recreation)
                battery_mode_source = extra.get("battery_mode_source", 1)  # 1=Capacity, 0=Voltage
                try:
                    battery_mode_source = int(battery_mode_source)
                except (ValueError, TypeError):
                    battery_mode_source = 1

                for idx in range(1, max_windows + 1):
                    # Get all TOU window data from telemetry extra fields only
                    # Do NOT call read_by_ident from API server to avoid triggering client recreation
                    # in wrong event loop, which causes lock conflicts with polling loop
                    start_time = extra.get(f"tou_window_{idx}_start_time") or extra.get(f"charge_start_time_{idx}")
                    end_time = extra.get(f"tou_window_{idx}_end_time") or extra.get(f"charge_end_time_{idx}")
                    power_w = extra.get(f"tou_window_{idx}_power_w") or extra.get(f"charge_power_{idx}")
                    target_soc_pct = extra.get(f"tou_window_{idx}_target_soc_pct") or extra.get(f"charger_end_soc_{idx}")
                    target_voltage_v = extra.get(f"tou_window_{idx}_target_voltage_v")
                    win_type = extra.get(f"tou_window_{idx}_type") or "auto"
                    
                    # Also check for register-based keys in extra (these are populated during polling)
                    if start_time is None:
                        start_time = extra.get(f"prog{idx}_time")
                    if end_time is None:
                        next_idx = idx + 1 if idx < max_windows else 1
                        end_time = extra.get(f"prog{next_idx}_time")
                    if power_w is None:
                        power_w = extra.get(f"prog{idx}_power_w")
                    if battery_mode_source == 1:  # Capacity mode -> SOC targets
                        if target_soc_pct is None:
                            target_soc_pct = extra.get(f"prog{idx}_capacity_pct", 100)
                    else:  # Voltage mode
                        if target_voltage_v is None:
                            target_voltage_v = extra.get(f"prog{idx}_voltage_v")

                    window = {
                        "index": idx,
                        "start_time": _fmt_hhmm(start_time),
                        "end_time": _fmt_hhmm(end_time),
                        "power_w": int(power_w or 0),
                        "target_soc_pct": int(target_soc_pct or (100 if battery_mode_source == 1 else 100)),
                        "target_voltage_v": float(target_voltage_v) if target_voltage_v is not None else None,
                        "type": win_type,
                    }
                    windows.append(window)
            else:
                # Senergy-style: separate charge and discharge windows (up to 3 each)
                max_charge = capability.get("max_charge_windows", 3)
                max_discharge = capability.get("max_discharge_windows", 3)
                
                # Charge windows
                for idx in range(1, max_charge + 1):
                    window = {
                        "index": idx,
                        "type": "charge",
                        "start_time": extra.get(f"charge_start_time_{idx}") or "00:00",
                        "end_time": extra.get(f"charge_end_time_{idx}") or "00:00",
                        "power_w": extra.get(f"charge_power_{idx}") or 0,
                        "target_soc_pct": extra.get(f"charger_end_soc_{idx}") or 100
                    }
                    windows.append(window)
                
                # Discharge windows
                for idx in range(1, max_discharge + 1):
                    window = {
                        "index": idx,
                        "type": "discharge",
                        "start_time": extra.get(f"discharge_start_time_{idx}") or "00:00",
                        "end_time": extra.get(f"discharge_end_time_{idx}") or "00:00",
                        "power_w": extra.get(f"discharge_power_{idx}") or 0,
                        "target_soc_pct": extra.get(f"discharge_end_soc_{idx}") or 30
                    }
                    windows.append(window)
            
            return {
                "inverter_id": inverter_id,
                "capabilities": capability,
                "windows": windows
            }
        except Exception as e:
            log.error(f"Error getting TOU windows: {e}", exc_info=True)
            return {
                "inverter_id": inverter_id,
                "windows": [],
                "error": str(e)
            }

    # -------------------- Device Management --------------------
    @app.get("/api/devices/discovery")
    async def api_get_discovered_devices(status: Optional[str] = None):
        """Get all discovered devices, optionally filtered by status."""
        if not app.device_registry:
            return {"devices": [], "error": "Device discovery not enabled"}
        
        try:
            devices = app.device_registry.get_all_devices(status_filter=status)
            return {
                "devices": [
                    {
                        "device_id": d.device_id,
                        "device_type": d.device_type,
                        "serial_number": d.serial_number,
                        "port": d.port,
                        "last_known_port": d.last_known_port,
                        "port_history": d.port_history,
                        "status": d.status,
                        "failure_count": d.failure_count,
                        "next_retry_time": d.next_retry_time,
                        "first_discovered": d.first_discovered,
                        "last_seen": d.last_seen,
                        "is_auto_discovered": d.is_auto_discovered,
                    }
                    for d in devices
                ]
            }
        except Exception as e:
            log.error(f"Error getting discovered devices: {e}", exc_info=True)
            return {"error": str(e)}
    
    @app.post("/api/devices/discovery/scan")
    async def api_trigger_discovery():
        """Manually trigger device discovery scan."""
        if not app.discovery_service:
            return {"error": "Device discovery not enabled"}
        
        try:
            discovered = await app.discovery_service.discover_devices(
                manual_config_inverters=app.cfg.inverters,
                manual_config_battery=getattr(app.cfg, "battery_bank", None)
            )
            return {
                "success": True,
                "devices_found": len(discovered),
                "devices": [
                    {
                        "device_id": d.device_id,
                        "device_type": d.device_type,
                        "serial_number": d.serial_number,
                        "port": d.port,
                        "status": d.status,
                    }
                    for d in discovered
                ]
            }
        except Exception as e:
            log.error(f"Error during discovery scan: {e}", exc_info=True)
            return {"error": str(e)}
    
    @app.get("/api/devices/{device_id}/status")
    async def api_get_device_status(device_id: str):
        """Get device status, failure count, next retry time."""
        if not app.device_registry:
            return {"error": "Device discovery not enabled"}
        
        try:
            device = app.device_registry.get_device(device_id)
            if not device:
                return {"error": "Device not found"}
            
            return {
                "device_id": device.device_id,
                "device_type": device.device_type,
                "serial_number": device.serial_number,
                "port": device.port,
                "last_known_port": device.last_known_port,
                "port_history": device.port_history,
                "status": device.status,
                "failure_count": device.failure_count,
                "next_retry_time": device.next_retry_time,
                "first_discovered": device.first_discovered,
                "last_seen": device.last_seen,
                "is_auto_discovered": device.is_auto_discovered,
            }
        except Exception as e:
            log.error(f"Error getting device status: {e}", exc_info=True)
            return {"error": str(e)}
    
    @app.post("/api/devices/{device_id}/re-enable")
    async def api_re_enable_device(device_id: str):
        """Re-enable a permanently disabled device."""
        if not app.device_registry:
            return {"error": "Device discovery not enabled"}
        
        try:
            app.device_registry.re_enable_device(device_id)
            return {"success": True, "message": f"Device {device_id} re-enabled for discovery"}
        except Exception as e:
            log.error(f"Error re-enabling device: {e}", exc_info=True)
            return {"error": str(e)}
    
    @app.post("/api/devices/{device_id}/disable")
    async def api_disable_device(device_id: str):
        """Manually disable a device."""
        if not app.device_registry:
            return {"error": "Device discovery not enabled"}
        
        try:
            app.device_registry.update_device_status(device_id, "recovering")
            return {"success": True, "message": f"Device {device_id} disabled"}
        except Exception as e:
            log.error(f"Error disabling device: {e}", exc_info=True)
            return {"error": str(e)}
    
    @app.get("/api/devices/serial-ports")
    def api_list_serial_ports() -> Dict[str, Any]:
        """List available serial/USB ports for RTU connections."""
        try:
            ports = []
            try:
                import serial.tools.list_ports  # type: ignore
                for p in serial.tools.list_ports.comports():
                    ports.append({
                        "device": getattr(p, "device", None) or getattr(p, "name", None),
                        "description": getattr(p, "description", ""),
                        "hwid": getattr(p, "hwid", "")
                    })
            except Exception as e:
                log.warning(f"Serial port listing failed: {e}")
            return {"ports": ports}
        except Exception as e:
            return {"ports": [], "error": str(e)}

    @app.get("/api/adapters")
    def api_list_adapters() -> Dict[str, Any]:
        """List supported inverter and battery adapters (by implementation)."""
        try:
            inverter_adapters = [
                {"value": "senergy", "label": "Senergy"},
                {"value": "powdrive", "label": "Powdrive"},
            ]
            battery_adapters = [
                {"value": "pytes", "label": "USB PYTES"},
            ]
            return {"inverter_adapters": inverter_adapters, "battery_adapters": battery_adapters}
        except Exception as e:
            return {"inverter_adapters": [], "battery_adapters": [], "error": str(e)}

    @app.get("/api/devices")
    def api_get_devices() -> Dict[str, Any]:
        """Return configured inverters and optional battery bank from persisted config, including connection status.
        This endpoint is designed to be non-blocking and won't interfere with the polling loop."""
        try:
            # Use cached config if available to avoid triggering adapter recreation
            # Only reload if config_manager is available and we need fresh data
            if solar_app.config_manager:
                try:
                    # Try to get config without triggering adapter initialization
                    cfg = solar_app.cfg  # Use current cached config first
                    # Only reload if we really need to (e.g., config was just updated)
                    # For read-only operations, use cached config to avoid blocking
                except Exception:
                    # Fallback to loading if cached config is not available
                    cfg = solar_app.config_manager.load_config()
            else:
                cfg = solar_app.cfg
            
            cfg_dict = cfg.model_dump() if hasattr(cfg, 'model_dump') else cfg.dict()
            
            # Check which inverters are actually connected (not just in the list)
            # IMPORTANT: Do NOT access adapter.client from API server thread to avoid triggering
            # client recreation in wrong event loop. Use only flags and runtime existence.
            # Use thread-safe access to avoid blocking polling loop
            polling_suspended = getattr(solar_app, '_polling_suspended', True)
            devices_connected = getattr(solar_app, '_devices_connected', False)
            
            connected_inverter_ids = set()
            if not polling_suspended and devices_connected:
                # Devices are connected - use runtime existence as proxy for connection
                # We don't access client.connected to avoid triggering client recreation
                # in the API server's event loop, which would cause lock conflicts
                try:
                    for rt in list(solar_app.inverters):  # Create a copy to avoid iteration issues
                        # Simply check if runtime exists and has adapter
                        # If devices_connected is True and polling is not suspended,
                        # we can assume inverters in the list are connected
                        if hasattr(rt, 'adapter') and rt.adapter is not None:
                            connected_inverter_ids.add(rt.cfg.id)
                except (RuntimeError, AttributeError) as e:
                    # Handle race conditions gracefully
                    log.debug(f"Error checking inverter connection state (non-critical): {e}")
            
            # Check battery connection state - use adapter existence as proxy
            battery_connected = False
            if not polling_suspended and devices_connected:
                try:
                    # Just check if battery adapter exists, don't access client
                    if getattr(solar_app, 'battery_adapter', None) is not None:
                        battery_connected = True
                except (AttributeError, RuntimeError):
                    # Battery adapter might be in transition, skip this check
                    pass
            
            # Add connection status to each inverter config
            inverters_with_status = []
            for inv in cfg_dict.get("inverters", []):
                inv_dict = dict(inv) if isinstance(inv, dict) else inv.model_dump() if hasattr(inv, 'model_dump') else inv.dict()
                inv_dict["connected"] = inv_dict.get("id") in connected_inverter_ids
                inverters_with_status.append(inv_dict)
            
            battery_bank = cfg_dict.get("battery_bank")
            if battery_bank:
                battery_dict = dict(battery_bank) if isinstance(battery_bank, dict) else battery_bank.model_dump() if hasattr(battery_bank, 'model_dump') else battery_bank.dict()
                battery_dict["connected"] = battery_connected
                battery_bank = battery_dict
            
            return {
                "inverters": inverters_with_status,
                "battery_bank": battery_bank,
                "has_connections": len(connected_inverter_ids) > 0 or battery_connected
            }
        except Exception as e:
            log.error(f"Error getting devices: {e}", exc_info=True)
            return {"inverters": [], "battery_bank": None, "has_connections": False, "error": str(e)}

    @app.post("/api/devices")
    def api_save_devices(devices: Dict[str, Any]) -> Dict[str, Any]:
        """Persist devices (inverters array and optional battery_bank) to configuration DB."""
        try:
            updates: Dict[str, Any] = {}
            if "inverters" in devices:
                updates["inverters"] = devices["inverters"]
            if "battery_bank" in devices:
                updates["battery_bank"] = devices.get("battery_bank")
            if not updates:
                return {"status": "error", "message": "No device updates provided"}
            if solar_app.config_manager:
                ok = solar_app.config_manager.update_config_bulk(updates)
                if ok:
                    # Reload cfg in app
                    solar_app.cfg = solar_app.config_manager.reload_config()
                    # Rebuild runtime objects (arrays, battery_bank_arrays, etc.) after config reload
                    solar_app._build_runtime_objects(solar_app.cfg)
                    return {"status": "success"}
                return {"status": "error", "message": "Failed to save"}
            return {"status": "error", "message": "Config manager unavailable"}
        except Exception as e:
            log.error(f"Error saving devices: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    @app.post("/api/devices/connect")
    async def api_connect_devices(body: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to configured devices now and start polling without restart.
        If already connected, skip duplicates.
        """
        try:
            from solarhub.config import InverterConfig, BatteryBankConfig
            from solarhub.app import InverterRuntime
            # Local helper to build adapter
            async def _ensure_inverter(rt_cfg: InverterConfig) -> str:
                # If already present, skip
                for rt in solar_app.inverters:
                    if rt.cfg.id == rt_cfg.id:
                        return "already_connected"
                adapter = None
                if rt_cfg.adapter.type.lower() == "senergy":
                    from solarhub.adapters.senergy import SenergyAdapter
                    adapter = SenergyAdapter(rt_cfg)
                elif rt_cfg.adapter.type.lower() == "powdrive":
                    from solarhub.adapters.powdrive import PowdriveAdapter
                    adapter = PowdriveAdapter(rt_cfg)
                else:
                    return "unsupported_adapter"
                # Don't connect here - let the polling loop create the client in its event loop
                # This avoids event loop mismatch issues where client is created in API server's
                # event loop but used in polling loop's event loop
                # The client will be created lazily on first poll via _ensure_client_in_current_loop()
                # Register with command queue so commands work immediately
                if hasattr(solar_app, 'command_queue'):
                    solar_app.command_queue.register_adapter(rt_cfg.id, adapter)
                    solar_app.command_queue.start()
                
                # Create and add inverter runtime
                rt_new = InverterRuntime(rt_cfg, adapter)
                solar_app.inverters.append(rt_new)
                
                # Subscribe to MQTT command topics for this inverter
                solar_app._subscribe_command_topics(rt_new)
                
                # Publish availability and discovery
                solar_app.mqtt.pub(f"{solar_app.cfg.mqtt.base_topic}/{rt_cfg.id}/availability", "online", retain=True)
                solar_app.ha.publish_all_for_inverter(rt_new)
                
                return "connected"

            async def _ensure_battery(bank_cfg: BatteryBankConfig) -> str:
                # If already present
                if getattr(solar_app, 'battery_adapter', None):
                    return "already_connected"
                if not bank_cfg or not bank_cfg.adapter or not bank_cfg.adapter.type:
                    return "no_config"
                if bank_cfg.adapter.type.lower() == "pytes":
                    from solarhub.adapters.battery_pytes import PytesBatteryAdapter
                    ba = PytesBatteryAdapter(bank_cfg)
                else:
                    return "unsupported_adapter"
                # Don't connect here - let the polling loop create the connection in its event loop
                # This avoids event loop mismatch issues
                # The battery adapter will connect lazily on first poll
                solar_app.battery_adapter = ba
                return "connected"

            # Use latest config
            cfg = solar_app.config_manager.load_config() if solar_app.config_manager else solar_app.cfg
            results: Dict[str, Any] = {"inverters": {}, "battery_bank": None}
            # Inverters
            for inv_cfg in (cfg.inverters or []):
                try:
                    status = await _ensure_inverter(inv_cfg)
                except Exception as e:
                    log.error(f"Connect failed for inverter {inv_cfg.id}: {e}")
                    status = f"error: {e}"
                results["inverters"][inv_cfg.id] = status
            # Battery
            if getattr(cfg, 'battery_bank', None):
                try:
                    results["battery_bank"] = await _ensure_battery(cfg.battery_bank)
                except Exception as e:
                    log.error(f"Battery connect failed: {e}")
                    results["battery_bank"] = f"error: {e}"

            # Ensure command queue manager is started (same as init())
            if hasattr(solar_app, 'command_queue'):
                solar_app.command_queue.start()
                log.info("Command queue manager started")
            
            # Initialize smart scheduler if needed (same as init())
            if solar_app.cfg.smart.policy.enabled and solar_app.smart is None:
                try:
                    from solarhub.schedulers.smart import SmartScheduler
                    solar_app.smart = SmartScheduler(solar_app.logger, solar_app)
                    log.info("Smart scheduler initialized after device connection")
                    
                    # Subscribe to battery optimization configuration commands
                    config_base = f"{solar_app.cfg.mqtt.base_topic}/config"
                    solar_app.mqtt.sub(f"{config_base}/set", solar_app.smart.handle_config_command)
                    
                    # Publish inverter configuration discovery messages
                    log.info("Publishing inverter configuration discovery messages after connection")
                    for inverter in solar_app.inverters:
                        if hasattr(inverter.adapter, 'regs') and inverter.adapter.regs:
                            solar_app.smart.inverter_config_ha.publish_inverter_config_sensors(inverter.cfg.id, inverter.adapter.regs)
                    log.info("Inverter configuration discovery messages published after connection")
                except Exception as e:
                    log.error(f"Failed to initialize smart scheduler: {e}")
                    log.error("Smart scheduler will not be available - inverter config commands will not be processed")
                    solar_app.smart = None
            
            # Check if we need to reconnect existing devices (they were disconnected but still in list)
            needs_reconnect = False
            if solar_app.inverters or getattr(solar_app, 'battery_adapter', None):
                # Check if devices are disconnected (polling suspended or devices not connected)
                if (hasattr(solar_app, '_polling_suspended') and solar_app._polling_suspended) or \
                   (hasattr(solar_app, '_devices_connected') and not solar_app._devices_connected):
                    needs_reconnect = True
            
            # Start or resume polling loop if devices were connected
            if solar_app.inverters or getattr(solar_app, 'battery_adapter', None):
                try:
                    if needs_reconnect:
                        # Signal the polling loop to reconnect (it will reconnect same client objects)
                        log.info("Signaling polling loop to reconnect devices (reusing client objects)")
                        solar_app._reconnect_requested = True
                        solar_app._reconnect_config = None  # Config already updated above
                        # Wait a bit for the polling loop to process the reconnect
                        await asyncio.sleep(0.5)
                    else:
                        # Start or resume polling loop normally
                        await solar_app.start_polling_loop()
                        log.info("Polling loop started/resumed after device connection")
                except Exception as e:
                    log.error(f"Failed to start/resume polling loop: {e}", exc_info=True)
                    # Don't fail the connection if polling loop fails to start
                    # It might already be running

            return {"status": "success", **results}
        except Exception as e:
            log.error(f"Error connecting devices: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    @app.post("/api/devices/disconnect")
    async def api_disconnect_devices(body: Dict[str, Any]) -> Dict[str, Any]:
        """Disconnect all currently connected devices by signaling the polling loop.
        The polling loop will handle the disconnect in its own event loop, keeping client objects for reuse.
        """
        try:
            results: Dict[str, Any] = {"inverters": {}, "battery_bank": None}
            
            # Signal the polling loop to handle disconnect
            # The polling loop will close connections but keep client objects
            # Check if devices are actually connected (polling is happening)
            polling_suspended = getattr(solar_app, '_polling_suspended', True)
            devices_connected = getattr(solar_app, '_devices_connected', False)
            has_inverters = len(solar_app.inverters) > 0
            has_battery = getattr(solar_app, 'battery_adapter', None) is not None
            
            log.info(f"Disconnect requested - state: polling_suspended={polling_suspended}, devices_connected={devices_connected}, has_inverters={has_inverters}, has_battery={has_battery}")
            
            # If devices are configured and polling is active, signal disconnect
            if (has_inverters or has_battery) and not polling_suspended:
                log.info("Signaling polling loop to disconnect devices (keeping client objects)")
                # Signal disconnect - polling loop will handle it
                solar_app._disconnect_requested = True
                log.info(f"Disconnect flag set to: {solar_app._disconnect_requested}")
                
                # Wait for the polling loop to process the disconnect
                # Poll the flags to ensure disconnect is complete
                max_wait = 5.0  # Maximum wait time in seconds (increased to allow polling loop to process)
                wait_interval = 0.1  # Check every 100ms
                waited = 0.0
                while waited < max_wait:
                    await asyncio.sleep(wait_interval)
                    waited += wait_interval
                    # Check if disconnect is complete (polling suspended and devices not connected)
                    # Note: Default to False for _devices_connected if not set (not connected)
                    polling_suspended = getattr(solar_app, '_polling_suspended', False)
                    devices_connected = getattr(solar_app, '_devices_connected', False)
                    if polling_suspended and not devices_connected:
                        log.info("Disconnect completed in polling loop")
                        break
                else:
                    # Check final state even if timeout
                    polling_suspended = getattr(solar_app, '_polling_suspended', False)
                    devices_connected = getattr(solar_app, '_devices_connected', False)
                    if polling_suspended and not devices_connected:
                        log.info("Disconnect completed in polling loop (after timeout check)")
                    else:
                        log.warning(f"Disconnect may not have completed within {max_wait}s timeout (polling_suspended={polling_suspended}, devices_connected={devices_connected})")
                
                # Collect results (inverters are still in the list, just disconnected)
                for rt in list(solar_app.inverters):
                    results["inverters"][rt.cfg.id] = "disconnected"
                    log.info(f"Disconnect signaled for inverter: {rt.cfg.id}")
                
                if getattr(solar_app, 'battery_adapter', None):
                    results["battery_bank"] = "disconnected"
                    log.info("Disconnect signaled for battery adapter")
                else:
                    results["battery_bank"] = "not_connected"
            else:
                log.info("No active devices to disconnect (already disconnected or no devices configured)")
                # Still return success for devices that exist
                for rt in list(solar_app.inverters):
                    results["inverters"][rt.cfg.id] = "not_connected"
                if getattr(solar_app, 'battery_adapter', None):
                    results["battery_bank"] = "not_connected"
                else:
                    results["battery_bank"] = "not_connected"
            
            return {"status": "success", **results}
        except Exception as e:
            log.error(f"Error signaling disconnect: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    @app.post("/api/inverter/tou-windows")
    def api_set_tou_window(window_data: Dict[str, Any]) -> Dict[str, Any]:
        """Set TOU window values for an inverter."""
        try:
            import json
            
            # Get parameters from request body
            inverter_id = window_data.get("inverter_id", "senergy1")
            window_index = int(window_data.get("window_index", 1))
            window_type = window_data.get("window_type", "charge")
            
            # Get adapter capabilities
            adapter = None
            for rt in solar_app.inverters:
                if rt.cfg.id == inverter_id:
                    adapter = rt.adapter
                    break
            
            if not adapter:
                return {"status": "error", "message": "Inverter not found"}
            
            capability = adapter.get_tou_window_capability() if hasattr(adapter, 'get_tou_window_capability') else {
                "max_windows": 3,
                "bidirectional": False,
                "separate_charge_discharge": True,
                "max_charge_windows": 3,
                "max_discharge_windows": 3
            }
            
            # Build command based on capability
            if capability.get("bidirectional", False):
                # Powdrive-style: bidirectional windows
                action = f"set_tou_window{window_index}"
            else:
                # Senergy-style: separate charge/discharge windows
                if window_type == "charge":
                    action = f"set_tou_window{window_index}"
                else:
                    action = f"set_tou_discharge_window{window_index}"
            
            # Build command from window data (exclude metadata fields)
            cmd = {
                "action": action,
                "start_time": window_data.get("start_time", "00:00"),
                "end_time": window_data.get("end_time", "00:00"),
                "power_w": window_data.get("power_w", 0),
                "target_soc_pct": window_data.get("target_soc_pct", 100)
            }
            
            # Add type for bidirectional windows
            if capability.get("bidirectional", False):
                cmd["type"] = window_data.get("type", "auto")
                if window_data.get("target_voltage_v"):
                    cmd["target_voltage_v"] = window_data.get("target_voltage_v")
            
            # Add charge-specific fields for Senergy
            if not capability.get("bidirectional", False) and window_type == "charge":
                cmd["charge_power_w"] = window_data.get("power_w", 0)
                cmd["charge_end_soc"] = window_data.get("target_soc_pct", 100)
                cmd["frequency"] = "Everyday"
            
            # Add discharge-specific fields for Senergy
            if not capability.get("bidirectional", False) and window_type == "discharge":
                cmd["discharge_power_w"] = window_data.get("power_w", 0)
                cmd["discharge_end_soc"] = window_data.get("target_soc_pct", 30)
                cmd["frequency"] = "Everyday"
            
            # Use command queue if available
            if hasattr(solar_app, 'command_queue'):
                success = solar_app.command_queue.enqueue_command(inverter_id, cmd)
                if success:
                    return {"status": "success", "message": f"TOU window {window_index} queued for update"}
                else:
                    return {"status": "error", "message": "Failed to queue command"}
            else:
                # Fallback: send via MQTT
                topic = f"{solar_app.cfg.mqtt.base_topic}/inverter/{inverter_id}/cmd"
                solar_app.mqtt.pub(topic, json.dumps(cmd))
                return {"status": "success", "message": f"TOU window {window_index} command sent"}
            
        except Exception as e:
            log.error(f"Error setting TOU window: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    @app.get("/api/energy/hourly")
    def api_energy_hourly(inverter_id: str = "senergy1", date: str = None) -> Dict[str, Any]:
        """Get hourly energy data for a specific date."""
        try:
            log.info(f"API /api/energy/hourly called for inverter_id: {inverter_id}, date: {date}")
            
            if not solar_app.logger or not hasattr(solar_app.logger, 'path'):
                return {
                    "inverter_id": inverter_id,
                    "hourly_data": [],
                    "source": "error",
                    "error": "No database available"
                }
            
            # Parse date or use today in PKST
            from solarhub.timezone_utils import parse_iso_to_configured, get_configured_start_of_day
            
            if date:
                target_date = parse_iso_to_configured(date)
            else:
                target_date = get_configured_start_of_day()
            
            # Get hourly energy data for the day with timezone handling
            energy_calc = EnergyCalculator(solar_app.logger.path)
            start_time = target_date
            end_time = target_date + timedelta(days=1)
            
            # Helper to fetch per-inverter hourly list (24 entries)
            def fetch_hourly(inv_id: str) -> List[Dict[str, Any]]:
                return energy_calc.ensure_24_hour_data(inv_id, target_date)

            # Aggregate if requested
            if inverter_id in (None, "", "all", "ALL"):
                # Determine inverter list
                inverter_ids: List[str] = []
                # Prefer configured list
                if solar_app and getattr(solar_app, 'cfg', None) and getattr(solar_app.cfg, 'inverters', None):
                    inverter_ids = [inv.id for inv in solar_app.cfg.inverters if getattr(inv, 'id', None)]
                # Fallback to DB
                if not inverter_ids:
                    try:
                        conn = sqlite3.connect(solar_app.logger.path)
                        cur = conn.cursor()
                        cur.execute("SELECT DISTINCT inverter_id FROM energy_samples ORDER BY inverter_id")
                        rows = cur.fetchall()
                        inverter_ids = [r[0] for r in rows if r and r[0]]
                    finally:
                        try:
                            conn.close()
                        except Exception:
                            pass

                per_inverter = [fetch_hourly(inv) for inv in inverter_ids] if inverter_ids else []

                # Initialize aggregate structure with 24 empty hours
                hourly_data: List[Dict[str, Any]] = []
                if per_inverter:
                    template = per_inverter[0]
                    for idx in range(len(template)):
                        hour_entry = {
                            "time": template[idx].get("time"),
                            "solar": 0.0,
                            "load": 0.0,
                            # keep split fields for compatibility with UI normalizer
                            "battery_charge": 0.0,
                            "battery_discharge": 0.0,
                            "grid_import": 0.0,
                            "grid_export": 0.0,
                        }
                        # Sum across inverters for this index
                        for inv_list in per_inverter:
                            if idx < len(inv_list):
                                ent = inv_list[idx] or {}
                                hour_entry["solar"] += float(ent.get("solar", 0) or 0)
                                hour_entry["load"] += float(ent.get("load", 0) or 0)
                                hour_entry["battery_charge"] += float(ent.get("battery_charge", 0) or 0)
                                hour_entry["battery_discharge"] += float(ent.get("battery_discharge", 0) or 0)
                                hour_entry["grid_import"] += float(ent.get("grid_import", 0) or 0)
                                hour_entry["grid_export"] += float(ent.get("grid_export", 0) or 0)
                                # If backend provided net fields, incorporate them by distributing into splits
                                if "battery" in ent and (ent.get("battery") is not None):
                                    b = float(ent.get("battery") or 0)
                                    if b >= 0:
                                        hour_entry["battery_charge"] += b
                                    else:
                                        hour_entry["battery_discharge"] += (-b)
                                if "grid" in ent and (ent.get("grid") is not None):
                                    g = float(ent.get("grid") or 0)
                                    if g >= 0:
                                        hour_entry["grid_import"] += g
                                    else:
                                        hour_entry["grid_export"] += (-g)
                        hourly_data.append(hour_entry)
                else:
                    hourly_data = []
            else:
                # Ensure we have complete 24-hour data for a specific inverter
                hourly_data = energy_calc.ensure_24_hour_data(inverter_id, target_date)
            
            return {
                "inverter_id": inverter_id,
                "date": target_date.strftime('%Y-%m-%d'),
                "hourly_data": hourly_data,
                "source": "energy_calculator"
            }
            
        except Exception as e:
            log.error(f"Error getting hourly energy data: {e}", exc_info=True)
            return {
                "inverter_id": inverter_id,
                "hourly_data": [],
                "source": "error",
                "error": str(e)
            }

    @app.get("/api/config")
    def api_get_config() -> Dict[str, Any]:
        """Get current configuration settings with hierarchy structure from database."""
        try:
            log.info("API /api/config called")
            
            # Load hierarchy from database first (primary source)
            hierarchy_data = {}
            if hasattr(solar_app, 'hierarchy_systems') and solar_app.hierarchy_systems:
                log.info(f"Loading hierarchy from database: {len(solar_app.hierarchy_systems)} system(s)")
                # Convert hierarchy systems to dictionary format
                systems_list = []
                for system_id, system in solar_app.hierarchy_systems.items():
                    system_dict = {
                        "system_id": system.system_id,
                        "name": system.name,
                        "description": system.description,
                        "timezone": system.timezone,
                        "inverter_arrays": [],
                        "battery_arrays": [],
                        "meters": []
                    }
                    
                    # Add inverter arrays
                    for inv_array in system.inverter_arrays:
                        array_dict = {
                            "array_id": inv_array.array_id,
                            "name": inv_array.name,
                            "system_id": inv_array.system_id,
                            "inverters": [],
                            "attached_battery_array_id": inv_array.attached_battery_array_id
                        }
                        for inverter in inv_array.inverters:
                            inv_dict = {
                                "inverter_id": inverter.inverter_id,
                                "name": inverter.name,
                                "array_id": inverter.array_id,
                                "system_id": inverter.system_id,
                                "model": inverter.model,
                                "serial_number": inverter.serial_number,
                                "vendor": inverter.vendor,
                                "phase_type": inverter.phase_type
                            }
                            if inverter.adapter:
                                inv_dict["adapter"] = {
                                    "adapter_id": inverter.adapter.adapter_id,
                                    "adapter_type": inverter.adapter.adapter_type,
                                    "config": inverter.adapter.config_json
                                }
                            array_dict["inverters"].append(inv_dict)
                        system_dict["inverter_arrays"].append(array_dict)
                    
                    # Add battery arrays
                    for bat_array in system.battery_arrays:
                        bat_array_dict = {
                            "battery_array_id": bat_array.battery_array_id,
                            "name": bat_array.name,
                            "system_id": bat_array.system_id,
                            "battery_packs": [],
                            "attached_inverter_array_id": bat_array.attached_inverter_array_id
                        }
                        for pack in bat_array.battery_packs:
                            pack_dict = {
                                "pack_id": pack.pack_id,
                                "name": pack.name,
                                "battery_array_id": pack.battery_array_id,
                                "system_id": pack.system_id,
                                "chemistry": pack.chemistry,
                                "nominal_kwh": pack.nominal_kwh,
                                "max_charge_kw": pack.max_charge_kw,
                                "max_discharge_kw": pack.max_discharge_kw
                            }
                            if pack.adapters:
                                pack_dict["adapters"] = [
                                    {
                                        "adapter_id": adapter.adapter_id,
                                        "adapter_type": adapter.adapter_type,
                                        "priority": adapter.priority,
                                        "enabled": adapter.enabled,
                                        "config": adapter.config_json
                                    }
                                    for adapter in pack.adapters
                                ]
                            bat_array_dict["battery_packs"].append(pack_dict)
                        system_dict["battery_arrays"].append(bat_array_dict)
                    
                    # Add meters
                    for meter in system.meters:
                        meter_dict = {
                            "meter_id": meter.meter_id,
                            "name": meter.name,
                            "system_id": meter.system_id,
                            "model": meter.model,
                            "serial_number": meter.serial_number,
                            "vendor": getattr(meter, 'vendor', None),  # Meter doesn't have vendor attribute
                            "meter_type": meter.meter_type,
                            "attachment_target": meter.attachment_target
                        }
                        if meter.adapter:
                            meter_dict["adapter"] = {
                                "adapter_id": meter.adapter.adapter_id,
                                "adapter_type": meter.adapter.adapter_type,
                                "config": meter.adapter.config_json
                            }
                        system_dict["meters"].append(meter_dict)
                    
                    systems_list.append(system_dict)
                
                hierarchy_data = {
                    "systems": systems_list,
                    "source": "database"
                }
            
            # Also include config.yaml for backward compatibility
            config_dict = {}
            if solar_app.config_manager:
                config = solar_app.config_manager.load_config()
                config_dict = config.model_dump() if hasattr(config, 'model_dump') else config.dict()
                source = "database" if solar_app.config_manager._config_cache else "config_file"
            elif solar_app.cfg:
                config_dict = solar_app.cfg.model_dump() if hasattr(solar_app.cfg, 'model_dump') else solar_app.cfg.dict()
                source = "config_file"
            
            return {
                "hierarchy": hierarchy_data if hierarchy_data else None,
                "config": config_dict,
                "source": source
            }
            
        except Exception as e:
            log.error(f"Error getting configuration: {e}", exc_info=True)
            return {
                "hierarchy": None,
                "config": {},
                "source": "error",
                "error": str(e)
            }

    @app.post("/api/config")
    def api_update_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update configuration settings."""
        try:
            log.info(f"API /api/config POST called with data: {config_data}")
            
            # Update configuration in database
            if solar_app.config_manager:
                # If only one field is being updated, use single update method
                if len(config_data) == 1:
                    key, value = next(iter(config_data.items()))
                    success = solar_app.config_manager.update_config_single(key, value)
                else:
                    success = solar_app.config_manager.update_config_bulk(config_data)
                
                if success:
                    log.info("Configuration updated successfully")
                    # Reload configuration from database to reflect changes
                    solar_app.cfg = solar_app.config_manager.reload_config()
                    # Rebuild runtime objects (arrays, battery_bank_arrays, etc.) after config reload
                    solar_app._build_runtime_objects(solar_app.cfg)
                    return {
                        "status": "success",
                        "message": "Configuration updated successfully"
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Failed to update configuration"
                    }
            else:
                return {
                    "status": "error",
                    "message": "Configuration manager not available"
                }
                
        except Exception as e:
            log.error(f"Error updating configuration: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }

    # ------------------------------------------------------------------
    # Authentication API
    # ------------------------------------------------------------------
    
    from solarhub.auth_manager import AuthManager
    auth_manager = AuthManager()
    
    @app.post("/api/auth/register")
    def api_register(request: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new user."""
        try:
            email = request.get("email")
            password = request.get("password")
            first_name = request.get("firstName")
            last_name = request.get("lastName")
            
            if not all([email, password, first_name, last_name]):
                return {
                    "status": "error",
                    "error": "All fields are required"
                }
            
            result = auth_manager.register_user(email, password, first_name, last_name)
            
            if result["success"]:
                return {
                    "status": "ok",
                    "user": result["user"],
                    "token": result["token"]
                }
            else:
                return {
                    "status": "error",
                    "error": result["error"]
                }
                
        except Exception as e:
            log.error(f"Registration error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": "Registration failed. Please try again."
            }
    
    @app.post("/api/auth/login")
    def api_login(request: Dict[str, Any]) -> Dict[str, Any]:
        """Login a user."""
        try:
            email = request.get("email")
            password = request.get("password")
            
            if not email or not password:
                return {
                    "status": "error",
                    "error": "Email and password are required"
                }
            
            result = auth_manager.login_user(email, password)
            
            if result["success"]:
                return {
                    "status": "ok",
                    "user": result["user"],
                    "token": result["token"]
                }
            else:
                return {
                    "status": "error",
                    "error": result["error"]
                }
                
        except Exception as e:
            log.error(f"Login error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": "Login failed. Please try again."
            }
    
    @app.post("/api/auth/verify")
    def api_verify_token(request: Dict[str, Any]) -> Dict[str, Any]:
        """Verify a session token."""
        try:
            token = request.get("token")
            
            if not token:
                return {
                    "status": "error",
                    "error": "Token is required"
                }
            
            user = auth_manager.verify_token(token)
            
            if user:
                return {
                    "status": "ok",
                    "user": user
                }
            else:
                return {
                    "status": "error",
                    "error": "Invalid or expired token"
                }
                
        except Exception as e:
            log.error(f"Token verification error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": "Token verification failed"
            }
    
    @app.post("/api/auth/logout")
    def api_logout(request: Dict[str, Any]) -> Dict[str, Any]:
        """Logout a user (invalidate session token)."""
        try:
            token = request.get("token")
            
            if not token:
                return {
                    "status": "error",
                    "error": "Token is required"
                }
            
            success = auth_manager.logout_user(token)
            
            if success:
                return {
                    "status": "ok",
                    "message": "Logged out successfully"
                }
            else:
                return {
                    "status": "error",
                    "error": "Logout failed"
                }
                
        except Exception as e:
            log.error(f"Logout error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": "Logout failed"
            }
    
    # ------------------------------------------------------------------
    # User Preferences API
    # ------------------------------------------------------------------
    
    @app.get("/api/user/preferences")
    def api_get_user_preferences() -> Dict[str, Any]:
        """Get user preferences (e.g., default application)."""
        try:
            # For now, return empty preferences (can be extended to use database)
            # In the future, this could store preferences per user in a database
            # Returning None means frontend will use system default (start app - Modern Solar Monitoring)
            return {
                "status": "ok",
                "default_app": None,  # None = use system default (start app for both mobile and desktop)
            }
        except Exception as e:
            log.error(f"Error getting user preferences: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
    
    @app.post("/api/user/preferences")
    def api_set_user_preferences(preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Set user preferences (e.g., default application)."""
        try:
            # For now, just log the preference (can be extended to use database)
            # In the future, this could store preferences per user in a database
            default_app = preferences.get("default_app")
            if default_app:
                log.info(f"User preference set: default_app={default_app}")
                # TODO: Store in database for persistence across sessions
                # For now, preferences are session-based (stored in frontend localStorage as fallback)
            
            return {
                "status": "ok",
                "message": "Preferences updated successfully"
            }
        except Exception as e:
            log.error(f"Error setting user preferences: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }

    # ------------------------------------------------------------------
    # Billing & capacity analysis endpoints
    # ------------------------------------------------------------------

    @app.get("/api/billing/simulate")
    def api_billing_simulate(year: Optional[int] = None, inverter_id: str = "all") -> Dict[str, Any]:
        """
        Run billing simulation for a given year.

        Returns per‑month energy/billing breakdown and annual summary.
        """
        try:
            from solarhub.timezone_utils import now_configured

            if year is None:
                year = now_configured().year

            if not solar_app.logger or not getattr(solar_app.logger, "path", None):
                return {
                    "status": "error",
                    "error": "No database available for billing simulation",
                }

            cfg = getattr(solar_app, "cfg", None)
            billing_cfg = getattr(cfg, "billing", None)
            if billing_cfg is None:
                return {
                    "status": "error",
                    "error": "Billing configuration not available",
                }

            result = simulate_billing_year(
                db_path=solar_app.logger.path,
                billing_cfg=billing_cfg,
                year=year,
                inverter_id=inverter_id,
            )

            # Attach capacity approximation
            installed_kw = 0.0
            if cfg and getattr(cfg, "inverters", None):
                for inv in cfg.inverters:
                    for solar in getattr(inv, "solar", []):
                        installed_kw += float(getattr(solar, "pv_dc_kw", 0.0) or 0.0)

            capacity = estimate_capacity_status(result, installed_kw, billing_cfg)

            # Simple forecast for next month in the same year
            forecast = forecast_next_billing(
                annual_billing=result,
                billing_cfg=billing_cfg,
                months_ahead=1,
                method=billing_cfg.forecast.default_method,
            )

            return {
                "status": "ok",
                "year": year,
                "billing": result,
                "capacity": capacity,
                "forecast_next": forecast,
            }
        except Exception as e:
            log.error(f"Error in /api/billing/simulate: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    @app.get("/api/billing/summary")
    def api_billing_summary(year: Optional[int] = None) -> Dict[str, Any]:
        """
        Convenience endpoint: returns only the current billing month's summary
        and high‑level annual summary for the given year.
        """
        try:
            from solarhub.timezone_utils import now_configured

            if year is None:
                now = now_configured()
                year = now.year

            sim = api_billing_simulate(year=year)
            if sim.get("status") != "ok":
                return sim

            billing = sim["billing"]
            months = billing.get("months", [])

            # Pick the last month as "current" (billing months are sequential)
            current_month = months[-1] if months else None

            return {
                "status": "ok",
                "year": year,
                "current": current_month,
                "summary": billing.get("summary", {}),
                "capacity": sim.get("capacity"),
                "forecast_next": sim.get("forecast_next"),
            }
        except Exception as e:
            log.error(f"Error in /api/billing/summary: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    @app.get("/api/billing/running")
    async def api_billing_running(
        date: Optional[str] = None,
        inverter_id: str = "all"
    ):
        """Get current-month to-date billing status and provisional bill."""
        try:
            if not solar_app.config_manager or not solar_app.logger:
                return {"error": "Configuration or database not available"}
            
            # Get config from cache or load it
            config = solar_app.config_manager._config_cache
            if not config:
                config = solar_app.config_manager.load_config()
            if not config or not config.billing:
                return {"error": "Billing configuration not found"}
            
            billing_cfg = config.billing
            
            from solarhub.timezone_utils import now_configured
            from solarhub.billing_scheduler import _compute_daily_snapshot
            import sqlite3
            
            # Use configured timezone for today's date
            target_date = now_configured().date()
            if date:
                try:
                    target_date = datetime.fromisoformat(date).date()
                except:
                    pass
            
            target_date_str = target_date.isoformat()
            
            # Try to get today's snapshot from billing_daily table first (if scheduler already ran)
            try:
                conn = sqlite3.connect(solar_app.logger.path)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("""
                    SELECT * FROM billing_daily
                    WHERE site_id = 'default' AND date = ?
                    ORDER BY generated_at_ts DESC
                    LIMIT 1
                """, (target_date_str,))
                row = cur.fetchone()
                conn.close()
                
                if row:
                    # Use data from database (scheduler already calculated today)
                    return {
                        "date": row["date"],
                        "billing_month_id": row["billing_month_id"],
                        "import_off_kwh": row["import_off_kwh"],
                        "export_off_kwh": row["export_off_kwh"],
                        "import_peak_kwh": row["import_peak_kwh"],
                        "export_peak_kwh": row["export_peak_kwh"],
                        "net_import_off_kwh": row["net_import_off_kwh"],
                        "net_import_peak_kwh": row["net_import_peak_kwh"],
                        "credits_off_cycle_kwh_balance": row["credits_off_cycle_kwh_balance"],
                        "credits_peak_cycle_kwh_balance": row["credits_peak_cycle_kwh_balance"],
                        "bill_off_energy_rs": row["bill_off_energy_rs"],
                        "bill_peak_energy_rs": row["bill_peak_energy_rs"],
                        "fixed_prorated_rs": row["fixed_prorated_rs"],
                        "expected_cycle_credit_rs": row["expected_cycle_credit_rs"],
                        "bill_raw_rs_to_date": row["bill_raw_rs_to_date"],
                        "bill_credit_balance_rs_to_date": row["bill_credit_balance_rs_to_date"],
                        "bill_final_rs_to_date": row["bill_final_rs_to_date"],
                        "surplus_deficit_flag": row["surplus_deficit_flag"],
                    }
            except Exception as db_e:
                log.debug(f"Error reading from billing_daily table: {db_e}, computing snapshot...")
            
            # No snapshot in DB yet, compute it using scheduler logic
            snapshot = _compute_daily_snapshot(
                solar_app.logger.path,
                billing_cfg,
                target_date,
                inverter_id,
                "default"
            )
            
            if not snapshot:
                return {"error": "Failed to compute daily snapshot"}
            
            # Convert snapshot to dict
            return {
                "date": snapshot.date.isoformat(),
                "billing_month_id": snapshot.billing_month_id,
                "import_off_kwh": snapshot.import_off_kwh,
                "export_off_kwh": snapshot.export_off_kwh,
                "import_peak_kwh": snapshot.import_peak_kwh,
                "export_peak_kwh": snapshot.export_peak_kwh,
                "net_import_off_kwh": snapshot.net_import_off_kwh,
                "net_import_peak_kwh": snapshot.net_import_peak_kwh,
                "credits_off_cycle_kwh_balance": snapshot.credits_off_cycle_kwh_balance,
                "credits_peak_cycle_kwh_balance": snapshot.credits_peak_cycle_kwh_balance,
                "bill_off_energy_rs": snapshot.bill_off_energy_rs,
                "bill_peak_energy_rs": snapshot.bill_peak_energy_rs,
                "fixed_prorated_rs": snapshot.fixed_prorated_rs,
                "expected_cycle_credit_rs": snapshot.expected_cycle_credit_rs,
                "bill_raw_rs_to_date": snapshot.bill_raw_rs_to_date,
                "bill_credit_balance_rs_to_date": snapshot.bill_credit_balance_rs_to_date,
                "bill_final_rs_to_date": snapshot.bill_final_rs_to_date,
                "surplus_deficit_flag": snapshot.surplus_deficit_flag,
            }
        except Exception as e:
            log.error(f"Error getting running bill: {e}", exc_info=True)
            return {"error": str(e)}
    
    @app.get("/api/billing/daily")
    async def api_billing_daily(
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        inverter_id: str = "all"
    ):
        """Get time-series daily billing data for sparklines."""
        try:
            if not solar_app.logger:
                return {"error": "Database not available"}
            
            import sqlite3
            from solarhub.timezone_utils import now_configured
            
            # Default to last 30 days if not specified
            if not from_date:
                today = now_configured().date()
                from_date_obj = today - timedelta(days=30)
                from_date = from_date_obj.isoformat()
            
            if not to_date:
                to_date = now_configured().date().isoformat()
            
            conn = sqlite3.connect(solar_app.logger.path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            try:
                cur.execute("""
                    SELECT * FROM billing_daily
                    WHERE site_id = 'default' AND date >= ? AND date <= ?
                    ORDER BY date ASC
                """, (from_date, to_date))
                
                rows = cur.fetchall()
                data = [dict(row) for row in rows]
                
                log.debug(f"Retrieved {len(data)} billing daily records from {from_date} to {to_date}")
                
                return {
                    "from_date": from_date,
                    "to_date": to_date,
                    "inverter_id": inverter_id,
                    "data": data
                }
            finally:
                conn.close()
        except Exception as e:
            log.error(f"Error getting daily billing data: {e}", exc_info=True)
            return {"error": str(e)}
    
    @app.post("/api/billing/trigger")
    async def api_billing_trigger(
        date: Optional[str] = None,
        inverter_id: str = "all",
        backfill: bool = True
    ):
        """Manually trigger the billing scheduler to compute and save today's billing snapshot."""
        try:
            if not solar_app.config_manager or not solar_app.logger:
                return {"status": "error", "error": "Configuration or database not available"}
            
            # Get config from cache or load it
            config = solar_app.config_manager._config_cache
            if not config:
                config = solar_app.config_manager.load_config()
            if not config or not config.billing:
                return {"status": "error", "error": "Billing configuration not found"}
            
            billing_cfg = config.billing
            
            from solarhub.timezone_utils import now_configured, get_configured_timezone
            from solarhub.billing_scheduler import run_daily_billing_job, _get_current_billing_month
            from datetime import timedelta
            
            # Use configured timezone for today's date
            target_date = now_configured().date()
            if date:
                try:
                    target_date = datetime.fromisoformat(date).date()
                except:
                    pass
            
            log.info(f"Manually triggering billing scheduler for {target_date}")
            
            # Backfill hourly energy data for the billing month if requested
            if backfill:
                try:
                    tz = get_configured_timezone()
                    month_start, month_end, month_label = _get_current_billing_month(target_date, billing_cfg.anchor_day, tz)
                    month_start_date = month_start.date()
                    
                    log.info(f"Backfilling hourly energy data from {month_start_date} to {target_date}")
                    
                    # Get all inverter IDs
                    inverter_ids = []
                    if inverter_id == "all" and solar_app.cfg.arrays:
                        for array_cfg in solar_app.cfg.arrays:
                            inverter_ids.extend(array_cfg.inverter_ids)
                    elif inverter_id != "all":
                        inverter_ids = [inverter_id]
                    else:
                        # Fallback: get from configured inverters
                        if solar_app.cfg.inverters:
                            inverter_ids = [inv.id for inv in solar_app.cfg.inverters if getattr(inv, 'id', None)]
                    
                    if not inverter_ids:
                        log.warning("No inverters found for backfill")
                    else:
                        # Backfill hourly energy for each day from month start to target date
                        current_date = month_start_date
                        hours_backfilled = 0
                        while current_date <= target_date:
                            # Backfill all 24 hours for this day
                            for hour in range(24):
                                hour_start = tz.localize(datetime.combine(current_date, datetime.min.time().replace(hour=hour)))
                                
                                for inv_id in inverter_ids:
                                    try:
                                        solar_app.energy_calculator.calculate_and_store_hourly_energy(
                                            inverter_id=inv_id,
                                            hour_start=hour_start
                                        )
                                        hours_backfilled += 1
                                    except Exception as e:
                                        log.debug(f"Backfill failed for {inv_id} at {hour_start}: {e}")
                            
                            current_date += timedelta(days=1)
                        
                        log.info(f"Backfilled {hours_backfilled} hours of energy data for {len(inverter_ids)} inverters")
                    
                    # Backfill meter hourly energy for home-attached meters
                    from solarhub.meter_energy_calculator import MeterEnergyCalculator
                    from solarhub.billing_scheduler import _get_home_meters
                    
                    meter_calc = MeterEnergyCalculator(solar_app.logger.path)
                    
                    # Get home ID (default to "home")
                    home_id = config.home.id if config.home else "home"
                    home_meter_ids = _get_home_meters(config, home_id)
                    
                    if home_meter_ids:
                        log.info(f"Backfilling meter hourly energy for home {home_id} (meters: {home_meter_ids})")
                        month_start_datetime = tz.localize(datetime.combine(month_start_date, datetime.min.time()))
                        target_datetime = tz.localize(datetime.combine(target_date, datetime.max.time()))
                        
                        total_meter_hours = 0
                        for meter_id in home_meter_ids:
                            try:
                                hours = meter_calc.backfill_hourly_energy_for_date_range(
                                    meter_id=meter_id,
                                    start_date=month_start_datetime,
                                    end_date=target_datetime
                                )
                                total_meter_hours += hours
                            except Exception as e:
                                log.warning(f"Failed to backfill meter {meter_id}: {e}", exc_info=True)
                        
                        log.info(f"Backfilled {total_meter_hours} hours of meter energy data for {len(home_meter_ids)} meters")
                    else:
                        log.debug(f"No home-attached meters found for home {home_id}, skipping meter backfill")
                        
                except Exception as e:
                    log.warning(f"Error during backfill (continuing with billing): {e}", exc_info=True)
            
            # Run the daily billing job (now supports home-level billing)
            success = run_daily_billing_job(
                solar_app.logger.path,
                billing_cfg,
                config,  # Pass hub_cfg
                target_date,
                home_id=None,  # Process all homes
                site_id="default"
            )
            
            if success:
                return {
                    "status": "success",
                    "message": f"Billing scheduler completed successfully for {target_date.isoformat()}",
                    "date": target_date.isoformat(),
                    "backfilled": backfill
                }
            else:
                return {
                    "status": "error",
                    "error": "Billing scheduler failed. Check logs for details."
                }
        except Exception as e:
            log.error(f"Error triggering billing scheduler: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    @app.post("/api/meter/backfill")
    async def api_meter_backfill(
        meter_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        home_id: Optional[str] = None
    ):
        """
        Manually trigger backfill of meter hourly energy from meter_samples data.
        
        Args:
            meter_id: Specific meter ID to backfill (if not provided, all home-attached meters are used)
            start_date: Start date in ISO format (YYYY-MM-DD). Defaults to start of current billing month.
            end_date: End date in ISO format (YYYY-MM-DD). Defaults to today.
            home_id: Home ID to get meters from (defaults to configured home or "home")
        """
        try:
            if not solar_app.config_manager or not solar_app.logger:
                return {"status": "error", "error": "Configuration or database not available"}
            
            from solarhub.meter_energy_calculator import MeterEnergyCalculator
            from solarhub.billing_scheduler import _get_home_meters, _get_current_billing_month
            from solarhub.timezone_utils import now_configured, get_configured_timezone
            from datetime import datetime, timedelta
            
            tz = get_configured_timezone()
            meter_calc = MeterEnergyCalculator(solar_app.logger.path)
            
            # Get config
            config = solar_app.config_manager._config_cache
            if not config:
                config = solar_app.config_manager.load_config()
            
            # Determine date range
            if end_date:
                try:
                    end_datetime = tz.localize(datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59))
                except:
                    end_datetime = now_configured().replace(hour=23, minute=59, second=59)
            else:
                end_datetime = now_configured().replace(hour=23, minute=59, second=59)
            
            if start_date:
                try:
                    start_datetime = tz.localize(datetime.fromisoformat(start_date).replace(hour=0, minute=0, second=0))
                except:
                    # Default to start of current billing month
                    if config and config.billing:
                        month_start, _, _ = _get_current_billing_month(end_datetime.date(), config.billing.anchor_day, tz)
                        start_datetime = month_start
                    else:
                        start_datetime = end_datetime.replace(day=1, hour=0, minute=0, second=0)
            else:
                # Default to start of current billing month
                if config and config.billing:
                    month_start, _, _ = _get_current_billing_month(end_datetime.date(), config.billing.anchor_day, tz)
                    start_datetime = month_start
                else:
                    start_datetime = end_datetime.replace(day=1, hour=0, minute=0, second=0)
            
            # Get meter IDs
            meter_ids = []
            if meter_id:
                meter_ids = [meter_id]
            else:
                # Get home-attached meters
                target_home_id = home_id or (config.home.id if config and config.home else "home")
                if config:
                    meter_ids = _get_home_meters(config, target_home_id)
                else:
                    return {"status": "error", "error": "Configuration not available"}
            
            if not meter_ids:
                return {
                    "status": "error",
                    "error": f"No meters found for home {target_home_id}. Specify meter_id or ensure meters are attached to home."
                }
            
            log.info(f"Backfilling meter hourly energy for {len(meter_ids)} meter(s) from {start_datetime.date()} to {end_datetime.date()}")
            
            results = {}
            total_hours = 0
            for mid in meter_ids:
                try:
                    hours = meter_calc.backfill_hourly_energy_for_date_range(
                        meter_id=mid,
                        start_date=start_datetime,
                        end_date=end_datetime
                    )
                    results[mid] = {"hours_backfilled": hours, "status": "success"}
                    total_hours += hours
                except Exception as e:
                    log.error(f"Failed to backfill meter {mid}: {e}", exc_info=True)
                    results[mid] = {"hours_backfilled": 0, "status": "error", "error": str(e)}
            
            return {
                "status": "success",
                "message": f"Backfilled {total_hours} hours of meter energy data",
                "start_date": start_datetime.date().isoformat(),
                "end_date": end_datetime.date().isoformat(),
                "meters": results,
                "total_hours": total_hours
            }
            
        except Exception as e:
            log.error(f"Error backfilling meter hourly energy: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    @app.post("/api/billing/cycle/close")
    async def api_billing_cycle_close(
        cycle_id: Optional[str] = None,
        force: bool = False
    ):
        """Admin endpoint to force close a billing cycle (with safety checks)."""
        try:
            if not solar_app.config_manager or not solar_app.logger:
                return {"error": "Configuration or database not available"}
            
            # TODO: Implement cycle closing logic
            # This would require tracking cycle state and finalizing settlements
            
            return {
                "status": "not_implemented",
                "message": "Cycle closing logic to be implemented"
            }
        except Exception as e:
            log.error(f"Error closing billing cycle: {e}", exc_info=True)
            return {"error": str(e)}
    
    @app.get("/api/billing/month/{month_id}")
    async def api_billing_month(month_id: str):
        """Get finalized monthly billing record."""
        try:
            if not solar_app.logger:
                return {"error": "Database not available"}
            
            import sqlite3
            
            conn = sqlite3.connect(solar_app.logger.path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            try:
                cur.execute("""
                    SELECT * FROM billing_months
                    WHERE id = ?
                """, (month_id,))
                
                row = cur.fetchone()
                if not row:
                    return {"error": "Month not found"}
                
                return dict(row)
            finally:
                conn.close()
        except Exception as e:
            log.error(f"Error getting billing month: {e}", exc_info=True)
            return {"error": str(e)}
    
    @app.get("/api/billing/trend")
    def api_billing_trend(year: Optional[int] = None) -> Dict[str, Any]:
        """
        Returns per‑month billing trend (energy + final bill) for charting.
        """
        try:
            from solarhub.timezone_utils import now_configured

            if year is None:
                year = now_configured().year

            sim = api_billing_simulate(year=year)
            if sim.get("status") != "ok":
                return sim

            billing = sim["billing"]
            months = billing.get("months", [])

            trend = [
                {
                    "billingMonth": m["billingMonth"],
                    "final_bill": m["final_bill"],
                    "import_off_kwh": m["import_off_kwh"],
                    "import_peak_kwh": m["import_peak_kwh"],
                    "export_off_kwh": m["export_off_kwh"],
                    "export_peak_kwh": m["export_peak_kwh"],
                }
                for m in months
            ]

            return {
                "status": "ok",
                "year": year,
                "trend": trend,
                "summary": billing.get("summary", {}),
            }
        except Exception as e:
            log.error(f"Error in /api/billing/trend: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    @app.get("/api/capacity/status")
    def api_capacity_status(year: Optional[int] = None) -> Dict[str, Any]:
        """
        Returns installed capacity and approximate required capacity for zero-bill scenario.
        """
        try:
            from solarhub.timezone_utils import now_configured

            if year is None:
                year = now_configured().year

            sim = api_billing_simulate(year=year)
            if sim.get("status") != "ok":
                return sim

            return {
                "status": "ok",
                "year": year,
                "capacity": sim.get("capacity"),
            }
        except Exception as e:
            log.error(f"Error in /api/capacity/status: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    @app.get("/api/inverter/sensors")
    def api_get_inverter_sensors(inverter_id: str = "senergy1") -> Dict[str, Any]:
        """Get editable inverter sensors and their current values."""
        try:
            log.info(f"API /api/inverter/sensors called for inverter_id: {inverter_id}")
            
            # Get current telemetry data
            tel = solar_app.get_now(inverter_id)
            if not tel:
                return {
                    "sensors": [],
                    "source": "error",
                    "error": "No telemetry data available"
                }
            
            # Define editable sensors based on register map
            editable_sensors = [
                {
                    "id": "maximum_feed_in_grid_power",
                    "name": "Maximum Feed-in Grid Power",
                    "type": "number",
                    "unit": "W",
                    "min": 0,
                    "max": 20000,
                    "step": 100,
                    "current_value": tel.get("extra", {}).get("maximum_feed_in_grid_power", 0),
                    "description": "Maximum power that can be fed into the grid"
                },
                {
                    "id": "inverter_control",
                    "name": "Inverter Control",
                    "type": "select",
                    "options": [
                        {"value": 0, "label": "Power On"},
                        {"value": 1, "label": "Shut Down"}
                    ],
                    "current_value": tel.get("extra", {}).get("inverter_control", 0),
                    "description": "Control inverter power state"
                },
                {
                    "id": "grid_charge",
                    "name": "Grid Charge",
                    "type": "boolean",
                    "current_value": tel.get("extra", {}).get("grid_charge", False),
                    "description": "Enable/disable grid charging"
                },
                {
                    "id": "maximum_grid_charger_power",
                    "name": "Maximum Grid Charger Power",
                    "type": "number",
                    "unit": "W",
                    "min": 0,
                    "max": 10000,
                    "step": 100,
                    "current_value": tel.get("extra", {}).get("maximum_grid_charger_power", 0),
                    "description": "Maximum power for grid charging"
                },
                {
                    "id": "maximum_charger_power",
                    "name": "Maximum Charger Power",
                    "type": "number",
                    "unit": "W",
                    "min": 0,
                    "max": 10000,
                    "step": 100,
                    "current_value": tel.get("extra", {}).get("maximum_charger_power", 0),
                    "description": "Maximum total charging power"
                },
                {
                    "id": "maximum_discharger_power",
                    "name": "Maximum Discharger Power",
                    "type": "number",
                    "unit": "W",
                    "min": 0,
                    "max": 10000,
                    "step": 100,
                    "current_value": tel.get("extra", {}).get("maximum_discharger_power", 0),
                    "description": "Maximum discharging power"
                },
                {
                    "id": "off_grid_mode",
                    "name": "Off-Grid Mode",
                    "type": "boolean",
                    "current_value": tel.get("extra", {}).get("off_grid_mode", False),
                    "description": "Enable/disable off-grid mode"
                },
                {
                    "id": "off_grid_start_up_battery_capacity",
                    "name": "Off-Grid Startup Battery Capacity",
                    "type": "number",
                    "unit": "%",
                    "min": 0,
                    "max": 100,
                    "step": 1,
                    "current_value": tel.get("extra", {}).get("off_grid_start_up_battery_capacity", 30),
                    "description": "Minimum battery capacity to start in off-grid mode"
                }
            ]
            
            return {
                "inverter_id": inverter_id,
                "sensors": editable_sensors,
                "source": "telemetry"
            }
            
        except Exception as e:
            log.error(f"Error getting inverter sensors: {e}", exc_info=True)
            return {
                "sensors": [],
                "source": "error",
                "error": str(e)
            }

    @app.post("/api/inverter/sensors/{sensor_id}")
    async def api_update_inverter_sensor(inverter_id: str, sensor_id: str, sensor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an inverter sensor value by directly calling the adapter."""
        try:
            log.info(f"API /api/inverter/sensors/{sensor_id} called for inverter_id: {inverter_id}")
            log.info(f"Sensor data: {sensor_data}")
            
            # Get the new value
            new_value = sensor_data.get("value")
            if new_value is None:
                return {
                    "status": "error",
                    "message": "No value provided"
                }
            
            # Find the inverter runtime
            rt = None
            for inv_rt in solar_app.inverters:
                if inv_rt.cfg.id == inverter_id:
                    rt = inv_rt
                    break
            
            if not rt:
                return {
                    "status": "error",
                    "message": f"Inverter {inverter_id} not found or not connected"
                }
            
            adapter = rt.adapter
            
            # Map sensor IDs to action commands or register IDs
            # Some sensors use action commands, others use direct register writes
            sensor_action_map = {
                "grid_charge": "set_grid_charge",
                "maximum_grid_charger_power": "set_max_grid_charge_power_w",
                "maximum_charger_power": "set_max_charge_power_w",
                "maximum_discharger_power": "set_max_discharge_power_w",
            }
            
            sensor_to_register_map = {
                "maximum_feed_in_grid_power": "max_export_power_w",
                "inverter_control": "power_on_off_status",
                "off_grid_mode": "off_grid_mode",
                "off_grid_start_up_battery_capacity": "off_grid_start_up_battery_capacity",
            }
            
            # Check if sensor uses an action command
            action = sensor_action_map.get(sensor_id)
            if action:
                # Create action-based command
                if sensor_id == "grid_charge":
                    cmd = {
                        "action": action,
                        "enable": bool(new_value),
                        "end_soc": None  # Can be set if provided in sensor_data
                    }
                elif sensor_id in ("maximum_grid_charger_power", "maximum_charger_power", "maximum_discharger_power"):
                    cmd = {
                        "action": action,
                        "value": int(new_value)
                    }
                else:
                    cmd = {
                        "action": action,
                        "value": new_value
                    }
                
                log.info(f"Writing sensor {sensor_id} using action {action} with value {new_value}")
            else:
                # Use direct register write
                register_id = sensor_to_register_map.get(sensor_id, sensor_id)
                cmd = {
                    "action": "write",
                    "id": register_id,
                    "value": new_value
                }
                log.info(f"Writing sensor {sensor_id} (register {register_id}) = {new_value}")
            
            # Execute write command via adapter
            result = await adapter.handle_command(cmd)
            
            if not result.get("ok", False):
                return {
                    "status": "error",
                    "message": result.get("reason", "Failed to write sensor value")
                }
            
            # Read back the value to confirm (for direct register writes only)
            # Note: We skip read-back to avoid triggering client recreation in API server's event loop
            # The write operation itself is sufficient confirmation
            confirmed_value = new_value
            # Skip read-back to avoid event loop conflicts - write operation is confirmation enough
            if action:
                log.info(f"Action command {action} executed successfully for sensor {sensor_id}")
            else:
                log.info(f"Sensor {sensor_id} write command executed, using provided value as confirmed")
            
            return {
                "status": "success",
                "message": f"Sensor {sensor_id} updated successfully",
                "sensor_id": sensor_id,
                "value": confirmed_value
            }
                
        except Exception as e:
            log.error(f"Error updating inverter sensor {sensor_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }

    @app.post("/api/inverter/registers/{register_name}")
    async def api_write_inverter_register(inverter_id: str, register_name: str, register_data: Dict[str, Any]) -> Dict[str, Any]:
        """Write to an inverter register by name/address and update memory objects."""
        try:
            import asyncio
            log.info(f"API /api/inverter/registers/{register_name} called for inverter_id: {inverter_id}")
            log.info(f"Register data: {register_data}")
            
            # Get the new value
            new_value = register_data.get("value")
            if new_value is None:
                return {
                    "status": "error",
                    "message": "No value provided"
                }
            
            # Find the inverter runtime
            rt = None
            for inv_rt in solar_app.inverters:
                if inv_rt.cfg.id == inverter_id:
                    rt = inv_rt
                    break
            
            if not rt:
                return {
                    "status": "error",
                    "message": f"Inverter {inverter_id} not found"
                }
            
            adapter = rt.adapter
            if not hasattr(adapter, 'regs') or not adapter.regs:
                return {
                    "status": "error",
                    "message": "Register map not available"
                }
            
            # Find the register by name or address
            register = None
            for reg in adapter.regs:
                if (reg.get("name", "").lower() == register_name.lower() or 
                    str(reg.get("addr", "")) == register_name or
                    reg.get("id", "") == register_name):
                    register = reg
                    break
            
            if not register:
                return {
                    "status": "error",
                    "message": f"Register {register_name} not found"
                }
            
            # Validate register is writeable
            if register.get("kind", "").lower() != "holding":
                return {
                    "status": "error",
                    "message": f"Register {register_name} is not a holding register (cannot write)"
                }
            
            if str(register.get("rw", "RO")).upper() not in ("RW", "WO", "R/W"):
                return {
                    "status": "error",
                    "message": f"Register {register_name} is read-only"
                }
            
            # Write to inverter via adapter
            log.info(f"Writing register {register_name} (addr: {register.get('addr')}) = {new_value}")
            cmd = {
                "action": "write",
                "id": register_name,  # Use name as identifier
                "value": new_value
            }
            
            # Execute write command
            result = await adapter.handle_command(cmd)
            
            if not result.get("ok", False):
                return {
                    "status": "error",
                    "message": result.get("reason", "Failed to write register")
                }
            
            # Skip read-back to avoid triggering client recreation in API server's event loop
            # The write operation itself is sufficient confirmation
            confirmed_value = new_value
            log.info(f"Register {register_name} write command executed, using provided value as confirmed")
            
            # Update in-memory telemetry object (last_tel)
            if hasattr(adapter, 'last_tel') and adapter.last_tel:
                # Map register name to telemetry field name
                register_id = register.get("id", "")
                register_name_lower = register.get("name", "").lower().replace(" ", "_").replace("-", "_")
                register_addr = register.get("addr", "")
                
                # Try multiple possible field names - check how register is stored in poll()
                # The adapter's poll() method stores values in extra dict using register id or name
                field_key = None
                if register_id:
                    field_key = register_id
                elif register_name_lower:
                    field_key = register_name_lower
                else:
                    # Generate field key from address (hex format like reg_2100)
                    field_key = f"reg_{int(register_addr):04x}"
                
                # Ensure extra dict exists
                if not adapter.last_tel.extra:
                    adapter.last_tel.extra = {}
                
                # Update in extra dict (where all register values are stored during polling)
                adapter.last_tel.extra[field_key] = confirmed_value
                
                # Also try updating by register name variations
                if register.get("name"):
                    name_key = register.get("name").lower().replace(" ", "_").replace("-", "_")
                    adapter.last_tel.extra[name_key] = confirmed_value
                
                # Also update at top level if it's a known telemetry field
                telemetry_field_map = {
                    "hybrid_work_mode": "inverter_mode",
                    "grid_charge": "grid_charge",
                    "maximum_grid_charger_power": "maximum_grid_charger_power",
                    "capacity_of_grid_charger_end": "grid_charge_end_soc",
                    "maximum_charger_power": "maximum_charger_power",
                    "capacity_of_charger_end_soc_": "charge_end_soc",
                    "maximum_discharger_power": "maximum_discharger_power",
                    "capacity_of_discharger_end_eod_": "discharge_end_soc",
                    "off_grid_mode": "off_grid_mode",
                    "off_grid_start_up_battery_capacity": "off_grid_start_up_battery_capacity"
                }
                
                # Check if any field key matches known telemetry fields
                for key_variant in [field_key, register_id, register_name_lower]:
                    if key_variant in telemetry_field_map:
                        tel_field = telemetry_field_map[key_variant]
                        setattr(adapter.last_tel, tel_field, confirmed_value)
                        adapter.last_tel.extra[tel_field] = confirmed_value
                        break
                
                log.info(f"Updated in-memory telemetry for register {register_name} = {confirmed_value} (field_key: {field_key})")
            
            # Save to database for persistence
            if solar_app.logger:
                try:
                    config_path = f"inverter.{inverter_id}.{register_name}"
                    value_str = str(confirmed_value) if not isinstance(confirmed_value, (dict, list)) else json.dumps(confirmed_value)
                    solar_app.logger.set_config(config_path, value_str, "api")
                    log.info(f"Saved register {register_name} to database")
                except Exception as e:
                    log.warning(f"Failed to save register to database: {e}")
            
            # Republish via MQTT if available
            if solar_app.mqtt and hasattr(adapter, 'last_tel') and adapter.last_tel:
                try:
                    # Convert Telemetry object to dict for MQTT
                    if hasattr(adapter.last_tel, 'model_dump'):
                        telemetry_data = adapter.last_tel.model_dump()
                    elif hasattr(adapter.last_tel, 'dict'):
                        telemetry_data = adapter.last_tel.dict()
                    else:
                        # Fallback: convert manually
                        telemetry_data = {
                            "id": inverter_id
                        }
                        if adapter.last_tel.extra:
                            telemetry_data.update(adapter.last_tel.extra)
                    
                    topic = f"{solar_app.cfg.mqtt.base_topic}/{inverter_id}/regs"
                    solar_app.mqtt.pub(topic, telemetry_data, retain=False)
                    log.debug(f"Republished telemetry with updated register {register_name}")
                except Exception as e:
                    log.warning(f"Failed to republish telemetry: {e}")
            
            return {
                "status": "success",
                "message": f"Register {register_name} updated successfully",
                "register_name": register_name,
                "register_address": register.get("addr"),
                "value": confirmed_value
            }
                
        except Exception as e:
            log.error(f"Error writing inverter register {register_name}: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }

    # ==================== Settings Endpoints ====================
    
    async def _read_settings_registers(adapter, register_ids: List[str]) -> Dict[str, Any]:
        """Read multiple settings registers from inverter."""
        settings = {}
        
        # Helper to ensure client connection with retry
        async def ensure_client_connected():
            """Ensure client is connected, with retry logic."""
            if hasattr(adapter, '_ensure_client_in_current_loop'):
                try:
                    await adapter._ensure_client_in_current_loop()
                    # Verify client is actually connected
                    if hasattr(adapter, 'client') and adapter.client is not None:
                        if hasattr(adapter.client, 'connected') and adapter.client.connected:
                            return True
                    # If we get here, client might not be connected
                    log.debug("Client connection verification failed, will retry on read")
                    return False
                except Exception as e:
                    log.debug(f"Failed to ensure client connection: {e}")
                    return False
            return True
        
        # Ensure client is connected before reading (for adapters that support it)
        await ensure_client_connected()
        
        for reg_id in register_ids:
            try:
                if hasattr(adapter, 'read_by_ident'):
                    # Retry logic: if read fails with connection error, try to reconnect once
                    max_retries = 2
                    for attempt in range(max_retries):
                        try:
                            value = await adapter.read_by_ident(reg_id)
                            settings[reg_id] = value
                            log.debug(f"Successfully read register {reg_id}: {value}")
                            break  # Success, exit retry loop
                        except (RuntimeError, AttributeError) as e:
                            error_msg = str(e).lower()
                            if ('client not connected' in error_msg or 
                                'nonetype' in error_msg or
                                'read_holding_registers' in error_msg):
                                if attempt < max_retries - 1:
                                    # Try to reconnect before retrying
                                    log.debug(f"Client connection issue on read {reg_id}, attempt {attempt + 1}/{max_retries}, reconnecting...")
                                    await ensure_client_connected()
                                    await asyncio.sleep(0.1)  # Brief delay before retry
                                    continue
                                else:
                                    # Last attempt failed
                                    log.warning(f"Failed to read register {reg_id} after {max_retries} attempts: {e}")
                                    settings[reg_id] = None
                                    break
                            else:
                                # Different error, don't retry
                                raise
                else:
                    log.debug(f"Adapter does not have read_by_ident method")
                    settings[reg_id] = None
            except KeyError as e:
                # Register not found in register map
                log.warning(f"Register {reg_id} not found in register map: {e}")
                settings[reg_id] = None
            except Exception as e:
                log.warning(f"Failed to read register {reg_id}: {e}")
                settings[reg_id] = None
                # Try fallback: read by direct address if register map lookup fails
                try:
                    if hasattr(adapter, 'regs') and adapter.regs:
                        reg_info = adapter.regs.get(reg_id)
                        if reg_info and 'addr' in reg_info:
                            addr = reg_info['addr']
                            size = reg_info.get('size', 1)
                            if hasattr(adapter, '_read_holding_regs'):
                                # Try to ensure client connection before fallback read
                                await ensure_client_connected()
                                raw_value = await adapter._read_holding_regs(addr, size)
                                if raw_value:
                                    # Apply scaling if needed
                                    scale = reg_info.get('scale', 1.0)
                                    if size == 1:
                                        value = raw_value[0] * scale if scale != 1.0 else raw_value[0]
                                    else:
                                        # Multi-register value
                                        value = raw_value[0] if raw_value else None
                                    settings[reg_id] = value
                                    log.debug(f"Successfully read register {reg_id} by direct address {addr}: {value}")
                except Exception as fallback_error:
                    log.debug(f"Fallback read also failed for {reg_id}: {fallback_error}")
        return settings
    
    async def _write_and_verify_registers(adapter, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Write registers and re-read to verify."""
        verified = {}
        for reg_id, value in updates.items():
            try:
                # Write register
                await adapter.write_by_ident(reg_id, value)
                # Re-read to verify
                verified_value = await adapter.read_by_ident(reg_id)
                verified[reg_id] = verified_value
                log.info(f"Verified register {reg_id}: wrote {value}, read back {verified_value}")
            except Exception as e:
                log.error(f"Failed to write/verify register {reg_id}: {e}")
                raise
        return verified

    @app.get("/api/inverter/specification")
    async def api_get_specification(inverter_id: str = "senergy1") -> Dict[str, Any]:
        """Get inverter specification (read-only)."""
        try:
            # Check cache
            cached = solar_app.get_settings_cache(inverter_id, "specification")
            if cached is not None:
                return {"inverter_id": inverter_id, "specification": cached}
            
            # Find inverter
            rt = None
            for inv_rt in solar_app.inverters:
                if inv_rt.cfg.id == inverter_id:
                    rt = inv_rt
                    break
            
            if not rt:
                return {"inverter_id": inverter_id, "specification": None, "error": "Inverter not found"}
            
            adapter = rt.adapter
            spec = {
                "driver": rt.cfg.adapter.type,
                "serial_number": None,
                "protocol_version": None,
                "max_ac_output_power_kw": None,
                "mppt_connections": None,
                "parallel": None,
                "modbus_number": rt.cfg.adapter.unit_id
            }
            
            # Try to get data from telemetry first (already polled)
            if hasattr(adapter, 'last_tel') and adapter.last_tel:
                tel_extra = adapter.last_tel.extra or {}
                spec["serial_number"] = tel_extra.get("device_serial_number") or tel_extra.get("serial_number")
                spec["protocol_version"] = tel_extra.get("protocol_version_raw") or tel_extra.get("protocol_version")
                rated_power = tel_extra.get("rated_power_w") or tel_extra.get("rated_power")
                if rated_power:
                    spec["max_ac_output_power_kw"] = round(float(rated_power) / 1000.0, 1)
                spec["mppt_connections"] = tel_extra.get("mppt_number") or tel_extra.get("mppt_connections") or tel_extra.get("mppt_count")
                spec["parallel"] = tel_extra.get("parallel") or tel_extra.get("parallel_enabled")
            
            # Read specification registers if not found in telemetry
            try:
                if hasattr(adapter, 'read_by_ident'):
                    if not spec["serial_number"]:
                        try:
                            spec["serial_number"] = await adapter.read_by_ident("device_serial_number")
                        except Exception:
                            pass
                    if not spec["protocol_version"]:
                        try:
                            spec["protocol_version"] = await adapter.read_by_ident("protocol_version_raw")
                        except Exception:
                            pass
                    if not spec["max_ac_output_power_kw"]:
                        try:
                            rated_power = await adapter.read_by_ident("rated_power_w")
                            if rated_power:
                                spec["max_ac_output_power_kw"] = round(float(rated_power) / 1000.0, 1)
                        except Exception:
                            pass
                    if not spec["mppt_connections"]:
                        try:
                            # Try mppt_number_and_phases first (Powdrive register 22)
                            mppt_phases = await adapter.read_by_ident("mppt_number_and_phases")
                            if mppt_phases is not None:
                                # Low byte is MPPT number
                                spec["mppt_connections"] = mppt_phases & 0xFF
                                log.info(f"Read MPPT connections from mppt_number_and_phases: {spec['mppt_connections']}")
                        except (KeyError, AttributeError) as e:
                            log.debug(f"Register mppt_number_and_phases not found, trying direct read: {e}")
                            # Fallback: try reading register 22 directly
                            try:
                                if hasattr(adapter, '_read_holding_regs'):
                                    regs = await adapter._read_holding_regs(22, 1)
                                    if regs and len(regs) > 0:
                                        mppt_phases = regs[0]
                                        spec["mppt_connections"] = mppt_phases & 0xFF
                                        log.info(f"Read MPPT connections from register 22: {spec['mppt_connections']}")
                            except Exception as e2:
                                log.debug(f"Failed to read register 22 directly: {e2}")
                                try:
                                    spec["mppt_connections"] = await adapter.read_by_ident("mppt_number")
                                except Exception:
                                    try:
                                        spec["mppt_connections"] = await adapter.read_by_ident("mppt_count")
                                    except Exception:
                                        pass
                        except Exception as e:
                            log.warning(f"Failed to read mppt_number_and_phases: {e}")
                    if not spec["parallel"]:
                        try:
                            # Read parallel register (Powdrive register 336)
                            parallel_reg = await adapter.read_by_ident("parallel_1")
                            if parallel_reg is not None:
                                # Bit0: 1=Parallel Enable, 0=Parallel Disable
                                spec["parallel"] = "Enabled" if (parallel_reg & 0x01) else "Disabled"
                                log.info(f"Read parallel status from parallel_1: {spec['parallel']}")
                        except (KeyError, AttributeError) as e:
                            log.debug(f"Register parallel_1 not found, trying direct read: {e}")
                            # Fallback: try reading register 336 directly
                            try:
                                if hasattr(adapter, '_read_holding_regs'):
                                    regs = await adapter._read_holding_regs(336, 1)
                                    if regs and len(regs) > 0:
                                        parallel_reg = regs[0]
                                        spec["parallel"] = "Enabled" if (parallel_reg & 0x01) else "Disabled"
                                        log.info(f"Read parallel status from register 336: {spec['parallel']}")
                            except Exception as e2:
                                log.debug(f"Failed to read register 336 directly: {e2}")
                        except Exception as e:
                            log.warning(f"Failed to read parallel_1: {e}")
            except Exception as e:
                log.warning(f"Failed to read some specification registers: {e}", exc_info=True)
            
            # Cache the result
            solar_app.set_settings_cache(inverter_id, "specification", spec)
            
            return {"inverter_id": inverter_id, "specification": spec}
        except Exception as e:
            log.error(f"Error getting specification: {e}", exc_info=True)
            return {"inverter_id": inverter_id, "specification": None, "error": str(e)}

    @app.get("/api/inverter/grid-settings")
    async def api_get_grid_settings(inverter_id: str = "senergy1") -> Dict[str, Any]:
        """Get grid settings."""
        try:
            # Check cache
            cached = solar_app.get_settings_cache(inverter_id, "grid_settings")
            if cached is not None:
                return {"inverter_id": inverter_id, "grid_settings": cached}
            
            # Find inverter and read registers
            rt = None
            for inv_rt in solar_app.inverters:
                if inv_rt.cfg.id == inverter_id:
                    rt = inv_rt
                    break
            
            if not rt:
                return {"inverter_id": inverter_id, "grid_settings": None, "error": "Inverter not found"}
            
            adapter = rt.adapter
            
            # Try to get grid frequency from telemetry first (already polled)
            grid_frequency_hz = None
            if hasattr(adapter, 'last_tel') and adapter.last_tel:
                tel_extra = adapter.last_tel.extra or {}
                grid_frequency_hz = tel_extra.get("grid_frequency_hz") or tel_extra.get("grid_frequency")
            
            # Read grid settings registers
            grid_registers = [
                "grid_voltage_high_v", "grid_voltage_low_v",
                "grid_frequency_high_hz", "grid_frequency_low_hz",
                "grid_peak_shaving_power_w", "control_board_special_function_1"
            ]
            
            settings = await _read_settings_registers(adapter, grid_registers)
            
            # Use telemetry value if available, otherwise try to read from register
            if not grid_frequency_hz:
                try:
                    grid_frequency_hz = await adapter.read_by_ident("grid_frequency_hz")
                except Exception:
                    pass
            
            # Extract grid peak shaving enable from control_board_special_function_1 (Bit4-5)
            grid_peak_shaving_enabled = None
            if settings.get("control_board_special_function_1") is not None:
                func1 = settings.get("control_board_special_function_1")
                # Bit4-5: 10=disable, 11=enable
                bits_4_5 = (func1 >> 4) & 0x03
                grid_peak_shaving_enabled = (bits_4_5 == 0x03)  # 11 = enable
            
            # Format response with proper scaling
            grid_settings = {
                "grid_voltage_high_v": round(settings.get("grid_voltage_high_v", 0) / 10.0, 1) if settings.get("grid_voltage_high_v") is not None else None,
                "grid_voltage_low_v": round(settings.get("grid_voltage_low_v", 0) / 10.0, 1) if settings.get("grid_voltage_low_v") is not None else None,
                "grid_frequency_hz": grid_frequency_hz,
                "grid_frequency_high_hz": round(settings.get("grid_frequency_high_hz", 0) / 100.0, 2) if settings.get("grid_frequency_high_hz") is not None else None,
                "grid_frequency_low_hz": round(settings.get("grid_frequency_low_hz", 0) / 100.0, 2) if settings.get("grid_frequency_low_hz") is not None else None,
                "grid_peak_shaving": grid_peak_shaving_enabled,
                "grid_peak_shaving_power_kw": round(settings.get("grid_peak_shaving_power_w", 0) / 1000.0, 2) if settings.get("grid_peak_shaving_power_w") else None
            }
            
            # Cache the result
            solar_app.set_settings_cache(inverter_id, "grid_settings", grid_settings)
            
            return {"inverter_id": inverter_id, "grid_settings": grid_settings}
        except Exception as e:
            log.error(f"Error getting grid settings: {e}", exc_info=True)
            return {"inverter_id": inverter_id, "grid_settings": None, "error": str(e)}

    @app.post("/api/inverter/grid-settings")
    async def api_update_grid_settings(inverter_id: str, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update grid settings."""
        try:
            # Find inverter
            rt = None
            for inv_rt in solar_app.inverters:
                if inv_rt.cfg.id == inverter_id:
                    rt = inv_rt
                    break
            
            if not rt:
                return {"status": "error", "message": "Inverter not found"}
            
            adapter = rt.adapter
            
            # Map frontend fields to register IDs
            updates = {}
            if "grid_voltage_high_v" in settings_data:
                # Convert V to 0.1V units (e.g., 230V -> 2300)
                updates["grid_voltage_high_v"] = int(settings_data["grid_voltage_high_v"] * 10)
            if "grid_voltage_low_v" in settings_data:
                # Convert V to 0.1V units
                updates["grid_voltage_low_v"] = int(settings_data["grid_voltage_low_v"] * 10)
            if "grid_frequency_hz" in settings_data:
                updates["grid_frequency_hz"] = settings_data["grid_frequency_hz"]
            if "grid_frequency_high_hz" in settings_data:
                # Convert Hz to 0.01Hz units (e.g., 50Hz -> 5000)
                updates["grid_frequency_high_hz"] = int(settings_data["grid_frequency_high_hz"] * 100)
            if "grid_frequency_low_hz" in settings_data:
                # Convert Hz to 0.01Hz units
                updates["grid_frequency_low_hz"] = int(settings_data["grid_frequency_low_hz"] * 100)
            if "grid_peak_shaving" in settings_data:
                # Update control_board_special_function_1 Bit4-5
                # Need to read current value, modify bits, then write back
                try:
                    current_func1 = await adapter.read_by_ident("control_board_special_function_1")
                    if current_func1 is None:
                        current_func1 = 0
                    # Clear bits 4-5 (mask 0xFFCF)
                    current_func1 = current_func1 & 0xFFCF
                    # Set bits 4-5: 10=disable, 11=enable
                    if settings_data["grid_peak_shaving"]:
                        current_func1 = current_func1 | 0x0030  # 11 = enable
                    else:
                        current_func1 = current_func1 | 0x0020  # 10 = disable
                    updates["control_board_special_function_1"] = current_func1
                except Exception as e:
                    log.warning(f"Failed to read control_board_special_function_1 for peak shaving update: {e}")
            if "grid_peak_shaving_power_kw" in settings_data:
                updates["grid_peak_shaving_power_w"] = int(settings_data["grid_peak_shaving_power_kw"] * 1000)
            
            # Write and verify
            verified = await _write_and_verify_registers(adapter, updates)
            
            # Update cache with verified values
            cached = solar_app.get_settings_cache(inverter_id, "grid_settings") or {}
            
            # Extract grid peak shaving enable from control_board_special_function_1 if updated
            grid_peak_shaving = None
            if "control_board_special_function_1" in verified:
                func1 = verified.get("control_board_special_function_1")
                bits_4_5 = (func1 >> 4) & 0x03
                grid_peak_shaving = (bits_4_5 == 0x03)
            elif cached.get("grid_peak_shaving") is not None:
                grid_peak_shaving = cached.get("grid_peak_shaving")
            
            cached.update({
                "grid_voltage_high_v": round(verified.get("grid_voltage_high_v", 0) / 10.0, 1) if verified.get("grid_voltage_high_v") else None,
                "grid_voltage_low_v": round(verified.get("grid_voltage_low_v", 0) / 10.0, 1) if verified.get("grid_voltage_low_v") else None,
                "grid_frequency_hz": verified.get("grid_frequency_hz"),
                "grid_frequency_high_hz": round(verified.get("grid_frequency_high_hz", 0) / 100.0, 2) if verified.get("grid_frequency_high_hz") else None,
                "grid_frequency_low_hz": round(verified.get("grid_frequency_low_hz", 0) / 100.0, 2) if verified.get("grid_frequency_low_hz") else None,
                "grid_peak_shaving": grid_peak_shaving,
                "grid_peak_shaving_power_kw": round(verified.get("grid_peak_shaving_power_w", 0) / 1000.0, 2) if verified.get("grid_peak_shaving_power_w") else None
            })
            solar_app.set_settings_cache(inverter_id, "grid_settings", cached)
            
            # Save to database
            if solar_app.logger:
                for reg_id, value in verified.items():
                    solar_app.logger.set_config(f"inverter.{inverter_id}.{reg_id}", str(value), "api")
            
            return {"status": "success", "inverter_id": inverter_id, "grid_settings": cached}
        except Exception as e:
            log.error(f"Error updating grid settings: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    # Similar endpoints for other sections - I'll create a few more key ones
    @app.get("/api/inverter/battery-type")
    async def api_get_battery_type(inverter_id: str = "senergy1") -> Dict[str, Any]:
        """Get battery type settings."""
        try:
            cached = solar_app.get_settings_cache(inverter_id, "battery_type")
            if cached is not None:
                return {"inverter_id": inverter_id, "battery_type": cached}
            
            rt = None
            for inv_rt in solar_app.inverters:
                if inv_rt.cfg.id == inverter_id:
                    rt = inv_rt
                    break
            
            if not rt:
                return {"inverter_id": inverter_id, "battery_type": None, "error": "Inverter not found"}
            
            adapter = rt.adapter
            battery_registers = ["battery_type", "battery_capacity_ah", "battery_mode_source"]
            settings = await _read_settings_registers(adapter, battery_registers)
            
            battery_type_settings = {
                "battery_type": settings.get("battery_type"),
                "battery_capacity_ah": settings.get("battery_capacity_ah"),
                "battery_operation": "State of charge" if settings.get("battery_mode_source") == 1 else "Voltage" if settings.get("battery_mode_source") == 0 else None
            }
            
            solar_app.set_settings_cache(inverter_id, "battery_type", battery_type_settings)
            return {"inverter_id": inverter_id, "battery_type": battery_type_settings}
        except Exception as e:
            log.error(f"Error getting battery type: {e}", exc_info=True)
            return {"inverter_id": inverter_id, "battery_type": None, "error": str(e)}

    @app.post("/api/inverter/battery-type")
    async def api_update_battery_type(inverter_id: str, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update battery type settings."""
        try:
            rt = None
            for inv_rt in solar_app.inverters:
                if inv_rt.cfg.id == inverter_id:
                    rt = inv_rt
                    break
            
            if not rt:
                return {"status": "error", "message": "Inverter not found"}
            
            adapter = rt.adapter
            updates = {}
            
            if "battery_type" in settings_data:
                updates["battery_type"] = settings_data["battery_type"]
            if "battery_capacity_ah" in settings_data:
                updates["battery_capacity_ah"] = settings_data["battery_capacity_ah"]
            if "battery_operation" in settings_data:
                # Map operation mode to register value
                op_mode = 1 if settings_data["battery_operation"] == "State of charge" else 0
                updates["battery_mode_source"] = op_mode
            
            verified = await _write_and_verify_registers(adapter, updates)
            
            cached = solar_app.get_settings_cache(inverter_id, "battery_type") or {}
            cached.update({
                "battery_type": verified.get("battery_type"),
                "battery_capacity_ah": verified.get("battery_capacity_ah"),
                "battery_operation": "State of charge" if verified.get("battery_mode_source") == 1 else "Voltage"
            })
            solar_app.set_settings_cache(inverter_id, "battery_type", cached)
            
            if solar_app.logger:
                for reg_id, value in verified.items():
                    solar_app.logger.set_config(f"inverter.{inverter_id}.{reg_id}", str(value), "api")
            
            return {"status": "success", "inverter_id": inverter_id, "battery_type": cached}
        except Exception as e:
            log.error(f"Error updating battery type: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    @app.get("/api/inverter/battery-charging")
    async def api_get_battery_charging(inverter_id: str = "senergy1") -> Dict[str, Any]:
        """Get battery charging settings."""
        try:
            cached = solar_app.get_settings_cache(inverter_id, "battery_charging")
            if cached is not None:
                return {"inverter_id": inverter_id, "battery_charging": cached}
            
            rt = None
            for inv_rt in solar_app.inverters:
                if inv_rt.cfg.id == inverter_id:
                    rt = inv_rt
                    break
            
            if not rt:
                return {"inverter_id": inverter_id, "battery_charging": None, "error": "Inverter not found"}
            
            adapter = rt.adapter
            adapter_type = rt.cfg.adapter.type if hasattr(rt.cfg, 'adapter') else None
            
            # Get battery voltage for current-to-power conversion (Powdrive)
            battery_voltage_v = None
            if hasattr(adapter, 'last_tel') and adapter.last_tel:
                battery_voltage_v = adapter.last_tel.batt_voltage_v or adapter.last_tel.extra.get("battery_voltage_v")
            # Default to 52V if not available (typical for 48V battery system)
            if not battery_voltage_v:
                battery_voltage_v = 52.0
            
            # For Powdrive, only read current-based registers (power registers don't exist)
            # For Senergy, read power registers directly
            if adapter_type == "powdrive":
                charging_registers = [
                    "battery_max_discharge_current_a", "battery_max_charge_current_a",
                    "grid_charge_battery_current_a", "generator_charge_enabled",
                    "battery_floating_voltage_v", "battery_absorption_voltage_v", "battery_equalization_voltage_v"
                ]
            else:
                charging_registers = [
                    "battery_max_discharge_current_a", "battery_max_charge_current_a",
                    "grid_charge_battery_current_a", "generator_charge_enabled",
                    "battery_floating_voltage_v", "battery_absorption_voltage_v", "battery_equalization_voltage_v",
                    "maximum_grid_charger_power", "max_grid_charge_power", "max_charge_power", "max_discharge_power",
                    "maximum_charger_power", "maximum_discharger_power"
                ]
            settings = await _read_settings_registers(adapter, charging_registers)
            
            # Read current values
            max_discharge_current_a = settings.get("battery_max_discharge_current_a")
            max_charge_current_a = settings.get("battery_max_charge_current_a")
            max_grid_charge_current_a = settings.get("grid_charge_battery_current_a")
            
            # For Powdrive: Convert current (A) to power (W) for display
            # For Senergy: Use power values directly if available
            if adapter_type == "powdrive":
                # Convert current to power: Power (W) = Current (A) × Voltage (V)
                max_charger_power_w = None
                max_discharger_power_w = None
                max_grid_charger_power_w = None
                
                if max_charge_current_a is not None:
                    max_charger_power_w = int(max_charge_current_a * battery_voltage_v)
                if max_discharge_current_a is not None:
                    max_discharger_power_w = int(max_discharge_current_a * battery_voltage_v)
                if max_grid_charge_current_a is not None:
                    max_grid_charger_power_w = int(max_grid_charge_current_a * battery_voltage_v)
                
                log.debug(f"Powdrive: Converted currents to power at {battery_voltage_v}V - "
                         f"Charge: {max_charge_current_a}A={max_charger_power_w}W, "
                         f"Discharge: {max_discharge_current_a}A={max_discharger_power_w}W, "
                         f"Grid: {max_grid_charge_current_a}A={max_grid_charger_power_w}W")
            else:
                # Senergy: Use power values directly
                max_charger_power_w = settings.get("maximum_charger_power") or settings.get("max_charge_power")
                max_discharger_power_w = settings.get("maximum_discharger_power") or settings.get("max_discharge_power")
                max_grid_charger_power_w = settings.get("maximum_grid_charger_power") or settings.get("max_grid_charge_power")
            
            battery_charging = {
                "max_discharge_current_a": max_discharge_current_a,
                "max_charge_current_a": max_charge_current_a,
                "max_grid_charge_current_a": max_grid_charge_current_a,
                "max_generator_charge_current_a": 0 if not settings.get("generator_charge_enabled") else None,
                "battery_float_charge_voltage_v": settings.get("battery_floating_voltage_v"),
                "battery_absorption_charge_voltage_v": settings.get("battery_absorption_voltage_v"),
                "battery_equalization_charge_voltage_v": settings.get("battery_equalization_voltage_v"),
                "max_grid_charger_power_w": max_grid_charger_power_w,
                "max_charger_power_w": max_charger_power_w,
                "max_discharger_power_w": max_discharger_power_w,
                "_adapter_type": adapter_type,  # Store adapter type for POST endpoint
                "_battery_voltage_v": battery_voltage_v  # Store battery voltage for POST endpoint
            }
            
            solar_app.set_settings_cache(inverter_id, "battery_charging", battery_charging)
            return {"inverter_id": inverter_id, "battery_charging": battery_charging}
        except Exception as e:
            log.error(f"Error getting battery charging: {e}", exc_info=True)
            return {"inverter_id": inverter_id, "battery_charging": None, "error": str(e)}

    @app.post("/api/inverter/battery-charging")
    async def api_update_battery_charging(inverter_id: str, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update battery charging settings."""
        try:
            rt = None
            for inv_rt in solar_app.inverters:
                if inv_rt.cfg.id == inverter_id:
                    rt = inv_rt
                    break
            
            if not rt:
                return {"status": "error", "message": "Inverter not found"}
            
            adapter = rt.adapter
            adapter_type = rt.cfg.adapter.type if hasattr(rt.cfg, 'adapter') else None
            updates = {}
            
            if "max_discharge_current_a" in settings_data:
                updates["battery_max_discharge_current_a"] = settings_data["max_discharge_current_a"]
            if "max_charge_current_a" in settings_data:
                updates["battery_max_charge_current_a"] = settings_data["max_charge_current_a"]
            if "max_grid_charge_current_a" in settings_data:
                updates["grid_charge_battery_current_a"] = settings_data["max_grid_charge_current_a"]
            if "battery_float_charge_voltage_v" in settings_data:
                updates["battery_floating_voltage_v"] = settings_data["battery_float_charge_voltage_v"]
            if "battery_absorption_charge_voltage_v" in settings_data:
                updates["battery_absorption_voltage_v"] = settings_data["battery_absorption_charge_voltage_v"]
            if "battery_equalization_charge_voltage_v" in settings_data:
                updates["battery_equalization_voltage_v"] = settings_data["battery_equalization_charge_voltage_v"]
            
            # Handle power settings - convert to current for Powdrive, use power directly for Senergy
            # Get battery voltage for power-to-current conversion (Powdrive)
            battery_voltage_v = None
            if hasattr(adapter, 'last_tel') and adapter.last_tel:
                battery_voltage_v = adapter.last_tel.batt_voltage_v or adapter.last_tel.extra.get("battery_voltage_v")
            if not battery_voltage_v:
                battery_voltage_v = 52.0  # Default to 52V
            
            if adapter_type == "powdrive":
                # Powdrive: Convert power (W) to current (A) for saving
                # Current (A) = Power (W) / Voltage (V)
                if "max_grid_charger_power_w" in settings_data:
                    power_w = settings_data["max_grid_charger_power_w"]
                    if power_w is not None and battery_voltage_v > 0:
                        # Convert to float in case it comes as string from frontend
                        power_w = float(power_w)
                        current_a = int(round(power_w / battery_voltage_v))
                        updates["grid_charge_battery_current_a"] = current_a
                        log.info(f"Powdrive: Converted max_grid_charger_power {power_w}W to {current_a}A (at {battery_voltage_v}V)")
                
                if "max_charger_power_w" in settings_data:
                    power_w = settings_data["max_charger_power_w"]
                    if power_w is not None and battery_voltage_v > 0:
                        # Convert to float in case it comes as string from frontend
                        power_w = float(power_w)
                        current_a = int(round(power_w / battery_voltage_v))
                        updates["battery_max_charge_current_a"] = current_a
                        log.info(f"Powdrive: Converted max_charger_power {power_w}W to {current_a}A (at {battery_voltage_v}V)")
                
                if "max_discharger_power_w" in settings_data:
                    power_w = settings_data["max_discharger_power_w"]
                    if power_w is not None and battery_voltage_v > 0:
                        # Convert to float in case it comes as string from frontend
                        power_w = float(power_w)
                        current_a = int(round(power_w / battery_voltage_v))
                        updates["battery_max_discharge_current_a"] = current_a
                        log.info(f"Powdrive: Converted max_discharger_power {power_w}W to {current_a}A (at {battery_voltage_v}V)")
            else:
                # Senergy: Use power values directly (convert to int in case they come as strings)
                if "max_grid_charger_power_w" in settings_data:
                    power_w = settings_data["max_grid_charger_power_w"]
                    updates["maximum_grid_charger_power"] = int(float(power_w)) if power_w is not None else None
                if "max_charger_power_w" in settings_data:
                    power_w = settings_data["max_charger_power_w"]
                    updates["maximum_charger_power"] = int(float(power_w)) if power_w is not None else None
                if "max_discharger_power_w" in settings_data:
                    power_w = settings_data["max_discharger_power_w"]
                    updates["maximum_discharger_power"] = int(float(power_w)) if power_w is not None else None
            
            verified = await _write_and_verify_registers(adapter, updates)
            
            cached = solar_app.get_settings_cache(inverter_id, "battery_charging") or {}
            
            # Re-read battery voltage for conversion (may have changed)
            updated_battery_voltage_v = battery_voltage_v
            if hasattr(adapter, 'last_tel') and adapter.last_tel:
                updated_battery_voltage_v = adapter.last_tel.batt_voltage_v or adapter.last_tel.extra.get("battery_voltage_v") or battery_voltage_v
            
            # Convert verified current values back to power for Powdrive
            verified_max_charge_current = verified.get("battery_max_charge_current_a")
            verified_max_discharge_current = verified.get("battery_max_discharge_current_a")
            verified_max_grid_charge_current = verified.get("grid_charge_battery_current_a")
            
            if adapter_type == "powdrive":
                # Convert current back to power for cache
                max_charger_power_w = int(verified_max_charge_current * updated_battery_voltage_v) if verified_max_charge_current else None
                max_discharger_power_w = int(verified_max_discharge_current * updated_battery_voltage_v) if verified_max_discharge_current else None
                max_grid_charger_power_w = int(verified_max_grid_charge_current * updated_battery_voltage_v) if verified_max_grid_charge_current else None
            else:
                # Senergy: Use power values directly
                max_charger_power_w = verified.get("maximum_charger_power") or verified.get("max_charge_power")
                max_discharger_power_w = verified.get("maximum_discharger_power") or verified.get("max_discharge_power")
                max_grid_charger_power_w = verified.get("maximum_grid_charger_power") or verified.get("max_grid_charge_power")
            
            cached.update({
                "max_discharge_current_a": verified_max_discharge_current,
                "max_charge_current_a": verified_max_charge_current,
                "max_grid_charge_current_a": verified_max_grid_charge_current,
                "battery_float_charge_voltage_v": verified.get("battery_floating_voltage_v"),
                "battery_absorption_charge_voltage_v": verified.get("battery_absorption_voltage_v"),
                "battery_equalization_charge_voltage_v": verified.get("battery_equalization_voltage_v"),
                "max_grid_charger_power_w": max_grid_charger_power_w,
                "max_charger_power_w": max_charger_power_w,
                "max_discharger_power_w": max_discharger_power_w
            })
            solar_app.set_settings_cache(inverter_id, "battery_charging", cached)
            
            if solar_app.logger:
                for reg_id, value in verified.items():
                    solar_app.logger.set_config(f"inverter.{inverter_id}.{reg_id}", str(value), "api")
            
            return {"status": "success", "inverter_id": inverter_id, "battery_charging": cached}
        except Exception as e:
            log.error(f"Error updating battery charging: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    @app.get("/api/inverter/work-mode")
    async def api_get_work_mode(inverter_id: str = "senergy1") -> Dict[str, Any]:
        """Get work mode settings."""
        try:
            cached = solar_app.get_settings_cache(inverter_id, "work_mode")
            if cached is not None:
                return {"inverter_id": inverter_id, "work_mode": cached}
            
            rt = None
            for inv_rt in solar_app.inverters:
                if inv_rt.cfg.id == inverter_id:
                    rt = inv_rt
                    break
            
            if not rt:
                return {"inverter_id": inverter_id, "work_mode": None, "error": "Inverter not found"}
            
            adapter = rt.adapter
            # Filter registers based on adapter type - some registers don't exist for Powdrive
            adapter_type = rt.cfg.adapter.type if hasattr(rt.cfg, 'adapter') else None
            if adapter_type == "powdrive":
                # Powdrive uses different register IDs
                work_mode_registers = [
                    "ac_charge_battery", "generator_charge_enabled",  # ac_charge_battery is Powdrive's grid charge equivalent
                    "battery_shutdown_capacity_pct", "battery_restart_capacity_pct",
                    "battery_low_capacity_pct", "grid_charging_start_voltage_v",
                    "grid_charging_start_capacity_pct",  # Grid charging start capacity
                    "control_board_special_function_2"  # For off-grid mode (bits 2-3)
                ]
            else:
                # Senergy registers
                work_mode_registers = [
                    "hybrid_work_mode", "grid_charge", "generator_charge_enabled",
                    "battery_shutdown_capacity_pct", "battery_restart_capacity_pct",
                    "battery_low_capacity_pct", "grid_charging_start_voltage_v",
                    "off_grid_mode", "off_grid_start_up_battery_capacity"
                ]
            settings = await _read_settings_registers(adapter, work_mode_registers)
            
            # Map Powdrive's ac_charge_battery to grid_charge for consistency
            # ac_charge_battery: 0=Enabled, 1=Disabled (inverted logic)
            # grid_charge: True=Enabled, False=Disabled
            if adapter_type == "powdrive":
                ac_charge_battery = settings.get("ac_charge_battery")
                grid_charge = (ac_charge_battery == 0) if ac_charge_battery is not None else None
            else:
                grid_charge = bool(settings.get("grid_charge", 0))
            
            # Extract off-grid mode from control_board_special_function_2 for Powdrive
            off_grid_mode = None
            off_grid_start_up_battery_capacity_pct = None
            if adapter_type == "powdrive":
                # Powdrive: Extract off-grid mode from control_board_special_function_2 (bits 2-3)
                # Bit2-3: 10=Force off-grid work disable, 11=Force off-grid work enable
                control_func_2 = settings.get("control_board_special_function_2")
                if control_func_2 is not None:
                    off_grid_bits = (control_func_2 >> 2) & 0b11  # Get bits 2-3
                    off_grid_mode = (off_grid_bits == 0b11)  # 11 = enabled
                # For Powdrive, use battery_restart_capacity_pct as off-grid startup capacity
                # (this is the capacity at which the battery restarts, which is similar to off-grid startup)
                off_grid_start_up_battery_capacity_pct = settings.get("battery_restart_capacity_pct")
            else:
                # Senergy: Use dedicated registers
                off_grid_mode = bool(settings.get("off_grid_mode", 0))
                off_grid_start_up_battery_capacity_pct = settings.get("off_grid_start_up_battery_capacity")
            
            work_mode = {
                "remote_switch": "On",  # May need register mapping
                "grid_charge": grid_charge,
                "generator_charge": bool(settings.get("generator_charge_enabled", 0)),
                "force_generator_on": False,  # May need register mapping
                "output_shutdown_capacity_pct": settings.get("battery_shutdown_capacity_pct"),
                "stop_battery_discharge_capacity_pct": settings.get("battery_low_capacity_pct"),
                "start_battery_discharge_capacity_pct": settings.get("battery_restart_capacity_pct"),
                "start_grid_charge_capacity_pct": settings.get("grid_charging_start_capacity_pct"),  # Grid charging start capacity
                "off_grid_mode": off_grid_mode,
                "off_grid_start_up_battery_capacity_pct": off_grid_start_up_battery_capacity_pct
            }
            
            solar_app.set_settings_cache(inverter_id, "work_mode", work_mode)
            return {"inverter_id": inverter_id, "work_mode": work_mode}
        except Exception as e:
            log.error(f"Error getting work mode: {e}", exc_info=True)
            return {"inverter_id": inverter_id, "work_mode": None, "error": str(e)}

    @app.post("/api/inverter/work-mode")
    async def api_update_work_mode(inverter_id: str, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update work mode settings."""
        try:
            rt = None
            for inv_rt in solar_app.inverters:
                if inv_rt.cfg.id == inverter_id:
                    rt = inv_rt
                    break
            
            if not rt:
                return {"status": "error", "message": "Inverter not found"}
            
            adapter = rt.adapter
            updates = {}
            
            # Handle grid_charge - map to correct register based on adapter type
            adapter_type = rt.cfg.adapter.type if hasattr(rt.cfg, 'adapter') else None
            if "grid_charge" in settings_data:
                if adapter_type == "powdrive":
                    # Powdrive: ac_charge_battery (0=Enabled, 1=Disabled) - inverted logic
                    # grid_charge True = Enabled = 0, grid_charge False = Disabled = 1
                    updates["ac_charge_battery"] = 0 if settings_data["grid_charge"] else 1
                else:
                    # Senergy: grid_charge (0=Disabled, 1=Enabled)
                    updates["grid_charge"] = 1 if settings_data["grid_charge"] else 0
            if "generator_charge" in settings_data:
                updates["generator_charge_enabled"] = 1 if settings_data["generator_charge"] else 0
            if "output_shutdown_capacity_pct" in settings_data:
                updates["battery_shutdown_capacity_pct"] = settings_data["output_shutdown_capacity_pct"]
            if "stop_battery_discharge_capacity_pct" in settings_data:
                updates["battery_low_capacity_pct"] = settings_data["stop_battery_discharge_capacity_pct"]
            if "start_battery_discharge_capacity_pct" in settings_data:
                updates["battery_restart_capacity_pct"] = settings_data["start_battery_discharge_capacity_pct"]
            # Handle off-grid mode - map to correct register based on adapter type
            if "off_grid_mode" in settings_data:
                if adapter_type == "powdrive":
                    # Powdrive: Update control_board_special_function_2 bits 2-3
                    # Read current value first
                    try:
                        current_func_2 = await adapter.read_by_ident("control_board_special_function_2")
                        # Clear bits 2-3 and set new value
                        # 10 = disable, 11 = enable
                        new_bits = 0b11 if settings_data["off_grid_mode"] else 0b10
                        current_func_2 = (current_func_2 & ~0b1100) | (new_bits << 2)  # Clear bits 2-3, set new value
                        updates["control_board_special_function_2"] = current_func_2
                    except Exception as e:
                        log.warning(f"Failed to read control_board_special_function_2 for off-grid mode update: {e}")
                else:
                    # Senergy: Use dedicated register
                    updates["off_grid_mode"] = 1 if settings_data["off_grid_mode"] else 0
            if "off_grid_start_up_battery_capacity_pct" in settings_data:
                if adapter_type == "powdrive":
                    # Powdrive: Use battery_restart_capacity_pct as off-grid startup capacity
                    updates["battery_restart_capacity_pct"] = settings_data["off_grid_start_up_battery_capacity_pct"]
                else:
                    # Senergy: Use dedicated register
                    updates["off_grid_start_up_battery_capacity"] = settings_data["off_grid_start_up_battery_capacity_pct"]
            
            verified = await _write_and_verify_registers(adapter, updates)
            
            cached = solar_app.get_settings_cache(inverter_id, "work_mode") or {}
            # Update cache with verified values, handling adapter-specific mappings
            if adapter_type == "powdrive":
                # For Powdrive, extract off-grid mode from control_board_special_function_2
                control_func_2 = verified.get("control_board_special_function_2")
                off_grid_mode = None
                if control_func_2 is not None:
                    off_grid_bits = (control_func_2 >> 2) & 0b11
                    off_grid_mode = (off_grid_bits == 0b11)
                cached.update({
                    "grid_charge": (verified.get("ac_charge_battery", 1) == 0),  # Inverted logic
                    "generator_charge": bool(verified.get("generator_charge_enabled", 0)),
                    "output_shutdown_capacity_pct": verified.get("battery_shutdown_capacity_pct"),
                    "stop_battery_discharge_capacity_pct": verified.get("battery_low_capacity_pct"),
                    "start_battery_discharge_capacity_pct": verified.get("battery_restart_capacity_pct"),
                    "off_grid_mode": off_grid_mode,
                    "off_grid_start_up_battery_capacity_pct": verified.get("battery_restart_capacity_pct")
                })
            else:
                # Senergy: Use direct register values
                cached.update({
                    "grid_charge": bool(verified.get("grid_charge", 0)),
                    "generator_charge": bool(verified.get("generator_charge_enabled", 0)),
                    "output_shutdown_capacity_pct": verified.get("battery_shutdown_capacity_pct"),
                    "stop_battery_discharge_capacity_pct": verified.get("battery_low_capacity_pct"),
                    "start_battery_discharge_capacity_pct": verified.get("battery_restart_capacity_pct"),
                    "off_grid_mode": bool(verified.get("off_grid_mode", 0)),
                    "off_grid_start_up_battery_capacity_pct": verified.get("off_grid_start_up_battery_capacity")
                })
            solar_app.set_settings_cache(inverter_id, "work_mode", cached)
            
            if solar_app.logger:
                for reg_id, value in verified.items():
                    solar_app.logger.set_config(f"inverter.{inverter_id}.{reg_id}", str(value), "api")
            
            return {"status": "success", "inverter_id": inverter_id, "work_mode": cached}
        except Exception as e:
            log.error(f"Error updating work mode: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    @app.get("/api/inverter/work-mode-detail")
    async def api_get_work_mode_detail(inverter_id: str = "senergy1") -> Dict[str, Any]:
        """Get work mode detail settings."""
        try:
            cached = solar_app.get_settings_cache(inverter_id, "work_mode_detail")
            if cached is not None:
                return {"inverter_id": inverter_id, "work_mode_detail": cached}
            
            rt = None
            for inv_rt in solar_app.inverters:
                if inv_rt.cfg.id == inverter_id:
                    rt = inv_rt
                    break
            
            if not rt:
                return {"inverter_id": inverter_id, "work_mode_detail": None, "error": "Inverter not found"}
            
            adapter = rt.adapter
            adapter_type = rt.cfg.adapter.type if hasattr(rt.cfg, 'adapter') else None
            
            # Read work mode detail registers
            work_mode_detail = {
                "work_mode": None,
                "solar_export_when_battery_full": None,
                "energy_pattern": None,
                "max_sell_power_kw": None,
                "max_solar_power_kw": None,
                "grid_trickle_feed_w": None,
                "max_export_power_w": None
            }
            
            # Read registers based on adapter type
            if adapter_type == "powdrive":
                # Powdrive-specific registers
                work_mode_detail_registers = [
                    "working_mode_raw",  # For work_mode (read-only, converted to string)
                    "limit_control_function",  # For work_mode (actual setting)
                    "solar_sell",  # For solar_export_when_battery_full
                    "energy_management_mode",  # For energy_pattern (bitmask)
                    "solar_priority",  # For energy_pattern (simpler enum: 0=Battery first, 1=Load first)
                    "max_solar_sell_power_w",  # For max_sell_power_kw
                    "max_export_power_w",  # For max_export_power_w
                    "zero_export_power_w"  # For grid_trickle_feed_w
                ]
            else:
                # Senergy-specific registers
                work_mode_detail_registers = [
                    "hybrid_work_mode",  # For work_mode
                    "max_export_power_w"  # For max_export_power_w
                ]
            
            # Read all registers
            try:
                settings = await _read_settings_registers(adapter, work_mode_detail_registers)
                
                if adapter_type == "powdrive":
                    # Map Powdrive registers to frontend fields
                    # Work mode: Use limit_control_function (0=Selling first, 1=Zero export to load, 2=Zero export to CT)
                    limit_control = settings.get("limit_control_function")
                    if limit_control is not None:
                        limit_map = {0: "Selling first", 1: "Zero export to load", 2: "Zero export to CT"}
                        work_mode_detail["work_mode"] = limit_map.get(limit_control, f"Unknown({limit_control})")
                    
                    # Solar export when battery full: Use solar_sell (0=disabled, 1=enabled)
                    solar_sell = settings.get("solar_sell")
                    if solar_sell is not None:
                        work_mode_detail["solar_export_when_battery_full"] = bool(solar_sell)
                    
                    # Energy pattern: Use energy_management_mode bits 0-1
                    # According to spec: Bit0-1: 10=Battery first, 11=Load first
                    # But we can also check solar_priority register (141) which is simpler
                    # solar_priority: 0=Battery first, 1=Load first
                    energy_mode = settings.get("energy_management_mode")
                    solar_priority = settings.get("solar_priority")
                    if solar_priority is not None:
                        # solar_priority is simpler: 0=Battery first, 1=Load first
                        work_mode_detail["energy_pattern"] = "Battery first" if solar_priority == 0 else "Load first"
                    elif energy_mode is not None:
                        # Fallback to energy_management_mode bits 0-1
                        energy_bits = energy_mode & 0b11  # Get bits 0-1
                        if energy_bits == 0b10:  # 2 in decimal (binary 10)
                            work_mode_detail["energy_pattern"] = "Battery first"
                        elif energy_bits == 0b11:  # 3 in decimal (binary 11)
                            work_mode_detail["energy_pattern"] = "Load first"
                        elif energy_bits == 0b00:  # 0 in decimal (binary 00)
                            work_mode_detail["energy_pattern"] = "Battery first"  # Default
                        elif energy_bits == 0b01:  # 1 in decimal (binary 01)
                            work_mode_detail["energy_pattern"] = "Load first"  # Default
                    
                    # Max sell power: Use max_solar_sell_power_w (convert W to kW)
                    max_solar_sell = settings.get("max_solar_sell_power_w")
                    if max_solar_sell is not None:
                        work_mode_detail["max_sell_power_kw"] = round(max_solar_sell / 1000.0, 2) if max_solar_sell else None
                        work_mode_detail["max_solar_power_kw"] = round(max_solar_sell / 1000.0, 2) if max_solar_sell else None
                    
                    # Max export power
                    max_export = settings.get("max_export_power_w")
                    if max_export is not None:
                        work_mode_detail["max_export_power_w"] = int(max_export) if max_export else None
                    
                    # Grid trickle feed: Use zero_export_power_w (register 104)
                    # This is the small amount of power that can be exported even in zero export mode
                    zero_export = settings.get("zero_export_power_w")
                    if zero_export is not None:
                        work_mode_detail["grid_trickle_feed_w"] = int(zero_export) if zero_export else None
                else:
                    # Senergy mapping
                    work_mode_detail["work_mode"] = settings.get("hybrid_work_mode")
                    max_export = settings.get("max_export_power_w")
                    if max_export is not None:
                        work_mode_detail["max_export_power_w"] = int(max_export) if max_export else None
            except Exception as e:
                log.warning(f"Failed to read work mode detail registers: {e}", exc_info=True)
            
            solar_app.set_settings_cache(inverter_id, "work_mode_detail", work_mode_detail)
            return {"inverter_id": inverter_id, "work_mode_detail": work_mode_detail}
        except Exception as e:
            log.error(f"Error getting work mode detail: {e}", exc_info=True)
            return {"inverter_id": inverter_id, "work_mode_detail": None, "error": str(e)}

    @app.get("/api/inverter/auxiliary-settings")
    async def api_get_auxiliary_settings(inverter_id: str = "senergy1") -> Dict[str, Any]:
        """Get auxiliary/generator settings."""
        try:
            cached = solar_app.get_settings_cache(inverter_id, "auxiliary")
            if cached is not None:
                return {"inverter_id": inverter_id, "auxiliary": cached}
            
            rt = None
            for inv_rt in solar_app.inverters:
                if inv_rt.cfg.id == inverter_id:
                    rt = inv_rt
                    break
            
            if not rt:
                return {"inverter_id": inverter_id, "auxiliary": None, "error": "Inverter not found"}
            
            adapter = rt.adapter
            # Filter registers based on adapter type - some registers don't exist for Powdrive
            adapter_type = rt.cfg.adapter.type if hasattr(rt.cfg, 'adapter') else None
            if adapter_type == "powdrive":
                # Powdrive-specific registers
                auxiliary_registers = [
                    "generator_port_usage", "generator_charge_enabled",
                    "generator_max_run_time_h", "generator_down_time_h",
                    "gen_peak_shaving_power_w",  # Powdrive uses gen_peak_shaving_power_w (not generator_peak_shaving_power_w)
                    "generator_charging_start_capacity_pct",  # Powdrive uses generator_charging_start_capacity_pct (not generator_start_capacity_pct)
                    "control_board_special_function_1",  # For generator peak shaving enable (bits 2-3)
                    "generator_connected_to_grid_input"  # Register 189: Generator connected to grid input
                ]
            else:
                # Senergy registers
                auxiliary_registers = [
                    "generator_port_usage", "generator_charge_enabled",
                    "generator_max_run_time_h", "generator_down_time_h",
                    "generator_peak_shaving_enabled", "generator_peak_shaving_power_w",
                    "generator_stop_capacity_pct", "generator_start_capacity_pct"
                ]
            settings = await _read_settings_registers(adapter, auxiliary_registers)
            
            # Map registers to frontend fields based on adapter type
            if adapter_type == "powdrive":
                # Powdrive: Extract generator peak shaving enable from control_board_special_function_1 (bits 2-3)
                # Bit2-3: 10=Gen peak-shaving disable, 11=Gen peak-shaving enable
                control_func = settings.get("control_board_special_function_1")
                gen_peak_shaving_enabled = None
                if control_func is not None:
                    gen_bits = (control_func >> 2) & 0b11  # Get bits 2-3
                    gen_peak_shaving_enabled = (gen_bits == 0b11)  # 11 = enabled
                
                # Map generator_charging_start_capacity_pct to generator_start_capacity_pct
                generator_start_capacity = settings.get("generator_charging_start_capacity_pct")
                
                auxiliary = {
                    "auxiliary_port": "Generator input" if settings.get("generator_port_usage") == 0 else None,
                    "generator_connected_to_grid_input": bool(settings.get("generator_connected_to_grid_input", 0)) if settings.get("generator_connected_to_grid_input") is not None else False,
                    "generator_peak_shaving": gen_peak_shaving_enabled,
                    "generator_peak_shaving_power_kw": round(settings.get("gen_peak_shaving_power_w", 0) / 1000.0, 2) if settings.get("gen_peak_shaving_power_w") is not None else None,
                    "generator_stop_capacity_pct": None,  # Powdrive doesn't have this register
                    "generator_start_capacity_pct": generator_start_capacity,
                    "generator_max_run_time_h": settings.get("generator_max_run_time_h"),
                    "generator_down_time_h": settings.get("generator_down_time_h")
                }
            else:
                # Senergy mapping
                auxiliary = {
                    "auxiliary_port": "Generator input" if settings.get("generator_port_usage") == 0 else None,
                    "generator_connected_to_grid_input": False,  # May need register mapping
                    "generator_peak_shaving": bool(settings.get("generator_peak_shaving_enabled", 0)),
                    "generator_peak_shaving_power_kw": round(settings.get("generator_peak_shaving_power_w", 0) / 1000.0, 2) if settings.get("generator_peak_shaving_power_w") else None,
                    "generator_stop_capacity_pct": settings.get("generator_stop_capacity_pct"),
                    "generator_start_capacity_pct": settings.get("generator_start_capacity_pct"),
                    "generator_max_run_time_h": settings.get("generator_max_run_time_h"),
                    "generator_down_time_h": settings.get("generator_down_time_h")
                }
            
            solar_app.set_settings_cache(inverter_id, "auxiliary", auxiliary)
            return {"inverter_id": inverter_id, "auxiliary": auxiliary}
        except Exception as e:
            log.error(f"Error getting auxiliary settings: {e}", exc_info=True)
            return {"inverter_id": inverter_id, "auxiliary": None, "error": str(e)}

    @app.post("/api/inverter/auxiliary-settings")
    async def api_update_auxiliary_settings(inverter_id: str, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update auxiliary/generator settings."""
        try:
            rt = None
            for inv_rt in solar_app.inverters:
                if inv_rt.cfg.id == inverter_id:
                    rt = inv_rt
                    break
            
            if not rt:
                return {"status": "error", "message": "Inverter not found"}
            
            adapter = rt.adapter
            adapter_type = rt.cfg.adapter.type if hasattr(rt.cfg, 'adapter') else None
            updates = {}
            
            if adapter_type == "powdrive":
                # Powdrive-specific mappings
                # Generator peak shaving: Update control_board_special_function_1 bits 2-3
                if "generator_peak_shaving" in settings_data:
                    try:
                        current_control_func = await adapter.read_by_ident("control_board_special_function_1")
                        if current_control_func is not None:
                            # Clear bits 2-3 and set new value
                            new_control_func = (current_control_func & 0xFFF3)  # Clear bits 2-3
                            if settings_data["generator_peak_shaving"]:
                                new_control_func |= 0b1100  # Set bits 2-3 to 11 (enabled)
                            else:
                                new_control_func |= 0b1000  # Set bits 2-3 to 10 (disabled)
                            updates["control_board_special_function_1"] = new_control_func
                    except Exception as e:
                        log.warning(f"Failed to read control_board_special_function_1 for update: {e}")
                
                # Generator peak shaving power: Use gen_peak_shaving_power_w (Powdrive register name)
                if "generator_peak_shaving_power_kw" in settings_data:
                    updates["gen_peak_shaving_power_w"] = int(settings_data["generator_peak_shaving_power_kw"] * 1000)
                
                # Generator start capacity: Use generator_charging_start_capacity_pct
                if "generator_start_capacity_pct" in settings_data:
                    updates["generator_charging_start_capacity_pct"] = settings_data["generator_start_capacity_pct"]
            else:
                # Senergy mappings
                if "generator_peak_shaving" in settings_data:
                    updates["generator_peak_shaving_enabled"] = 1 if settings_data["generator_peak_shaving"] else 0
                if "generator_peak_shaving_power_kw" in settings_data:
                    updates["generator_peak_shaving_power_w"] = int(settings_data["generator_peak_shaving_power_kw"] * 1000)
                if "generator_stop_capacity_pct" in settings_data:
                    updates["generator_stop_capacity_pct"] = settings_data["generator_stop_capacity_pct"]
                if "generator_start_capacity_pct" in settings_data:
                    updates["generator_start_capacity_pct"] = settings_data["generator_start_capacity_pct"]
            
            # Common registers for both adapters
            if "generator_max_run_time_h" in settings_data:
                updates["generator_max_run_time_h"] = settings_data["generator_max_run_time_h"]
            if "generator_down_time_h" in settings_data:
                updates["generator_down_time_h"] = settings_data["generator_down_time_h"]
            
            verified = await _write_and_verify_registers(adapter, updates)
            
            # Re-read all auxiliary registers to get updated values
            if adapter_type == "powdrive":
                auxiliary_registers = [
                    "generator_port_usage", "generator_charge_enabled",
                    "generator_max_run_time_h", "generator_down_time_h",
                    "gen_peak_shaving_power_w",
                    "generator_charging_start_capacity_pct",
                    "control_board_special_function_1"
                ]
            else:
                auxiliary_registers = [
                    "generator_port_usage", "generator_charge_enabled",
                    "generator_max_run_time_h", "generator_down_time_h",
                    "generator_peak_shaving_enabled", "generator_peak_shaving_power_w",
                    "generator_stop_capacity_pct", "generator_start_capacity_pct"
                ]
            
            try:
                updated_settings = await _read_settings_registers(adapter, auxiliary_registers)
                
                cached = solar_app.get_settings_cache(inverter_id, "auxiliary") or {}
                
                if adapter_type == "powdrive":
                    # Extract generator peak shaving enable from control_board_special_function_1
                    control_func = updated_settings.get("control_board_special_function_1")
                    gen_peak_shaving_enabled = None
                    if control_func is not None:
                        gen_bits = (control_func >> 2) & 0b11
                        gen_peak_shaving_enabled = (gen_bits == 0b11)
                    
                    cached.update({
                        "generator_peak_shaving": gen_peak_shaving_enabled,
                        "generator_peak_shaving_power_kw": round(updated_settings.get("gen_peak_shaving_power_w", 0) / 1000.0, 2) if updated_settings.get("gen_peak_shaving_power_w") is not None else None,
                        "generator_stop_capacity_pct": None,  # Powdrive doesn't have this
                        "generator_start_capacity_pct": updated_settings.get("generator_charging_start_capacity_pct"),
                        "generator_max_run_time_h": updated_settings.get("generator_max_run_time_h"),
                        "generator_down_time_h": updated_settings.get("generator_down_time_h")
                    })
                else:
                    cached.update({
                        "generator_peak_shaving": bool(updated_settings.get("generator_peak_shaving_enabled", 0)),
                        "generator_peak_shaving_power_kw": round(updated_settings.get("generator_peak_shaving_power_w", 0) / 1000.0, 2) if updated_settings.get("generator_peak_shaving_power_w") else None,
                        "generator_stop_capacity_pct": updated_settings.get("generator_stop_capacity_pct"),
                        "generator_start_capacity_pct": updated_settings.get("generator_start_capacity_pct"),
                        "generator_max_run_time_h": updated_settings.get("generator_max_run_time_h"),
                        "generator_down_time_h": updated_settings.get("generator_down_time_h")
                    })
            except Exception as e:
                log.warning(f"Failed to re-read auxiliary settings after update: {e}")
                # Fallback to verified values
                cached = solar_app.get_settings_cache(inverter_id, "auxiliary") or {}
                if adapter_type == "powdrive":
                    cached.update({
                        "generator_max_run_time_h": verified.get("generator_max_run_time_h"),
                        "generator_down_time_h": verified.get("generator_down_time_h"),
                        "generator_start_capacity_pct": verified.get("generator_charging_start_capacity_pct")
                    })
                else:
                    cached.update({
                        "generator_peak_shaving": bool(verified.get("generator_peak_shaving_enabled", 0)),
                        "generator_peak_shaving_power_kw": round(verified.get("generator_peak_shaving_power_w", 0) / 1000.0, 2) if verified.get("generator_peak_shaving_power_w") else None,
                        "generator_stop_capacity_pct": verified.get("generator_stop_capacity_pct"),
                        "generator_start_capacity_pct": verified.get("generator_start_capacity_pct"),
                        "generator_max_run_time_h": verified.get("generator_max_run_time_h"),
                        "generator_down_time_h": verified.get("generator_down_time_h")
                    })
            solar_app.set_settings_cache(inverter_id, "auxiliary", cached)
            
            if solar_app.logger:
                for reg_id, value in verified.items():
                    solar_app.logger.set_config(f"inverter.{inverter_id}.{reg_id}", str(value), "api")
            
            return {"status": "success", "inverter_id": inverter_id, "auxiliary": cached}
        except Exception as e:
            log.error(f"Error updating auxiliary settings: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    @app.post("/api/inverter/work-mode-detail")
    async def api_update_work_mode_detail(inverter_id: str, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update work mode detail settings."""
        try:
            rt = None
            for inv_rt in solar_app.inverters:
                if inv_rt.cfg.id == inverter_id:
                    rt = inv_rt
                    break
            
            if not rt:
                return {"status": "error", "message": "Inverter not found"}
            
            adapter = rt.adapter
            adapter_type = rt.cfg.adapter.type if hasattr(rt.cfg, 'adapter') else None
            updates = {}
            
            # Map frontend fields to register IDs based on adapter type
            if adapter_type == "powdrive":
                # Powdrive mappings
                # Work mode: Map to limit_control_function
                if "work_mode" in settings_data:
                    work_mode = settings_data["work_mode"]
                    # Map frontend values to Powdrive register values
                    if work_mode == "Zero export to load":
                        updates["limit_control_function"] = 1
                    elif work_mode == "Selling first":
                        updates["limit_control_function"] = 0
                    elif work_mode == "Zero export to CT":
                        updates["limit_control_function"] = 2
                
                # Solar export when battery full: Map to solar_sell
                if "solar_export_when_battery_full" in settings_data:
                    updates["solar_sell"] = 1 if settings_data["solar_export_when_battery_full"] else 0
                
                # Energy pattern: Map to energy_management_mode bits 0-1
                if "energy_pattern" in settings_data:
                    energy_pattern = settings_data["energy_pattern"]
                    # Read current value first to preserve other bits
                    try:
                        current_energy_mode = await adapter.read_by_ident("energy_management_mode")
                        if current_energy_mode is not None:
                            # Clear bits 0-1 and set new value
                            new_energy_mode = (current_energy_mode & 0xFFFC)  # Clear bits 0-1
                            if energy_pattern == "Battery first":
                                new_energy_mode |= 0b10  # Set to 2
                            elif energy_pattern == "Load first":
                                new_energy_mode |= 0b11  # Set to 3
                            updates["energy_management_mode"] = new_energy_mode
                    except Exception as e:
                        log.warning(f"Failed to read energy_management_mode for update: {e}")
                
                # Max sell power: Map to max_solar_sell_power_w (convert kW to W)
                if "max_sell_power_kw" in settings_data:
                    max_sell_kw = settings_data["max_sell_power_kw"]
                    if max_sell_kw is not None:
                        updates["max_solar_sell_power_w"] = int(max_sell_kw * 1000)
                
                # Max solar power: Also map to max_solar_sell_power_w
                if "max_solar_power_kw" in settings_data:
                    max_solar_kw = settings_data["max_solar_power_kw"]
                    if max_solar_kw is not None:
                        updates["max_solar_sell_power_w"] = int(max_solar_kw * 1000)
                
                # Max export power
                if "max_export_power_w" in settings_data:
                    updates["max_export_power_w"] = settings_data["max_export_power_w"]
            else:
                # Senergy mappings
                if "work_mode" in settings_data:
                    updates["hybrid_work_mode"] = settings_data["work_mode"]
                if "max_export_power_w" in settings_data:
                    updates["max_export_power_w"] = settings_data["max_export_power_w"]
            
            verified = await _write_and_verify_registers(adapter, updates)
            
            # Re-read all work mode detail registers to get updated values
            if adapter_type == "powdrive":
                work_mode_detail_registers = [
                    "limit_control_function",
                    "solar_sell",
                    "energy_management_mode",
                    "max_solar_sell_power_w",
                    "max_export_power_w"
                ]
            else:
                work_mode_detail_registers = [
                    "hybrid_work_mode",
                    "max_export_power_w"
                ]
            
            # Read updated values
            try:
                updated_settings = await _read_settings_registers(adapter, work_mode_detail_registers)
                
                cached = solar_app.get_settings_cache(inverter_id, "work_mode_detail") or {}
                
                if adapter_type == "powdrive":
                    # Map Powdrive registers to frontend fields
                    limit_control = updated_settings.get("limit_control_function")
                    if limit_control is not None:
                        limit_map = {0: "Selling first", 1: "Zero export to load", 2: "Zero export to CT"}
                        cached["work_mode"] = limit_map.get(limit_control, f"Unknown({limit_control})")
                    
                    solar_sell = updated_settings.get("solar_sell")
                    if solar_sell is not None:
                        cached["solar_export_when_battery_full"] = bool(solar_sell)
                    
                    # Energy pattern: Use solar_priority first (simpler), fallback to energy_management_mode
                    solar_priority = updated_settings.get("solar_priority")
                    if solar_priority is not None:
                        cached["energy_pattern"] = "Battery first" if solar_priority == 0 else "Load first"
                    else:
                        energy_mode = updated_settings.get("energy_management_mode")
                        if energy_mode is not None:
                            energy_bits = energy_mode & 0b11
                            if energy_bits == 0b10:  # 2 (binary 10)
                                cached["energy_pattern"] = "Battery first"
                            elif energy_bits == 0b11:  # 3 (binary 11)
                                cached["energy_pattern"] = "Load first"
                            elif energy_bits == 0b00:  # 0 (binary 00)
                                cached["energy_pattern"] = "Battery first"  # Default
                            elif energy_bits == 0b01:  # 1 (binary 01)
                                cached["energy_pattern"] = "Load first"  # Default
                    
                    max_solar_sell = updated_settings.get("max_solar_sell_power_w")
                    if max_solar_sell is not None:
                        cached["max_sell_power_kw"] = round(max_solar_sell / 1000.0, 2) if max_solar_sell else None
                        cached["max_solar_power_kw"] = round(max_solar_sell / 1000.0, 2) if max_solar_sell else None
                    
                    max_export = updated_settings.get("max_export_power_w")
                    if max_export is not None:
                        cached["max_export_power_w"] = int(max_export) if max_export else None
                    
                    # Grid trickle feed: Use zero_export_power_w
                    zero_export = updated_settings.get("zero_export_power_w")
                    if zero_export is not None:
                        cached["grid_trickle_feed_w"] = int(zero_export) if zero_export else None
                else:
                    cached["work_mode"] = updated_settings.get("hybrid_work_mode")
                    max_export = updated_settings.get("max_export_power_w")
                    if max_export is not None:
                        cached["max_export_power_w"] = int(max_export) if max_export else None
            except Exception as e:
                log.warning(f"Failed to re-read work mode detail after update: {e}")
                # Fallback to verified values
                cached = solar_app.get_settings_cache(inverter_id, "work_mode_detail") or {}
                cached.update({
                    "max_export_power_w": verified.get("max_export_power_w")
                })
            solar_app.set_settings_cache(inverter_id, "work_mode_detail", cached)
            
            if solar_app.logger:
                for reg_id, value in verified.items():
                    solar_app.logger.set_config(f"inverter.{inverter_id}.{reg_id}", str(value), "api")
            
            return {"status": "success", "inverter_id": inverter_id, "work_mode_detail": cached}
        except Exception as e:
            log.error(f"Error updating work mode detail: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    return app


def start_api_in_background(fastapi_app: FastAPI, host: str, port: int) -> None:
    """Start a uvicorn server in a background daemon thread."""
    try:
        # Configure uvicorn to use the main application's logger
        import logging
        uvicorn_logger = logging.getLogger("uvicorn")
        uvicorn_logger.setLevel(logging.INFO)
        
        # Add a handler to capture uvicorn logs in the main application
        if not uvicorn_logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            uvicorn_logger.addHandler(handler)
        
        config = uvicorn.Config(
            fastapi_app, 
            host=host, 
            port=port, 
            log_level="info",
            access_log=True,
            use_colors=False,
            log_config=None  # Disable uvicorn's default logging config
        )
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        log.info(f"API server thread started on {host}:{port}")
    except Exception as e:
        log.error(f"Error starting API server: {e}", exc_info=True)

