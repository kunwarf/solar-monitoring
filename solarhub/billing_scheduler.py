"""
Billing Daily Scheduler Module

Runs daily at 00:30 local time to:
- Compute daily accruals for current billing month
- Update cycle credit balances
- Write daily snapshot to billing_daily table
- Detect and finalize billing months and cycles
"""

import sqlite3
import logging
import hashlib
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .billing_engine import (
    BillingConfig,
    simulate_billing_year,
    _billing_month_boundaries,
    _aggregate_hourly_for_billing_month,
    _aggregate_meter_hourly_for_billing_month,
)
from .energy_calculator import EnergyCalculator
from .meter_energy_calculator import MeterEnergyCalculator
from .timezone_utils import get_configured_timezone, to_configured, now_configured
from .config import HubConfig
from typing import List, Optional

log = logging.getLogger(__name__)


@dataclass
class DailySnapshot:
    """Daily billing snapshot data."""
    date: date
    billing_month_id: str
    import_off_kwh: float
    export_off_kwh: float
    import_peak_kwh: float
    export_peak_kwh: float
    net_import_off_kwh: float
    net_import_peak_kwh: float
    credits_off_cycle_kwh_balance: float
    credits_peak_cycle_kwh_balance: float
    bill_off_energy_rs: float
    bill_peak_energy_rs: float
    fixed_prorated_rs: float
    expected_cycle_credit_rs: float
    bill_raw_rs_to_date: float
    bill_credit_balance_rs_to_date: float
    bill_final_rs_to_date: float
    surplus_deficit_flag: str


def _compute_config_hash(billing_cfg: BillingConfig) -> str:
    """Compute hash of billing config for auditability."""
    cfg_dict = {
        "anchor_day": billing_cfg.anchor_day,
        "price_offpeak_import": billing_cfg.price_offpeak_import,
        "price_peak_import": billing_cfg.price_peak_import,
        "price_offpeak_settlement": billing_cfg.price_offpeak_settlement,
        "price_peak_settlement": billing_cfg.price_peak_settlement,
        "fixed_charge": billing_cfg.fixed_charge_per_billing_month,
        "peak_windows": [{"start": w.start, "end": w.end} for w in (billing_cfg.peak_windows or [])],
    }
    cfg_json = json.dumps(cfg_dict, sort_keys=True)
    return hashlib.sha256(cfg_json.encode()).hexdigest()[:16]


def _get_current_billing_month(today: date, anchor_day: int, tz) -> Tuple[datetime, datetime, str]:
    """Get current billing month boundaries for a given date."""
    # Find the billing month that contains today
    year = today.year
    months = _billing_month_boundaries(year, anchor_day, tz)
    
    for start, end, label in months:
        start_date = to_configured(start).date()
        end_date = to_configured(end - timedelta(seconds=1)).date()
        if start_date <= today <= end_date:
            return (start, end, label)
    
    # If not found in current year, check previous year's last month
    prev_year_months = _billing_month_boundaries(year - 1, anchor_day, tz)
    if prev_year_months:
        start, end, label = prev_year_months[-1]
        start_date = to_configured(start).date()
        end_date = to_configured(end - timedelta(seconds=1)).date()
        if start_date <= today <= end_date:
            return (start, end, label)
    
    # Fallback: use first month of current year
    return months[0] if months else (tz.localize(datetime(year, 1, anchor_day)), 
                                      tz.localize(datetime(year, 2, anchor_day)), 
                                      f"{year}-01")


def _get_home_meters(hub_cfg: HubConfig, home_id: str) -> List[str]:
    """Get list of meter IDs attached to a home."""
    if not hub_cfg.meters:
        return []
    
    # Meters attached to home have array_id="home"
    return [m.id for m in hub_cfg.meters if m.array_id == "home"]


def _get_home_inverter_ids(hub_cfg: HubConfig, home_id: str) -> List[str]:
    """Get list of inverter IDs belonging to arrays attached to a home."""
    if not hub_cfg.arrays:
        # If no arrays defined, return all inverter IDs
        return [inv.id for inv in hub_cfg.inverters] if hub_cfg.inverters else []
    
    # Get all inverter IDs from all arrays (all arrays are attached to home by default)
    inverter_ids = []
    for array_cfg in hub_cfg.arrays:
        inverter_ids.extend(array_cfg.inverter_ids)
    
    return inverter_ids


