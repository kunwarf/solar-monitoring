from __future__ import annotations

"""
Billing and capacity analysis engine.

Implements the core logic described in BillingAndCapacityModuleRequirements.md:
- Billing months based on configurable anchor date
- 3‑month net metering cycles for peak and off‑peak
- Fixed monthly charges
- Monetary credit carry‑forward

Notes / Limitations (v1):
- Battery flows are intentionally ignored.
- Capacity and forecasting calculations are simple approximations and can be
  refined later without changing the public API shape.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, date, timedelta, time as dtime
from typing import List, Dict, Any, Optional, Tuple

from .config import BillingConfig
from .energy_calculator import EnergyCalculator
from .meter_energy_calculator import MeterEnergyCalculator
from .timezone_utils import get_configured_timezone, to_configured
import logging

log = logging.getLogger(__name__)


@dataclass
class BillingMonthEnergy:
    label: str
    start: datetime
    end: datetime
    import_off_kwh: float = 0.0
    import_peak_kwh: float = 0.0
    export_off_kwh: float = 0.0
    export_peak_kwh: float = 0.0
    solar_kwh: float = 0.0
    load_kwh: float = 0.0


@dataclass
class BillingMonthBill:
    billing_month: str
    energy: BillingMonthEnergy
    net_import_off_kwh: float
    net_import_peak_kwh: float
    fixed_charge: float
    cycle_credit_off: float
    cycle_credit_peak: float
    raw_bill: float
    final_bill: float
    credit_balance_after: float


def _parse_hhmm(value: str) -> dtime:
    """Parse HH:MM into datetime.time."""
    hour, minute = value.split(":")
    return dtime(hour=int(hour), minute=int(minute))


def _is_peak_time(time_str: str, billing_cfg: BillingConfig) -> bool:
    """
    Determine if a given time (HH:MM or HH:00) is within any configured peak window.
    Peak windows are interpreted in local configured timezone and assumed not to span midnight.
    """
    if not billing_cfg.peak_windows:
        return False
    # time_str is expected like "13:00"
    parts = time_str.split(":")
    hhmm = dtime(hour=int(parts[0]), minute=int(parts[1] if len(parts) > 1 else 0))
    for win in billing_cfg.peak_windows:
        start = _parse_hhmm(win.start)
        end = _parse_hhmm(win.end)
        if start <= hhmm < end:
            return True
    return False


def _billing_month_boundaries(year: int, anchor_day: int, tz) -> List[Tuple[datetime, datetime, str]]:
    """
    Compute billing month boundaries for a given calendar year.

    Example (anchor_day=15, year=2025):
      Month 1: 2025-01-15 ... 2025-02-14
      ...
      Month 12: 2025-12-15 ... 2026-01-14
    """
    # Start at anchor in given year
    start = tz.localize(datetime(year, 1, anchor_day, 0, 0))
    months: List[Tuple[datetime, datetime, str]] = []
    current_start = start
    for i in range(12):
        # next month anchor
        # naive month increment
        if current_start.month == 12:
            next_start = tz.localize(datetime(current_start.year + 1, 1, anchor_day, 0, 0))
        else:
            next_start = tz.localize(datetime(current_start.year, current_start.month + 1, anchor_day, 0, 0))
        label = current_start.strftime("%Y-%m")
        months.append((current_start, next_start, label))
        current_start = next_start
    return months


def _aggregate_hourly_for_billing_month(
    energy_calc: EnergyCalculator,
    inverter_id: str,
    start: datetime,
    end: datetime,
    billing_cfg: BillingConfig,
) -> BillingMonthEnergy:
    """
    Aggregate hourly_energy rows into billing-month level energy metrics, split into peak/off-peak.
    """
    # energy_calculator works with dates; use inclusive date range from start.date() to (end - 1s).date()
    start_local = to_configured(start)
    end_local = to_configured(end - timedelta(seconds=1))
    start_date = start_local.date()
    end_date = end_local.date()

    data = energy_calc.get_hourly_energy_data(inverter_id, start_local, end_local)
    
    log.debug(f"_aggregate_hourly_for_billing_month: inverter_id={inverter_id}, "
              f"start={start_local}, end={end_local}, rows_returned={len(data)}")

    energy = BillingMonthEnergy(
        label=f"{start_local.strftime('%Y-%m-%d')}:{end_local.strftime('%Y-%m-%d')}",
        start=start_local,
        end=end_local,
    )

    for row in data:
        # row: {'time': 'HH:00', 'solar': kwh, 'load': kwh, 'battery_charge': kwh, 'battery_discharge': kwh,
        #       'grid_import': kwh, 'grid_export': kwh, ...}
        time_str = row.get("time", "00:00")
        grid_import = float(row.get("grid_import", 0.0) or 0.0)
        grid_export = float(row.get("grid_export", 0.0) or 0.0)
        solar = float(row.get("solar", 0.0) or 0.0)
        load = float(row.get("load", 0.0) or 0.0)

        energy.solar_kwh += solar
        energy.load_kwh += load

        if _is_peak_time(time_str, billing_cfg):
            energy.import_peak_kwh += grid_import
            energy.export_peak_kwh += grid_export
        else:
            energy.import_off_kwh += grid_import
            energy.export_off_kwh += grid_export

    return energy


def _aggregate_meter_hourly_for_billing_month(
    meter_calc: MeterEnergyCalculator,
    meter_ids: List[str],
    start: datetime,
    end: datetime,
    billing_cfg: BillingConfig,
    energy_calc: Optional[EnergyCalculator] = None,
    inverter_id: Optional[str] = None,
) -> BillingMonthEnergy:
    """
    Aggregate meter_hourly_energy rows into billing-month level energy metrics, split into peak/off-peak.
    
    If meter data is missing for specific hours, falls back to inverter data for those hours.
    
    Note: Meters only provide import/export data, not solar/load. Solar/load should be aggregated separately
    from inverter data.
    
    Args:
        meter_calc: Meter energy calculator
        meter_ids: List of meter IDs to aggregate
        start: Start datetime
        end: End datetime
        billing_cfg: Billing configuration
        energy_calc: Optional energy calculator for fallback to inverter data
        inverter_id: Optional inverter ID for fallback (use "all" for all inverters)
    """
    start_local = to_configured(start)
    end_local = to_configured(end - timedelta(seconds=1))
    
    # Get meter hourly data
    meter_data = meter_calc.get_hourly_energy_data(meter_ids, start_local, end_local)
    
    log.debug(f"_aggregate_meter_hourly_for_billing_month: meter_ids={meter_ids}, "
              f"start={start_local}, end={end_local}, meter_rows_returned={len(meter_data)}")

    # Build a map of date_hour -> meter data for precise hour-by-hour matching
    meter_data_map = {}
    for row in meter_data:
        # Use date_hour if available, otherwise fall back to time
        key = row.get('date_hour') or row.get('time')
        meter_data_map[key] = row
    
    # Generate all expected hours in the time range (using date+hour format)
    all_expected_hours = set()
    current_hour = start_local.replace(minute=0, second=0, microsecond=0)
    while current_hour <= end_local:
        date_str = current_hour.strftime('%Y-%m-%d')
        hour_str = current_hour.strftime('%H:00')
        date_hour_str = f"{date_str} {hour_str}"
        all_expected_hours.add(date_hour_str)
        current_hour += timedelta(hours=1)
    
    # Get missing hours if fallback is enabled
    missing_hours = all_expected_hours - set(meter_data_map.keys())
    
    if missing_hours and energy_calc and inverter_id:
        log.debug(f"Found {len(missing_hours)} missing hours in meter data, using inverter fallback")
        
        # Get inverter data for fallback
        inverter_data = energy_calc.get_hourly_energy_data(inverter_id, start_local, end_local)
        # Build inverter data map using date_hour as key
        inverter_data_map = {}
        for row in inverter_data:
            key = row.get('date_hour') or row.get('time')
            inverter_data_map[key] = row
        
        # Fill in missing hours with inverter data (hour-by-hour fallback)
        fallback_count = 0
        for date_hour_str in missing_hours:
            if date_hour_str in inverter_data_map:
                inv_row = inverter_data_map[date_hour_str]
                # Extract hour from date_hour_str for backward compatibility
                hour_str = date_hour_str.split(' ')[1] if ' ' in date_hour_str else date_hour_str
                # Add inverter data to meter data map (for missing hours only)
                meter_data_map[date_hour_str] = {
                    'time': hour_str,  # Keep for backward compatibility
                    'date_hour': date_hour_str,  # Include date_hour
                    'import': inv_row.get('grid_import', 0.0) or 0.0,
                    'export': inv_row.get('grid_export', 0.0) or 0.0,
                    'avg_power_w': inv_row.get('avg_grid_power_w', 0.0) or 0.0,
                    'sample_count': inv_row.get('sample_count', 0) or 0,
                    '_fallback': True  # Mark as fallback data
                }
                fallback_count += 1
        
        if fallback_count > 0:
            log.info(f"Used inverter fallback for {fallback_count} missing hours in meter data")
        elif missing_hours:
            log.warning(f"Found {len(missing_hours)} missing hours but inverter data not available for fallback")

    energy = BillingMonthEnergy(
        label=f"{start_local.strftime('%Y-%m-%d')}:{end_local.strftime('%Y-%m-%d')}",
        start=start_local,
        end=end_local,
    )

    # Aggregate all hours (meter data + fallback data)
    for date_hour_key, row in sorted(meter_data_map.items()):
        # Extract time string for peak/off-peak determination
        time_str = row.get("time")
        if not time_str:
            # Fallback: extract hour from date_hour_key
            if ' ' in date_hour_key:
                time_str = date_hour_key.split(' ')[1]
            else:
                time_str = date_hour_key
        
        grid_import = float(row.get("import", 0.0) or 0.0)
        grid_export = float(row.get("export", 0.0) or 0.0)

        # Solar and load remain 0.0 (meters don't provide this data)
        if _is_peak_time(time_str, billing_cfg):
            energy.import_peak_kwh += grid_import
            energy.export_peak_kwh += grid_export
        else:
            energy.import_off_kwh += grid_import
            energy.export_off_kwh += grid_export

    return energy


def simulate_billing_year(
    db_path: str,
    billing_cfg: BillingConfig,
    year: int,
    inverter_id: str = "all",
) -> Dict[str, Any]:
    """
    Run billing simulation for a given year and inverter_id (default 'all').

    Returns a dictionary with:
      - 'year'
      - 'months': list of BillingMonthBill as dicts
      - 'summary': annual totals & final credit balance
    """
    tz = get_configured_timezone()
    energy_calc = EnergyCalculator(db_path)

    # Determine billing months
    months_def = _billing_month_boundaries(year, billing_cfg.anchor_day, tz)

    # 3‑month cycle credit pools (kWh)
    credits_off_cycle = 0.0
    credits_peak_cycle = 0.0
    # Monetary credit balance (currency)
    credit_balance = 0.0

    months_results: List[BillingMonthBill] = []

    # Track annual energy for capacity calculations
    total_solar = 0.0
    total_load = 0.0
    total_import_off = 0.0
    total_import_peak = 0.0
    total_export_off = 0.0
    total_export_peak = 0.0

    for idx, (start, end, label) in enumerate(months_def):
        energy = _aggregate_hourly_for_billing_month(
            energy_calc=energy_calc,
            inverter_id=inverter_id,
            start=start,
            end=end,
            billing_cfg=billing_cfg,
        )

        total_solar += energy.solar_kwh
        total_load += energy.load_kwh
        total_import_off += energy.import_off_kwh
        total_import_peak += energy.import_peak_kwh
        total_export_off += energy.export_off_kwh
        total_export_peak += energy.export_peak_kwh

        # --- Off-peak netting within cycle ---
        raw_net_off = energy.import_off_kwh - energy.export_off_kwh
        if raw_net_off > 0:
            # Use existing credits to offset
            net_import_off = max(0.0, raw_net_off - credits_off_cycle)
            credits_off_cycle = max(0.0, credits_off_cycle - raw_net_off)
        else:
            # Export dominates -> accumulate credits
            net_import_off = 0.0
            credits_off_cycle += (-raw_net_off)

        # --- Peak netting within cycle ---
        raw_net_peak = energy.import_peak_kwh - energy.export_peak_kwh
        if raw_net_peak > 0:
            net_import_peak = max(0.0, raw_net_peak - credits_peak_cycle)
            credits_peak_cycle = max(0.0, credits_peak_cycle - raw_net_peak)
        else:
            net_import_peak = 0.0
            credits_peak_cycle += (-raw_net_peak)

        # --- Base charges ---
        off_charge = net_import_off * billing_cfg.price_offpeak_import
        peak_charge = net_import_peak * billing_cfg.price_peak_import
        fixed_charge = billing_cfg.fixed_charge_per_billing_month

        cycle_credit_off = 0.0
        cycle_credit_peak = 0.0

        # If this is the last month of the current 3‑month cycle, settle credits
        # Cycles: months 0-2, 3-5, 6-8, 9-11
        if (idx + 1) % 3 == 0:
            if credits_off_cycle > 0:
                cycle_credit_off = credits_off_cycle * billing_cfg.price_offpeak_settlement
                credits_off_cycle = 0.0
            if credits_peak_cycle > 0:
                cycle_credit_peak = credits_peak_cycle * billing_cfg.price_peak_settlement
                credits_peak_cycle = 0.0

        # Raw bill this month (before monetary carry-forward)
        raw_bill = off_charge + peak_charge + fixed_charge - cycle_credit_off - cycle_credit_peak

        # Apply monetary credit balance
        if raw_bill > 0 and credit_balance < 0:
            final_bill = max(0.0, raw_bill + credit_balance)
            credit_balance = min(0.0, credit_balance + raw_bill)
        else:
            # raw_bill <= 0 or no credit available: add to balance
            final_bill = max(0.0, raw_bill)
            if raw_bill <= 0:
                credit_balance += raw_bill

        month_bill = BillingMonthBill(
            billing_month=label,
            energy=energy,
            net_import_off_kwh=net_import_off,
            net_import_peak_kwh=net_import_peak,
            fixed_charge=fixed_charge,
            cycle_credit_off=cycle_credit_off,
            cycle_credit_peak=cycle_credit_peak,
            raw_bill=raw_bill,
            final_bill=final_bill,
            credit_balance_after=credit_balance,
        )
        months_results.append(month_bill)

    annual_final_bill = sum(m.final_bill for m in months_results)

    summary = {
        "year": year,
        "total_solar_kwh": total_solar,
        "total_load_kwh": total_load,
        "total_import_off_kwh": total_import_off,
        "total_import_peak_kwh": total_import_peak,
        "total_export_off_kwh": total_export_off,
        "total_export_peak_kwh": total_export_peak,
        "annual_final_bill": annual_final_bill,
        "final_credit_balance": credit_balance,
    }

    return {
        "year": year,
        "months": [
            {
                "billingMonth": m.billing_month,
                "import_off_kwh": m.energy.import_off_kwh,
                "import_peak_kwh": m.energy.import_peak_kwh,
                "export_off_kwh": m.energy.export_off_kwh,
                "export_peak_kwh": m.energy.export_peak_kwh,
                "solar_kwh": m.energy.solar_kwh,
                "load_kwh": m.energy.load_kwh,
                "net_import_off_kwh": m.net_import_off_kwh,
                "net_import_peak_kwh": m.net_import_peak_kwh,
                "fixed_charge": m.fixed_charge,
                "cycle_credit_off": m.cycle_credit_off,
                "cycle_credit_peak": m.cycle_credit_peak,
                "raw_bill": m.raw_bill,
                "final_bill": m.final_bill,
                "credit_balance_after": m.credit_balance_after,
            }
            for m in months_results
        ],
        "summary": summary,
    }


def estimate_capacity_status(
    annual_billing: Dict[str, Any],
    installed_kw: float,
    billing_cfg: BillingConfig,
) -> Dict[str, Any]:
    """
    Very simple capacity estimation based on annual net imports/exports.

    This is an approximation and can be refined later:
    - If annual_final_bill <= 0 -> at least balanced; required_kw_for_zero_bill = installed_kw.
    - If annual_final_bill > 0 -> assume we need extra capacity proportional to current solar production
      to offset the remaining bill.
    """
    installed_kw = max(0.0, installed_kw)
    total_solar = float(annual_billing["summary"].get("total_solar_kwh", 0.0) or 0.0)
    annual_bill = float(annual_billing["summary"].get("annual_final_bill", 0.0) or 0.0)

    if installed_kw <= 0 or total_solar <= 0:
        return {
            "installed_kw": installed_kw,
            "required_kw_for_zero_bill": installed_kw,
            "status": "unknown",
            "deficit_kw": 0.0,
        }

    if annual_bill <= 0:
        return {
            "installed_kw": installed_kw,
            "required_kw_for_zero_bill": installed_kw,
            "status": "balanced",
            "deficit_kw": 0.0,
        }

    # Approximate: assume that additional solar production reduces bill linearly with
    # average effective price (weighted between peak/off-peak).
    # Effective price: use off-peak import price as conservative baseline.
    effective_price = max(billing_cfg.price_offpeak_import, 0.01)
    extra_kwh_needed = annual_bill / effective_price

    # Production per kW per year:
    solar_per_kw = total_solar / installed_kw
    if solar_per_kw <= 0:
        required_kw = installed_kw
    else:
        extra_kw = extra_kwh_needed / solar_per_kw
        required_kw = installed_kw + extra_kw

    deficit_kw = required_kw - installed_kw
    status = "under-capacity" if deficit_kw > 0.25 else "balanced"

    return {
        "installed_kw": installed_kw,
        "required_kw_for_zero_bill": round(required_kw, 3),
        "status": status,
        "deficit_kw": round(deficit_kw, 3),
    }


def forecast_next_billing(
    annual_billing: Dict[str, Any],
    billing_cfg: BillingConfig,
    months_ahead: int = 1,
    method: str = "trend",
) -> Dict[str, Any]:
    """
    Simple forecast for the next billing month, based on recent history.
    - trend: use average of last 3 months.
    - seasonal: use average of months with same label suffix (MM) if available.

    Returns a small object with predicted imports/exports/bill and a confidence value.
    """
    months = annual_billing.get("months", [])
    if not months:
        return {
            "predicted_import_kwh": 0.0,
            "predicted_export_kwh": 0.0,
            "predicted_bill": 0.0,
            "confidence": 0.0,
        }

    # Use last up-to-12 months for statistics
    history = months[-12:]

    if method == "seasonal" and len(history) >= 4:
        # Group by MM suffix
        by_month: Dict[str, List[Dict[str, Any]]] = {}
        for m in history:
            label = m["billingMonth"]
            mm = label.split("-")[1] if "-" in label else label
            by_month.setdefault(mm, []).append(m)
        # Assume next month has last month's MM suffix (approximate)
        last_label = history[-1]["billingMonth"]
        last_year, last_mm = last_label.split("-")
        target_mm = last_mm  # simplistic: same month next year
        candidates = by_month.get(target_mm, history)
    else:
        # trend-based: last 3 months
        candidates = history[-3:] if len(history) >= 3 else history

    if not candidates:
        return {
            "predicted_import_kwh": 0.0,
            "predicted_export_kwh": 0.0,
            "predicted_bill": 0.0,
            "confidence": 0.0,
        }

    avg_import = sum(c["import_off_kwh"] + c["import_peak_kwh"] for c in candidates) / len(candidates)
    avg_export = sum(c["export_off_kwh"] + c["export_peak_kwh"] for c in candidates) / len(candidates)
    avg_bill = sum(c["final_bill"] for c in candidates) / len(candidates)

    # Confidence: simple function of number of points used
    confidence = min(1.0, len(candidates) / 6.0)

    return {
        "predicted_import_kwh": round(avg_import, 3),
        "predicted_export_kwh": round(avg_export, 3),
        "predicted_bill": round(avg_bill, 2),
        "confidence": confidence,
    }