def _compute_daily_snapshot(
    db_path: str,
    billing_cfg: BillingConfig,
    target_date: date,
    home_id: str = "home",
    hub_cfg: Optional[HubConfig] = None,
    site_id: str = "default",
) -> Optional[DailySnapshot]:
    """
    Compute daily snapshot for a given date and home.
    
    Args:
        db_path: Path to database
        billing_cfg: Billing configuration
        target_date: Date to compute snapshot for
        home_id: Home ID (default: "home")
        hub_cfg: Hub configuration (required to determine meters and inverters)
        site_id: Site ID (for backward compatibility, defaults to home_id)
    
    Returns None if insufficient data or error.
    """
    tz = get_configured_timezone()
    energy_calc = EnergyCalculator(db_path)
    meter_calc = MeterEnergyCalculator(db_path)
    
    if not hub_cfg:
        log.error("hub_cfg is required for home-level billing")
        return None
    
    # Get home-attached meters and inverters
    home_meter_ids = _get_home_meters(hub_cfg, home_id)
    home_inverter_ids = _get_home_inverter_ids(hub_cfg, home_id)
    
    log.info(f"Computing billing snapshot for home={home_id}, meters={home_meter_ids}, inverters={home_inverter_ids}")
    
    # Get current billing month
    try:
        month_start, month_end, month_label = _get_current_billing_month(target_date, billing_cfg.anchor_day, tz)
    except Exception as e:
        log.error(f"Failed to get billing month for {target_date}: {e}")
        return None
    
    # Aggregate energy for the day (target_date)
    day_start = tz.localize(datetime.combine(target_date, datetime.min.time()))
    day_end = day_start + timedelta(days=1)
    
    # Get cumulative data for billing month up to target_date
    month_start_local = to_configured(month_start)
    target_datetime = tz.localize(datetime.combine(target_date, datetime.max.time()))
    
    # Determine data source: use meters if available, otherwise use inverters
    use_meter_data = len(home_meter_ids) > 0
    
    try:
        if use_meter_data:
            # Use meter data as source of truth for import/export
            log.debug(f"Using meter data for home {home_id} (meters: {home_meter_ids})")
            
            # Determine inverter_id for fallback
            inverter_id_for_fallback = None
            if home_inverter_ids:
                inverter_id_for_fallback = "all" if len(home_inverter_ids) > 1 else home_inverter_ids[0]
            
            # Aggregate meter hourly data for the month (with hour-by-hour fallback)
            month_energy_to_date = _aggregate_meter_hourly_for_billing_month(
                meter_calc=meter_calc,
                meter_ids=home_meter_ids,
                start=month_start_local,
                end=target_datetime + timedelta(seconds=1),
                billing_cfg=billing_cfg,
                energy_calc=energy_calc,  # For fallback
                inverter_id=inverter_id_for_fallback,  # For fallback
            )
            
            # Get inverter data for solar/load (meters don't provide this)
            if home_inverter_ids:
                inverter_energy = _aggregate_hourly_for_billing_month(
                    energy_calc=energy_calc,
                    inverter_id=inverter_id_for_fallback,
                    start=month_start_local,
                    end=target_datetime + timedelta(seconds=1),
                    billing_cfg=billing_cfg,
                )
                
                # Add solar/load from inverters (meters don't provide this)
                month_energy_to_date.solar_kwh = inverter_energy.solar_kwh
                month_energy_to_date.load_kwh = inverter_energy.load_kwh
        else:
            # Use inverter data (aggregate all home inverters)
            log.debug(f"Using inverter data for home {home_id} (inverters: {home_inverter_ids})")
            
            if not home_inverter_ids:
                log.warning(f"No inverters found for home {home_id}")
                return None
            
            inverter_id_param = "all" if len(home_inverter_ids) > 1 else home_inverter_ids[0]
            month_energy_to_date = _aggregate_hourly_for_billing_month(
                energy_calc=energy_calc,
                inverter_id=inverter_id_param,
                start=month_start_local,
                end=target_datetime + timedelta(seconds=1),
                billing_cfg=billing_cfg,
            )
        
        log.info(f"Billing snapshot for home={home_id}, date={target_date}: Month-to-date energy - "
                f"Import Off: {month_energy_to_date.import_off_kwh:.3f} kWh, "
                f"Import Peak: {month_energy_to_date.import_peak_kwh:.3f} kWh, "
                f"Export Off: {month_energy_to_date.export_off_kwh:.3f} kWh, "
                f"Export Peak: {month_energy_to_date.export_peak_kwh:.3f} kWh, "
                f"Solar: {month_energy_to_date.solar_kwh:.3f} kWh, "
                f"Load: {month_energy_to_date.load_kwh:.3f} kWh")
    except Exception as e:
        log.error(f"Failed to aggregate month-to-date energy: {e}", exc_info=True)
        return None
    
    # Compute net imports
    net_import_off = month_energy_to_date.import_off_kwh - month_energy_to_date.export_off_kwh
    net_import_peak = month_energy_to_date.import_peak_kwh - month_energy_to_date.export_peak_kwh
    
    # For cycle credits, we need to simulate the full billing year to get current cycle state
    # This is simplified: we'll compute cycle credits from the month's position in the cycle
    # Cycle 1: months 1-3, Cycle 2: months 4-6, etc.
    month_num = ((target_date.month - 1) // 3) * 3 + 1  # Simplified
    cycle_start_month = ((month_num - 1) // 3) * 3 + 1
    cycle_num = (cycle_start_month - 1) // 3 + 1
    
    # For now, use simplified credit tracking (will be improved with full cycle simulation)
    credits_off = max(0.0, -net_import_off)  # Simplified: excess export becomes credit
    credits_peak = max(0.0, -net_import_peak)
    
    # Apply credits to net imports
    net_import_off_after_credits = max(0.0, net_import_off - credits_off)
    net_import_peak_after_credits = max(0.0, net_import_peak - credits_peak)
    
    # Compute energy charges
    bill_off_energy = net_import_off_after_credits * billing_cfg.price_offpeak_import
    bill_peak_energy = net_import_peak_after_credits * billing_cfg.price_peak_import
    
    # Fixed charge proration
    total_days_in_month = (to_configured(month_end).date() - to_configured(month_start).date()).days
    elapsed_days = (target_date - to_configured(month_start).date()).days + 1
    fixed_prorated = 0.0
    fixed_proration = getattr(billing_cfg, 'fixed_proration', 'none')  # Default to 'none' if not set
    if fixed_proration == "linear_by_day" and total_days_in_month > 0:
        fixed_prorated = billing_cfg.fixed_charge_per_billing_month * (elapsed_days / total_days_in_month)
    elif fixed_proration == "none":
        fixed_prorated = billing_cfg.fixed_charge_per_billing_month  # Full charge even for partial month
    
    # Expected cycle credit (preview)
    expected_cycle_credit = 0.0
    if credits_off > 0:
        expected_cycle_credit += credits_off * billing_cfg.price_offpeak_settlement
    if credits_peak > 0:
        expected_cycle_credit += credits_peak * billing_cfg.price_peak_settlement
    
    # Raw bill to date
    bill_raw = bill_off_energy + bill_peak_energy + fixed_prorated - expected_cycle_credit
    
    # Credit balance (simplified: assume 0 for now, will be tracked from previous months)
    credit_balance = 0.0
    bill_final = max(0.0, bill_raw + credit_balance)
    
    # Surplus/deficit flag
    net_kwh = net_import_off + net_import_peak
    if net_kwh < -0.1:  # More export than import
        flag = "SURPLUS"
    elif net_kwh > 0.1:  # More import than export
        flag = "DEFICIT"
    else:
        flag = "NEUTRAL"
    
    log.info(f"Billing snapshot for {target_date}: "
            f"Net Import Off: {net_import_off:.3f} kWh, Net Import Peak: {net_import_peak:.3f} kWh, "
            f"Bill Off Energy: PKR {bill_off_energy:.2f}, Bill Peak Energy: PKR {bill_peak_energy:.2f}, "
            f"Fixed Prorated: PKR {fixed_prorated:.2f}, Expected Cycle Credit: PKR {expected_cycle_credit:.2f}, "
            f"Bill Raw: PKR {bill_raw:.2f}, Bill Final: PKR {bill_final:.2f}, Flag: {flag}")
    
    return DailySnapshot(
        date=target_date,
        billing_month_id=month_label,
        import_off_kwh=round(month_energy_to_date.import_off_kwh, 3),
        export_off_kwh=round(month_energy_to_date.export_off_kwh, 3),
        import_peak_kwh=round(month_energy_to_date.import_peak_kwh, 3),
        export_peak_kwh=round(month_energy_to_date.export_peak_kwh, 3),
        net_import_off_kwh=round(net_import_off, 3),
        net_import_peak_kwh=round(net_import_peak, 3),
        credits_off_cycle_kwh_balance=round(credits_off, 3),
        credits_peak_cycle_kwh_balance=round(credits_peak, 3),
        bill_off_energy_rs=round(bill_off_energy, 2),
        bill_peak_energy_rs=round(bill_peak_energy, 2),
        fixed_prorated_rs=round(fixed_prorated, 2),
        expected_cycle_credit_rs=round(expected_cycle_credit, 2),
        bill_raw_rs_to_date=round(bill_raw, 2),
        bill_credit_balance_rs_to_date=round(credit_balance, 2),
        bill_final_rs_to_date=round(bill_final, 2),
        surplus_deficit_flag=flag,
    )


def save_daily_snapshot(db_path: str, snapshot: DailySnapshot, home_id: str = "home", site_id: Optional[str] = None) -> bool:
    """Save daily snapshot to billing_daily table (idempotent)."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        # Use home_id as site_id if site_id not provided (for backward compatibility)
        actual_site_id = site_id if site_id else home_id
        
        cur.execute("""
            INSERT OR REPLACE INTO billing_daily (
                site_id, home_id, date, billing_month_id,
                import_off_kwh, export_off_kwh, import_peak_kwh, export_peak_kwh,
                net_import_off_kwh, net_import_peak_kwh,
                credits_off_cycle_kwh_balance, credits_peak_cycle_kwh_balance,
                bill_off_energy_rs, bill_peak_energy_rs, fixed_prorated_rs,
                expected_cycle_credit_rs,
                bill_raw_rs_to_date, bill_credit_balance_rs_to_date, bill_final_rs_to_date,
                surplus_deficit_flag, generated_at_ts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            actual_site_id,
            home_id,
            snapshot.date.isoformat(),
            snapshot.billing_month_id,
            snapshot.import_off_kwh,
            snapshot.export_off_kwh,
            snapshot.import_peak_kwh,
            snapshot.export_peak_kwh,
            snapshot.net_import_off_kwh,
            snapshot.net_import_peak_kwh,
            snapshot.credits_off_cycle_kwh_balance,
            snapshot.credits_peak_cycle_kwh_balance,
            snapshot.bill_off_energy_rs,
            snapshot.bill_peak_energy_rs,
            snapshot.fixed_prorated_rs,
            snapshot.expected_cycle_credit_rs,
            snapshot.bill_raw_rs_to_date,
            snapshot.bill_credit_balance_rs_to_date,
            snapshot.bill_final_rs_to_date,
            snapshot.surplus_deficit_flag,
            datetime.now().isoformat(),
        ))
        
        conn.commit()
        log.info(f"Saved daily snapshot for {snapshot.date}")
        return True
        
    except Exception as e:
        conn.rollback()
        log.error(f"Failed to save daily snapshot: {e}", exc_info=True)
        return False
    finally:
        conn.close()


def finalize_billing_month(
    db_path: str,
    billing_cfg: BillingConfig,
    year: int,
    month_label: str,
    inverter_id: str = "all",
) -> Optional[Dict[str, Any]]:
    """
    Finalize a billing month and save to billing_months table.
    
    Returns the finalized record or None on error.
    """
    # Run full year simulation to get accurate month data
    result = simulate_billing_year(db_path, billing_cfg, year, inverter_id)
    
    # Find the month in results
    month_bill = None
    for m in result.get("months", []):
        if m.get("billing_month") == month_label:
            month_bill = m
            break
    
    if not month_bill:
        log.warning(f"Month {month_label} not found in simulation results")
        return None
    
    # Extract month number from label (e.g., "2025-01" -> 1)
    try:
        month_num = int(month_label.split("-")[1])
    except:
        month_num = 1
    
    config_hash = _compute_config_hash(billing_cfg)
    month_id = f"{year}-{month_label}"
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        energy = month_bill.get("energy", {})
        cur.execute("""
            INSERT OR REPLACE INTO billing_months (
                id, billing_month, year, month_number,
                anchor_start, anchor_end,
                import_off_kwh, export_off_kwh, import_peak_kwh, export_peak_kwh,
                net_import_off_kwh, net_import_peak_kwh,
                solar_kwh, load_kwh,
                fixed_charge_rs, cycle_credit_off_rs, cycle_credit_peak_rs,
                raw_bill_rs, final_bill_rs, credit_balance_after_rs,
                config_hash, finalized_at_ts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            month_id,
            month_label,
            year,
            month_num,
            energy.get("start", ""),
            energy.get("end", ""),
            energy.get("import_off_kwh", 0.0),
            energy.get("export_off_kwh", 0.0),
            energy.get("import_peak_kwh", 0.0),
            energy.get("export_peak_kwh", 0.0),
            month_bill.get("net_import_off_kwh", 0.0),
            month_bill.get("net_import_peak_kwh", 0.0),
            energy.get("solar_kwh", 0.0),
            energy.get("load_kwh", 0.0),
            month_bill.get("fixed_charge", 0.0),
            month_bill.get("cycle_credit_off", 0.0),
            month_bill.get("cycle_credit_peak", 0.0),
            month_bill.get("raw_bill", 0.0),
            month_bill.get("final_bill", 0.0),
            month_bill.get("credit_balance_after", 0.0),
            config_hash,
            datetime.now().isoformat(),
        ))
        
        conn.commit()
        log.info(f"Finalized billing month {month_label}")
        return month_bill
        
    except Exception as e:
        conn.rollback()
        log.error(f"Failed to finalize billing month: {e}", exc_info=True)
        return None
    finally:
        conn.close()


def run_daily_billing_job(
    db_path: str,
    billing_cfg: BillingConfig,
    hub_cfg: HubConfig,
    target_date: Optional[date] = None,
    home_id: Optional[str] = None,
    site_id: str = "default",
) -> bool:
    """
    Main daily billing job entry point.
    
    Runs at 00:30 local time to:
    1. Compute daily snapshot for target_date (or today) for each home
    2. Save to billing_daily
    3. Check if billing month or cycle ended, and finalize if needed
    
    Args:
        db_path: Path to database
        billing_cfg: Billing configuration
        hub_cfg: Hub configuration (required to determine homes, meters, and inverters)
        target_date: Date to compute snapshot for (default: today)
        home_id: Specific home ID to process (default: None = process all homes)
        site_id: Site ID (for backward compatibility)
    """
    if target_date is None:
        target_date = now_configured().date()
    
    # Determine which homes to process
    homes_to_process = []
    if home_id:
        # Process specific home
        homes_to_process = [home_id]
    else:
        # Process all homes
        if hub_cfg.home:
            homes_to_process = [hub_cfg.home.id]
        else:
            # Fallback: use "home" as default
            homes_to_process = ["home"]
    
    log.info(f"Running daily billing job for {target_date}, homes: {homes_to_process}")
    
    success_count = 0
    for home_id_to_process in homes_to_process:
        log.info(f"Processing billing for home: {home_id_to_process}")
        
        # Compute and save daily snapshot
        snapshot = _compute_daily_snapshot(
            db_path, 
            billing_cfg, 
            target_date, 
            home_id=home_id_to_process,
            hub_cfg=hub_cfg,
            site_id=site_id
        )
        if not snapshot:
            log.error(f"Failed to compute daily snapshot for home {home_id_to_process}")
            continue
        
        if not save_daily_snapshot(db_path, snapshot, home_id=home_id_to_process, site_id=site_id):
            log.error(f"Failed to save daily snapshot for home {home_id_to_process}")
            continue
        
        success_count += 1
        
        # Check if we're at the end of a billing month (for this home)
        tz = get_configured_timezone()
        month_start, month_end, month_label = _get_current_billing_month(target_date, billing_cfg.anchor_day, tz)
        month_end_date = to_configured(month_end - timedelta(seconds=1)).date()
        
        if target_date >= month_end_date:
            # Finalize the month (TODO: make this home-aware)
            year = target_date.year
            log.info(f"Finalizing billing month {month_label} for home {home_id_to_process}")
            # Note: finalize_billing_month currently doesn't support home_id, may need update
            # finalize_billing_month(db_path, billing_cfg, year, month_label, home_id=home_id_to_process)
    
    # TODO: Check for cycle end and finalize cycle
    # This requires tracking which cycle we're in and detecting cycle boundaries
    
    log.info(f"Daily billing job completed for {target_date}, processed {success_count}/{len(homes_to_process)} homes")
    return success_count > 0

