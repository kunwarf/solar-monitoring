# solarhub/schedulers/smart.py
import logging, pytz
import hashlib
from typing import Dict, Any, List, Tuple, Optional
from .helpers import EnergyPlanner, TariffManager, GridManager, InverterManager, SolarQualityAssessor
from .reliability import ReliabilityManager
from .power_splitter import split_power, InverterCapabilities, calculate_headroom
from dataclasses import dataclass
from datetime import datetime, timezone, time as dtime
import pandas as pd

from solarhub.config import ForecastConfig
from solarhub.forecast.weather import NaiveWeather, OpenMeteoWeather
from solarhub.forecast.enhanced_weather import EnhancedWeather
from solarhub.forecast.weatherapi_weather import WeatherAPIWeather
from solarhub.forecast.openweather_simple import OpenWeatherSimple
from solarhub.forecast.simple_weather import SimpleWeather
from solarhub.api_key_manager import get_weather_api_key
from solarhub.forecast.solar import PvlibSolarEstimator
from solarhub.schedulers.bias import BiasLearner
from solarhub.schedulers.load import LoadLearner
from solarhub.logging.logger import DataLogger
from solarhub.database_optimizer import optimize_database_if_needed
from solarhub.daily_aggregator import initialize_daily_aggregation
from solarhub.config_manager import ConfigurationManager
from solarhub.ha.battery_optimization_discovery import BatteryOptimizationDiscovery
from solarhub.ha.config_discovery import ConfigDiscoveryPublisher
from solarhub.ha.config_command_handler import ConfigCommandHandler
from solarhub.ha.inverter_config_discovery import InverterConfigDiscovery
from solarhub.ha.inverter_config_command_handler import InverterConfigCommandHandler
# ADD at top with other imports
import math
import json
try:
    import pvlib
except Exception:
    pvlib = None

log = logging.getLogger(__name__)

def now_iso() -> str:
    from solarhub.timezone_utils import now_configured_iso
    return now_configured_iso()

@dataclass
class TariffWindow:
    """One tariff window in local time."""
    kind: str          # "cheap", "normal", "peak"
    start: dtime       # inclusive
    end: dtime         # exclusive
    price: float       # arbitrary units; cheaper is better
    allow_grid_charge: bool = True
    allow_discharge: bool = True

def _parse_hhmm(hhmm: str) -> dtime:
    hh, mm = hhmm.split(":")
    return dtime(int(hh), int(mm))

def _in_window(t: dtime, w: TariffWindow) -> bool:
    if w.start <= w.end:  # normal same-day
        return (t >= w.start) and (t < w.end)
    # overnight window (e.g., 23:00-06:00)
    return (t >= w.start) or (t < w.end)

class SmartScheduler:
    """
    Tariff-aware, multi-window smart control:
      - learns PV shape & load profile
      - targets SOC before sunset (configurable)
      - uses cheap tariff windows for grid charging
      - protects blackout reserve & adds hysteresis
      - programs up to 3 TOU windows (1..3)
      - caps grid charge power by current * voltage and model max
    """

    def _calculate_energy_requirements(self, soc_pct: float, batt_kwh: float, end_soc_target_pct: int) -> Dict[str, float]:
        """
        Calculate energy requirements once and reuse throughout the charging logic.
        
        Args:
            soc_pct: Current SOC percentage
            batt_kwh: Battery capacity in kWh
            end_soc_target_pct: Target SOC percentage
            
        Returns:
            Dictionary with energy requirement calculations
        """
        current_soc_kwh = (soc_pct / 100.0) * batt_kwh
        target_soc_kwh = (end_soc_target_pct / 100.0) * batt_kwh
        energy_needed_kwh = max(0, target_soc_kwh - current_soc_kwh)
        
        return {
            'current_soc_kwh': current_soc_kwh,
            'target_soc_kwh': target_soc_kwh,
            'energy_needed_kwh': energy_needed_kwh
        }

    def _calculate_optimal_charge_power(self, power_kw: float, max_charge_power_w: int) -> int:
        """
        Calculate and cap charge power consistently across all charging contexts.
        
        Args:
            power_kw: Desired power in kW
            max_charge_power_w: Maximum allowed charge power in W
            
        Returns:
            Optimal charge power in W, capped at maximum
        """
        return int(min(power_kw * 1000, max_charge_power_w))

    def _assess_solar_sufficiency(self, available_power_kw: float, required_power_kw: float, 
                                daily_excess_solar_kwh: float, energy_needed_kwh: float) -> Dict[str, bool]:
        """
        Unified solar sufficiency assessment with consistent logic.
        
        Args:
            available_power_kw: Available solar power in kW
            required_power_kw: Required power in kW
            daily_excess_solar_kwh: Daily excess solar energy in kWh
            energy_needed_kwh: Energy needed to reach target SOC in kWh
            
        Returns:
            Dictionary with solar sufficiency assessments
        """
        # Primary assessment: immediate power availability
        solar_insufficient = available_power_kw < required_power_kw
        
        # Secondary assessment: daily energy sufficiency (with 20% margin)
        daily_solar_insufficient = daily_excess_solar_kwh < (energy_needed_kwh * 0.8)
        
        # Combined assessment: solar is insufficient if either condition is true
        overall_solar_insufficient = solar_insufficient or daily_solar_insufficient
        
        return {
            'solar_insufficient': solar_insufficient,
            'daily_solar_insufficient': daily_solar_insufficient,
            'overall_solar_insufficient': overall_solar_insufficient
        }

    def _calculate_unified_charging_plan(self, tznow: pd.Timestamp, site_pv_hourly: Dict[int, float],
                                       site_load_hourly: Dict[int, float], soc_pct: float, batt_kwh: float,
                                       max_charge_power_w: int, max_discharge_power_w: int, end_soc_target_pct: int,
                                       effective_min_soc: float, sunset_hour: float, sunrise_hour: float,
                                       grid_available: bool, tariffs: List = None) -> Dict[str, Any]:
        """
        UNIFIED CHARGING PLAN: Single method that calculates ALL TOU windows once, considering:
        - Solar generation forecast
        - Load requirements  
        - Target SOC (must be reached before 2 hours before sunset)
        - Battery capacity and current SOC
        - Grid availability
        - Tariff windows
        
        This replaces ALL other TOU window calculation methods to eliminate duplication
        and ensure consistent logic.
        
        Args:
            tznow: Current time
            site_pv_hourly: Hourly PV forecast
            site_load_hourly: Hourly load forecast
            soc_pct: Current SOC percentage
            batt_kwh: Battery capacity in kWh
            max_charge_power_w: Maximum charge power in W
            max_discharge_power_w: Maximum discharge power in W
            end_soc_target_pct: Target SOC percentage
            effective_min_soc: Effective minimum SOC percentage
            sunset_hour: Sunset hour
            sunrise_hour: Sunrise hour
            grid_available: Whether grid is available
            tariffs: List of tariff windows (optional)
            
        Returns:
            Dictionary with complete charging plan including all TOU windows
        """
        log.info("=== UNIFIED CHARGING PLAN CALCULATION ===")
        
        # 1. CALCULATE ALL REQUIREMENTS ONCE
        energy_reqs = self._calculate_energy_requirements(soc_pct, batt_kwh, end_soc_target_pct)
        current_hour = tznow.hour
        current_minute = tznow.minute
        current_time_decimal = current_hour + current_minute / 60.0
        
        # 2. CALCULATE SOLAR CHARGE DEADLINE (configurable hours before sunset - CONSISTENT)
        # Use the same calculation as the main tick method for consistency
        pol = self.hub.cfg.smart.policy
        deadline_hours_before_sunset = int(getattr(pol, "solar_charge_deadline_hours_before_sunset", 2))
        deadline_hours_before_sunset = max(0, min(6, deadline_hours_before_sunset))  # constrain 0..6 hours
        solar_charge_deadline_h = max(0, sunset_hour - deadline_hours_before_sunset)
        log.info(f"Solar charge deadline: {solar_charge_deadline_h:.1f} hours ({deadline_hours_before_sunset} hours before sunset {sunset_hour:.1f})")
        
        # 3. CALCULATE DAILY TOTALS
        daily_pv_kwh = sum(site_pv_hourly.values())
        daily_load_kwh = sum(site_load_hourly.values())
        daily_excess_solar_kwh = max(0, daily_pv_kwh - daily_load_kwh)
        
        # 4. CALCULATE REMAINING SOLAR HOURS UNTIL DEADLINE
        if current_time_decimal < sunrise_hour:
            remaining_solar_hours = solar_charge_deadline_h - sunrise_hour
        elif current_time_decimal < solar_charge_deadline_h:
            remaining_solar_hours = solar_charge_deadline_h - current_time_decimal
        else:
            remaining_solar_hours = 0
        
        log.info(f"Remaining solar hours until deadline: {remaining_solar_hours:.2f}h")
        
        # 5. CALCULATE REQUIRED POWER TO REACH TARGET SOC
        if remaining_solar_hours > 0:
            required_power_kw = energy_reqs['energy_needed_kwh'] / remaining_solar_hours
        else:
            required_power_kw = 0
        
        # 6. CALCULATE CURRENT AVAILABLE SOLAR POWER
        current_pv_kw = site_pv_hourly.get(current_hour, 0)
        current_load_kw = site_load_hourly.get(current_hour, 0)
        available_power_kw = max(0, current_pv_kw - current_load_kw)
        
        # 7. ASSESS SOLAR SUFFICIENCY
        solar_assessment = self._assess_solar_sufficiency(
            available_power_kw, required_power_kw, 
            daily_excess_solar_kwh, energy_reqs['energy_needed_kwh']
        )
        
        log.info(f"Solar assessment: insufficient={solar_assessment['overall_solar_insufficient']}, "
                f"required={required_power_kw:.2f}kW, available={available_power_kw:.2f}kW")
        
        # 8. INITIALIZE WINDOWS LIST
        windows = []
        
        # 9. MORNING CHARGE WINDOW (if needed and before deadline)
        morning_start_hour = int(sunrise_hour)
        morning_end_hour = min(int(sunrise_hour + 2), int(solar_charge_deadline_h))
        
        if current_hour < morning_end_hour and energy_reqs['energy_needed_kwh'] > 0:
            # Calculate morning solar availability
            morning_pv_kw = sum(site_pv_hourly.get(h, 0) for h in range(morning_start_hour, morning_end_hour))
            morning_load_kw = sum(site_load_hourly.get(h, 0) for h in range(morning_start_hour, morning_end_hour))
            morning_excess_solar_kw = max(0, morning_pv_kw - morning_load_kw)
            
            # Only set morning window if solar is insufficient or SOC is very low
            should_set_morning = (
                morning_excess_solar_kw < energy_reqs['energy_needed_kwh'] or
                soc_pct < 30 or
                morning_excess_solar_kw < 0.5
            )
            
            if should_set_morning:
                hours_available = morning_end_hour - max(current_hour, morning_start_hour)
                if hours_available > 0:
                    net_morning_load_kw = max(0, morning_load_kw - morning_pv_kw)
                    optimal_charge_kw = (net_morning_load_kw + energy_reqs['energy_needed_kwh']) / hours_available
                    optimal_charge_power_w = self._calculate_optimal_charge_power(optimal_charge_kw, max_charge_power_w)
                    
                    windows.append({
                        "name": "Morning Charge",
                        "start_time": f"{morning_start_hour:02d}:00",
                        "end_time": f"{morning_end_hour:02d}:00",
                        "type": "charge",
                        "charge_power_w": optimal_charge_power_w,
                        "discharge_power_w": 0,
                        "target_soc": int(end_soc_target_pct),
                        "enabled": True
                    })
                    log.info(f"Added morning charge window: {morning_start_hour:02d}:00-{morning_end_hour:02d}:00 ({optimal_charge_power_w}W)")
        
        # 10. MAIN SOLAR CHARGE WINDOW (until 2 hours before sunset)
        if (energy_reqs['energy_needed_kwh'] > 0.5 and 
            daily_excess_solar_kwh > 1.0 and 
            soc_pct < end_soc_target_pct - 5):
            
            # Calculate optimal charge power
            if solar_assessment['overall_solar_insufficient']:
                optimal_charge_power_w = self._calculate_optimal_charge_power(available_power_kw, max_charge_power_w)
                grid_charge_needed = True
                energy_shortfall_kwh = energy_reqs['energy_needed_kwh'] - (available_power_kw * remaining_solar_hours)
            else:
                optimal_charge_power_w = self._calculate_optimal_charge_power(required_power_kw, max_charge_power_w)
                grid_charge_needed = False
                energy_shortfall_kwh = 0
            
            # Determine window start time
            if current_time_decimal >= sunrise_hour:
                window_start_time = f"{current_hour:02d}:{current_minute:02d}"
            else:
                window_start_time = f"{int(sunrise_hour):02d}:00"
            
            windows.append({
                "name": "Solar Charge",
                "start_time": window_start_time,
                "end_time": f"{int(solar_charge_deadline_h):02d}:00",
                "type": "charge",
                "charge_power_w": optimal_charge_power_w,
                "discharge_power_w": 0,
                "target_soc": int(end_soc_target_pct),
                "enabled": True
            })
            
            log.info(f"Added solar charge window: {window_start_time}-{int(solar_charge_deadline_h):02d}:00 ({optimal_charge_power_w}W)")
            
            # Set grid charging flags if needed
            if grid_charge_needed:
                self._grid_charge_needed_for_target = True
                self._grid_charge_shortfall_kwh = energy_shortfall_kwh
                log.warning(f"Solar insufficient - grid charging needed for {energy_shortfall_kwh:.2f}kWh shortfall")
        
        # 11. PEAK DISCHARGE WINDOW (if tariffs available)
        peak_end = int(solar_charge_deadline_h)  # Default to solar deadline if no peak tariffs
        if tariffs:
            peak_tariffs = [t for t in tariffs if t.kind == "peak" and t.allow_discharge]
            if peak_tariffs and soc_pct > effective_min_soc + 10:  # Only if sufficient SOC
                peak_start = min(t.start.hour for t in peak_tariffs)
                peak_end = max(t.end.hour for t in peak_tariffs)
                
                # Calculate peak discharge power
                peak_load_kw = sum(site_load_hourly.get(h, 0) for h in range(peak_start, peak_end))
                peak_pv_kw = sum(site_pv_hourly.get(h, 0) for h in range(peak_start, peak_end))
                net_peak_load_kw = max(0, peak_load_kw - peak_pv_kw)
                
                if net_peak_load_kw > 0:
                    peak_hours = peak_end - peak_start
                    current_soc_kwh = energy_reqs['current_soc_kwh']
                    min_soc_kwh = (effective_min_soc / 100.0) * batt_kwh
                    available_energy_kwh = max(0, current_soc_kwh - min_soc_kwh)
                    
                    if peak_hours > 0 and available_energy_kwh > 0:
                        optimal_discharge_kw = min(net_peak_load_kw, available_energy_kwh / peak_hours)
                        optimal_discharge_power_w = self._calculate_optimal_charge_power(optimal_discharge_kw, max_discharge_power_w)
                        
                        windows.append({
                            "name": "Peak Discharge",
                            "start_time": f"{peak_start:02d}:00",
                            "end_time": f"{peak_end:02d}:00",
                            "type": "discharge",
                            "charge_power_w": 0,
                            "discharge_power_w": optimal_discharge_power_w,
                            "target_soc": int(math.ceil(effective_min_soc)),
                            "enabled": True
                        })
                        log.info(f"Added peak discharge window: {peak_start:02d}:00-{peak_end:02d}:00 ({optimal_discharge_power_w}W)")
        
        # 12. NIGHT DISCHARGE WINDOW (after peak discharge window to avoid overlap)
        # Start after peak discharge window ends to avoid overlapping
        night_start_hour = max(int(solar_charge_deadline_h + 1), peak_end)  # Start after solar deadline or peak window
        night_hours = list(range(night_start_hour, 24)) + list(range(0, int(sunrise_hour)))
        
        if night_hours:
            max_night_load_kw = max((site_load_hourly.get(h, 0.0) for h in night_hours), default=0.0)
            if max_night_load_kw > 0:
                night_discharge_power_w = self._calculate_optimal_charge_power(max_night_load_kw, max_discharge_power_w)
                
                windows.append({
                    "name": "Night Discharge",
                    "start_time": f"{night_start_hour:02d}:00",
                    "end_time": f"{int(sunrise_hour):02d}:00",
                    "type": "discharge",
                    "charge_power_w": 0,
                    "discharge_power_w": night_discharge_power_w,
                    "target_soc": int(math.ceil(effective_min_soc)),
                    "enabled": True
                })
                log.info(f"Added night discharge window: {night_start_hour:02d}:00-{int(sunrise_hour):02d}:00 ({night_discharge_power_w}W)")
        
        # 13. ADJUST WINDOWS BASED ON CURRENT SOC
        for window in windows:
            if soc_pct < 30 and window["type"] == "charge":
                # Increase charge power when SOC is low
                increased_power_kw = window["charge_power_w"] * 1.5 / 1000
                window["charge_power_w"] = self._calculate_optimal_charge_power(increased_power_kw, max_charge_power_w)
                window["target_soc"] = min(window["target_soc"] + 10, 100)
            elif soc_pct > 80 and window["type"] == "discharge":
                # Increase discharge power when SOC is high
                increased_power_kw = window["discharge_power_w"] * 1.5 / 1000
                window["discharge_power_w"] = self._calculate_optimal_charge_power(increased_power_kw, max_discharge_power_w)
        
        # 14. RETURN COMPLETE CHARGING PLAN
        plan = {
            'windows': windows,
            'energy_reqs': energy_reqs,
            'solar_assessment': solar_assessment,
            'solar_charge_deadline_h': solar_charge_deadline_h,
            'remaining_solar_hours': remaining_solar_hours,
            'required_power_kw': required_power_kw,
            'available_power_kw': available_power_kw,
            'daily_excess_solar_kwh': daily_excess_solar_kwh,
            'grid_charge_needed': getattr(self, '_grid_charge_needed_for_target', False),
            'energy_shortfall_kwh': getattr(self, '_grid_charge_shortfall_kwh', 0)
        }
        
        log.info(f"Unified charging plan completed: {len(windows)} windows created")
        return plan

    def _detect_past_tou_windows(self, telemetry, tznow: pd.Timestamp) -> bool:
        """
        Detect if any TOU windows in the current telemetry are in the past or invalid.
        
        Args:
            telemetry: Current inverter telemetry data (Telemetry object or dict)
            tznow: Current time
            
        Returns:
            True if past/invalid windows are detected, False otherwise
        """
        if not telemetry:
            return False
        
        current_hour = tznow.hour
        current_minute = tznow.minute
        current_time_minutes = current_hour * 60 + current_minute
        
        # Check all 3 TOU windows
        for idx in range(1, 4):
            # Handle both Telemetry objects and dictionaries
            if hasattr(telemetry, 'extra'):
                # Telemetry object - access via extra field
                start_time = telemetry.extra.get(f"charge_start_time_{idx}")
                end_time = telemetry.extra.get(f"charge_end_time_{idx}")
            else:
                # Dictionary - access directly
                start_time = telemetry.get(f"charge_start_time_{idx}")
                end_time = telemetry.get(f"charge_end_time_{idx}")
            
            if start_time and end_time and start_time != "00:00" and end_time != "00:00":
                try:
                    # Parse time strings (format: "HH:MM")
                    start_hour, start_min = map(int, start_time.split(":"))
                    end_hour, end_min = map(int, end_time.split(":"))
                    
                    start_minutes = start_hour * 60 + start_min
                    end_minutes = end_hour * 60 + end_min
                    
                    # Check if window is in the past
                    # For overnight windows (e.g., 23:00-06:00), check if we're past the end time
                    if start_minutes > end_minutes:  # Overnight window
                        if current_time_minutes > end_minutes and current_time_minutes < start_minutes:
                            log.info(f"TOU window {idx} ({start_time}-{end_time}) is in the past (overnight window)")
                            return True
                    else:  # Same-day window
                        if current_time_minutes > end_minutes:
                            log.info(f"TOU window {idx} ({start_time}-{end_time}) is in the past (same-day window)")
                            return True
                            
                except (ValueError, AttributeError) as e:
                    log.warning(f"Could not parse TOU window {idx} times: {start_time}-{end_time}, error: {e}")
                    return True  # Treat parsing errors as invalid windows
        
        return False

    def _detect_mode_change(self, telemetry, desired_mode: str) -> bool:
        """
        Detect if the inverter work mode has changed from the current telemetry.
        
        Args:
            telemetry: Current inverter telemetry data (Telemetry object or dict)
            desired_mode: The mode we want to set
            
        Returns:
            True if mode change is detected, False otherwise
        """
        if not telemetry:
            return True  # No telemetry means we should clear windows
        
        # Handle both Telemetry objects and dictionaries
        if hasattr(telemetry, 'inverter_mode'):
            # Telemetry object - access directly
            current_mode = telemetry.inverter_mode
        elif isinstance(telemetry, dict):
            # Dictionary - access via get method
            current_mode = telemetry.get("hybrid_work_mode")
        else:
            return True  # Unknown type, assume mode change needed
        if isinstance(current_mode, str):
            return current_mode != desired_mode
        elif isinstance(current_mode, int):
            # Map numeric mode to string for comparison
            mode_map = {
                0: "Self used mode",
                1: "Time-based control", 
                2: "Backup mode",
                3: "Feed-in priority mode"
            }
            current_mode_str = mode_map.get(current_mode, f"Unknown mode ({current_mode})")
            return current_mode_str != desired_mode
        
        return True  # Unknown mode format, clear windows

    def _detect_significant_time_change(self, tznow: pd.Timestamp) -> bool:
        """
        Detect if there's been a significant time change that should trigger window clearing.
        
        Args:
            tznow: Current time
            
        Returns:
            True if significant time change detected, False otherwise
        """
        # Store last check time in instance variable
        if not hasattr(self, '_last_time_check'):
            self._last_time_check = tznow
            return True  # First run, clear windows
        
        last_check = self._last_time_check
        time_diff = tznow - last_check
        
        # Clear windows if:
        # 1. More than 1 hour has passed
        # 2. We've crossed midnight (new day)
        # 3. We've crossed a significant boundary (e.g., sunrise/sunset times)
        should_clear = (
            time_diff.total_seconds() > 3600 or  # More than 1 hour
            tznow.date() != last_check.date() or  # Different day
            (last_check.hour < 6 and tznow.hour >= 6) or  # Crossed sunrise
            (last_check.hour < 18 and tznow.hour >= 18)   # Crossed sunset
        )
        
        if should_clear:
            self._last_time_check = tznow
            return True
        
        return False

    def _hourly_shape_today(self, est_list: list, tznow: pd.Timestamp) -> dict[int, float]:
        """
        Build a physics-based hourly PV shape for 'today' using pvlib clearsky POA.
        Returns {hour -> weight} that sums to 1.0 (or empty dict if pvlib missing).
        Uses caching to avoid expensive recalculations.
        """
        if pvlib is None or not est_list:
            return {}

        # Check cache first - use date as cache key since solar calculations are date-dependent
        today_str = tznow.strftime('%Y-%m-%d')
        cache_key = f"{today_str}_{len(est_list)}"
        
        if (self._pv_shape_cache_date == today_str and 
            cache_key in self._pv_shape_cache):
            return self._pv_shape_cache[cache_key]

        # Use location from scheduler config
        loc = pvlib.location.Location(self.fc.lat, self.fc.lon, tz=str(self.tz))
        # hourly index (start of hour) for today in local tz
        day = tznow.normalize()
        # Ensure pandas receives the same tz as the Timestamp to avoid tz inference mismatch
        idx = pd.date_range(day, periods=24, freq="1h", tz=tznow.tz)

        # Sum POA across arrays for this inverter
        poa_sum = pd.Series(0.0, index=idx)

        # Build a finer timeseries inside each hour for better integration (e.g., 10 min)
        fine = pd.date_range(day, periods=24 * 6, freq="10min", tz=tznow.tz)
        solpos = loc.get_solarposition(fine)
        cs = loc.get_clearsky(fine, model='ineichen')  # GHI/DNI/DHI

        for est in est_list:
            # array geometry
            tilt = float(est.cfg.tilt_deg)
            azim = float(est.cfg.azimuth_deg)
            # transposition to POA
            poa = pvlib.irradiance.get_total_irradiance(
                surface_tilt=tilt,
                surface_azimuth=azim,
                dni=cs['dni'],
                ghi=cs['ghi'],
                dhi=cs['dhi'],
                solar_zenith=solpos['zenith'],
                solar_azimuth=solpos['azimuth'],
            )
            poa_glob = poa['poa_global'].clip(lower=0)

            # integrate 10-min into hourly buckets
            hourly = poa_glob.resample("1h").mean()
            # sum with others
            # align to our 'idx' to avoid timezone index drift
            hourly = hourly.reindex(idx, fill_value=0.0)
            poa_sum = poa_sum.add(hourly, fill_value=0.0)

        # Keep only daylight hours (non-zero POA)
        poa_sum = poa_sum.clip(lower=0.0)
        total = float(poa_sum.sum())
        if total <= 0:
            return {}

        # Normalize to 1.0
        weights = (poa_sum / total).to_dict()
        # keys are Timestamps; map to hour int
        out: dict[int, float] = {}
        for ts, w in weights.items():
            out[int(pd.Timestamp(ts).hour)] = float(w)
        # make sure numerical cleanliness sums to ~1
        s = sum(out.values())
        if s > 0 and abs(s - 1.0) > 1e-6:
            # renormalize
            for h in out:
                out[h] = out[h] / s
        
        # Cache the result
        self._pv_shape_cache[cache_key] = out
        self._pv_shape_cache_date = today_str
        
        return out

    def _estimate_hourly_pv_kwh_from_instant(self, current_pv_w: float, tznow: pd.Timestamp) -> float:
        """Estimate this hour's PV energy (kWh) from an instantaneous PV power reading (W).

        Uses a simple bell-shaped solar curve around midday to infer peak power and
        the hour's average factor.
        """
        if current_pv_w <= 0:
            return 0.0

        def factor_at(hour_decimal: float) -> float:
            peak_hour = 12.5
            d = abs(hour_decimal - peak_hour)
            if d <= 1.0:
                f = 1.0
            elif d <= 3.0:
                f = 0.8 - (d - 1.0) * 0.2
            else:
                f = 0.6 - (d - 3.0) * 0.1
            return max(0.3, f)

        current_hour = tznow.hour
        current_minute = tznow.minute
        now_decimal = current_hour + current_minute / 60.0

        current_factor = factor_at(now_decimal)
        estimated_peak_w = current_pv_w / max(0.3, current_factor)

        start_factor = factor_at(float(current_hour))
        end_factor = factor_at(float(current_hour + 1))
        avg_hour_factor = (start_factor + end_factor) / 2.0

        return (estimated_peak_w * avg_hour_factor) / 1000.0

    def _get_inverter_capabilities(self, array_inverters: List) -> List[InverterCapabilities]:
        """
        Get capabilities for all inverters in the array from their telemetry.
        
        Args:
            array_inverters: List of InverterRuntime objects
            
        Returns:
            List of InverterCapabilities objects
        """
        capabilities = []
        for rt in array_inverters:
            tel = rt.adapter.last_tel if hasattr(rt.adapter, 'last_tel') else None
            if not tel:
                continue
            
            # Extract power values from telemetry
            if isinstance(tel, dict):
                batt_power_w = float(tel.get('batt_power_w', 0) or 0)
                extra = tel.get('extra', {}) or {}
            else:
                batt_power_w = float(getattr(tel, 'batt_power_w', 0) or 0)
                extra = getattr(tel, 'extra', {}) or {}
            
            # Determine charge/discharge from battery power (positive = charging, negative = discharging)
            current_charge_w = max(0, batt_power_w)
            current_discharge_w = abs(min(0, batt_power_w))
            
            # Get rated capabilities from config or telemetry
            # Default to config values if available, otherwise use telemetry
            rated_charge_kw = getattr(rt.cfg.safety, 'max_charge_a', 120) * 48.0 / 1000.0  # Rough estimate: A * 48V / 1000
            rated_discharge_kw = getattr(rt.cfg.safety, 'max_discharge_a', 120) * 48.0 / 1000.0
            
            # Try to get from telemetry if available
            if isinstance(tel, dict):
                max_charge_kw = extra.get('max_charge_power_w', rated_charge_kw * 1000) / 1000.0
                max_discharge_kw = extra.get('max_discharge_power_w', rated_discharge_kw * 1000) / 1000.0
            else:
                max_charge_kw = getattr(tel, 'max_charge_power_w', rated_charge_kw * 1000) / 1000.0 if hasattr(tel, 'max_charge_power_w') else rated_charge_kw
                max_discharge_kw = getattr(tel, 'max_discharge_power_w', rated_discharge_kw * 1000) / 1000.0 if hasattr(tel, 'max_discharge_power_w') else rated_discharge_kw
            
            # Check online/faulted status
            online = True  # Assume online if we have telemetry
            faulted = False
            if isinstance(tel, dict):
                faulted = extra.get('fault_status', 0) != 0
            else:
                faulted = getattr(tel, 'fault_status', 0) != 0 if hasattr(tel, 'fault_status') else False
            
            # Get power step from adapter if available
            power_step_w = None
            if hasattr(rt.adapter, 'get_power_step_w'):
                power_step_w = rt.adapter.get_power_step_w()
            
            capabilities.append(InverterCapabilities(
                inverter_id=rt.cfg.id,
                online=online,
                faulted=faulted,
                rated_charge_kw=rated_charge_kw,
                rated_discharge_kw=rated_discharge_kw,
                max_charge_kw_now=max_charge_kw,
                max_discharge_kw_now=max_discharge_kw,
                current_charge_w=current_charge_w,
                current_discharge_w=current_discharge_w,
                power_step_w=power_step_w,
                supports_abs_power_setpoint=True  # Assume true for now
            ))
        
        return capabilities

    def __init__(self, dbLogger: DataLogger, hub: "SolarApp", array_id: Optional[str] = None):
        """
        Initialize SmartScheduler.
        
        Args:
            dbLogger: DataLogger instance
            hub: SolarApp instance
            array_id: Optional array ID to scope this scheduler to a specific array.
                     If None, scheduler works with all inverters (legacy mode).
        """
        self.hub = hub
        self.dbLogger = dbLogger
        self.array_id = array_id  # Array this scheduler is scoped to
        self._last_split_plan: Optional[Dict[str, Any]] = None  # Store last split plan for API/MQTT
        fc = hub.cfg.smart.forecast
        self.fc = fc
        from solarhub.timezone_utils import get_configured_timezone
        self.tz = get_configured_timezone()
        # Get system timezone for weather forecasting
        system_tz = hub.cfg.timezone
        
        # Initialize enhanced weather forecasting
        log.info(f"Initializing weather provider: {fc.provider}")
        if fc.provider == "openmeteo":
            self.weather = EnhancedWeather(fc.lat, fc.lon, system_tz)
        elif fc.provider == "weatherapi":
            # WeatherAPI.com provider (requires API key)
            api_key = getattr(fc, 'weatherapi_key', None) or get_weather_api_key("weatherapi")
            self.weather = WeatherAPIWeather(fc.lat, fc.lon, system_tz, api_key)
        elif fc.provider == "openweather":
            # OpenWeatherMap provider (requires API key)
            # Debug: Check what's in the config object
            log.info(f"Config object attributes: {[attr for attr in dir(fc) if not attr.startswith('_')]}")
            log.info(f"Config openweather_key attribute: {getattr(fc, 'openweather_key', 'NOT_FOUND')}")

            # Prioritize config file API key over database lookup
            api_key = getattr(fc, 'openweather_key', None)
            if not api_key:
                api_key = get_weather_api_key("openweathermap")
            log.info(f"Using OpenWeatherMap provider with API key: {'Provided' if api_key else 'Not provided'}")
            if api_key:
                log.info(f"API key source: {'Config file' if getattr(fc, 'openweather_key', None) else 'Database/Environment'}")
            self.weather = OpenWeatherSimple(fc.lat, fc.lon, system_tz, api_key)
        elif fc.provider == "simple":
            # Simple weather provider (no API key required)
            self.weather = SimpleWeather(fc.lat, fc.lon, system_tz)
        else:
            self.weather = NaiveWeather()

        # Command throttling state to avoid redundant inverter writes
        self._last_command_signature: Optional[str] = None
        self._last_command_write_ts: Optional[datetime] = None
        self._last_effective_min_soc: Optional[float] = None
        self._last_work_mode: Optional[str] = None

        # Warning cooldown tracking to prevent repeated warnings
        self._last_grid_instability_warning = 0.0
        self._last_presunset_assurance_warning = 0.0
        self._warning_cooldown_seconds = 300  # 5 minutes

        # PV estimators per inverter/array
        # Filter inverters by array_id if scheduler is scoped to an array
        self.inv_estimators: Dict[str, list[PvlibSolarEstimator]] = {}
        array_inverters = [rt for rt in hub.inverters if not array_id or getattr(rt.cfg, 'array_id', None) == array_id]
        
        if array_id and not array_inverters:
            log.warning(f"No inverters found for array {array_id}")
        
        for rt in array_inverters:
            est_list = []
            for arr in rt.cfg.solar:
                invfc = ForecastConfig(
                    enabled=True, lat=fc.lat, lon=fc.lon, provider=fc.provider,
                    pv_dc_kw=arr.pv_dc_kw, pv_perf_ratio=arr.perf_ratio,
                    tilt_deg=arr.tilt_deg, azimuth_deg=arr.azimuth_deg, albedo=arr.albedo,
                )
                est_list.append(PvlibSolarEstimator(invfc))
            self.inv_estimators[rt.cfg.id] = est_list

        # Optimize database for better performance
        try:
            optimize_database_if_needed(dbLogger.path)
        except Exception as e:
            log.warning(f"Database optimization failed: {e}")
        # Initialize daily aggregation system
        try:
            self.daily_aggregator = initialize_daily_aggregation(dbLogger.path, system_tz)
            # Process any missing daily summaries for array inverters
            for rt in array_inverters:
                processed = self.daily_aggregator.process_missing_days(rt.cfg.id, days_back=7)
                if processed > 0:
                    log.info(f"Processed {processed} missing daily summaries for {rt.cfg.id}")
        except Exception as e:
            log.warning(f"Daily aggregation initialization failed: {e}")
            self.daily_aggregator = None

        # Learners
        self.bias = BiasLearner(dbLogger, tz=system_tz)
        self.load = LoadLearner(dbLogger, tz=system_tz)

        # Configuration manager for database persistence
        self.config_manager = ConfigurationManager("config.yaml", dbLogger)

        # Reliability manager for outage prevention and risk management
        self.reliability = ReliabilityManager(dbLogger, self.config_manager)

        # Backtest manager for policy auto-tuning
        from solarhub.schedulers.backtest import BacktestManager
        self.backtest = BacktestManager(dbLogger, self.config_manager)

        # Sunset calculator for Pakistan
        from solarhub.schedulers.sunset_calculator import PakistanSunsetCalculator
        self.sunset_calc = PakistanSunsetCalculator(system_tz)

        # Battery optimization discovery
        self.battery_ha = BatteryOptimizationDiscovery(hub.mqtt, hub.cfg.mqtt.base_topic)

        # Configuration discovery and command handling
        self.config_ha = ConfigDiscoveryPublisher(hub.mqtt, hub.cfg.mqtt.base_topic, hub.cfg)
        self.config_handler = ConfigCommandHandler(hub.cfg, dbLogger, self.config_ha)

        # Inverter configuration discovery and command handling
        self.inverter_config_ha = InverterConfigDiscovery(hub.mqtt, hub.cfg.mqtt.base_topic)
        # Initialize command handler later when adapters are available
        self.inverter_config_handler = None

        # Hysteresis memory
        self._last_use_grid: Optional[bool] = None

        # Grid availability hysteresis
        self._grid_availability_history: List[Tuple[float, bool]] = []  # List of (timestamp, available) tuples
        self._grid_hysteresis_threshold = 3  # Number of consecutive readings to confirm change
        self._grid_hysteresis_timeout = 30  # Seconds to wait before confirming grid loss
        self._last_grid_availability = True  # Last confirmed grid availability
        self._grid_availability_confidence = 1.0  # Confidence in current grid status

        # SOC logging frequency control
        self._last_soc_log_time: Optional[float] = None
        self._soc_log_interval_seconds = getattr(hub.cfg.smart.policy, 'soc_log_interval_secs', 300)  # Default 5 minutes

        # Backtest execution control
        self._last_backtest_date: Optional[str] = None
        self._daily_performance_data: Dict[str, Any] = {}

        # Forecast accuracy tracking
        self._forecast_accuracy_history: Dict[str, List[float]] = {
            'pv_accuracy': [],
            'load_accuracy': []
        }
        self._forecast_accuracy_window = 168  # Keep last 168 hours (1 week) of accuracy data

        # Initialize inverter config handler when adapters are available
        self._initialize_inverter_config_handler()

        # Performance optimization: Cache expensive calculations
        self._pv_shape_cache: Dict[str, Dict[int, float]] = {}
        self._pv_shape_cache_date: Optional[str] = None
        self._weather_cache: Optional[Dict[str, float]] = None

        self._weather_cache_time: Optional[float] = None
        self._bias_cache: Dict[str, Dict[Tuple[int,int], float]] = {}
        self._load_cache: Dict[Tuple[int,int], float] = {}
        self._cache_ttl_seconds = 300  # 5 minutes cache TTL

        # Unique cache key for weather provider
        self._weather_cache_key = f"smart_scheduler_{fc.lat}_{fc.lon}_{system_tz}_{fc.provider}"

        # Tariffs from config -> TariffWindow list (sorted by price asc)
        self.tariffs: List[TariffWindow] = []
        try:
            pol = hub.cfg.smart.policy
            for tw in getattr(pol, "tariffs", []):
                self.tariffs.append(TariffWindow(
                    kind=getattr(tw, "kind", "normal"),
                    start=_parse_hhmm(tw.start),
                    end=_parse_hhmm(tw.end),
                    price=float(getattr(tw, "price", 1.0)),
                    allow_grid_charge=bool(getattr(tw, "allow_grid_charge", True)),
                    allow_discharge=bool(getattr(tw, "allow_discharge", True)),
                ))
            # sort by price, cheapest first (better for grid charge)
            self.tariffs.sort(key=lambda t: t.price)
        except Exception as e:
            log.warning("Tariff parse failed; using default behavior: %s", e)
            self.tariffs = []

    def _initialize_inverter_config_handler(self):
        """Initialize the inverter config command handler when adapters are available."""
        try:
            if self.hub.inverters and not self.inverter_config_handler:
                # Get the first available adapter from the first inverter
                adapter = self.hub.inverters[0].adapter
                if adapter and hasattr(adapter, 'regs'):
                    self.inverter_config_handler = InverterConfigCommandHandler(adapter, self.inverter_config_ha, self.dbLogger)
                    log.info("Inverter config command handler initialized successfully")
                else:
                    log.debug("Adapter not ready for inverter config handler initialization")
        except Exception as e:
            log.warning(f"Could not initialize inverter config handler: {e}")
            # Don't fail the entire initialization if this fails


    def _energy_in_battery_kwh(self, soc_pct: float) -> float:
        return max(0.0, min(100.0, soc_pct)) / 100.0 * self.fc.batt_capacity_kwh

    def _project_sunrise_soc(self, soc_pct: float, site_net_hourly: Dict[int, float], sunset_calc, tznow: pd.Timestamp) -> float:
        try:
            log.info(f"Starting SOC projection: current SOC={soc_pct}%, current hour={tznow.hour}")
            sunrise_hour_raw = sunset_calc.get_sunrise_hour(tznow)
            sunrise_hour = int(round(sunrise_hour_raw))  # Convert to integer hour
            log.info(f"Sunrise hour from calculator: {sunrise_hour_raw} -> rounded to {sunrise_hour}")
            cur_hour = tznow.hour
            net_until = 0.0
            h = cur_hour
            loop_count = 0
            max_loops = 24  # Safety counter to prevent infinite loop

            log.info(f"Starting hour-by-hour integration from hour {h} to sunrise hour {sunrise_hour}")
            # integrate net energy hour-by-hour until sunrise
            while h != sunrise_hour and loop_count < max_loops:
                net_energy = site_net_hourly.get(h, 0.0)
                net_until += net_energy
                log.info(f"Hour {h}: net_energy={net_energy:.3f}kWh, cumulative={net_until:.3f}kWh")
                h = (h + 1) % 24
                loop_count += 1

            if loop_count >= max_loops:
                log.warning(f"Loop limit reached ({max_loops}) in SOC projection - possible infinite loop")
                log.warning(f"Current hour: {cur_hour}, Sunrise hour: {sunrise_hour}, Final hour: {h}")
                return soc_pct  # Return current SOC as fallback

            log.info(f"Hour-by-hour integration completed: {loop_count} hours, total net energy={net_until:.3f}kWh")

            batt_kwh = self.fc.batt_capacity_kwh
            log.info(f"Battery capacity: {batt_kwh}kWh")
            projected = soc_pct + (net_until / batt_kwh * 100.0 if batt_kwh > 0 else 0.0)
            final_projected = max(0.0, min(100.0, projected))
            log.info(f"SOC projection completed: {soc_pct}% + {net_until/batt_kwh*100:.1f}% = {final_projected:.1f}%")
            return final_projected
        except Exception as e:
            log.warning(f"SOC projection failed: {e}, returning current SOC: {soc_pct}%")
            return soc_pct

    def _detect_grid_availability(self, telemetry, tznow: pd.Timestamp, soc_pct: float, effective_min_soc: float) -> bool:
        """
        Detect grid availability from telemetry data with hysteresis to prevent flicker issues.
        Based on inverter specifications, check grid power and inverter mode.
        """
        if not telemetry:
            return self._last_grid_availability  # Return last known state

        # Get raw grid availability from telemetry
        raw_grid_available = self._get_raw_grid_availability(telemetry, tznow, soc_pct, effective_min_soc)

        # Apply hysteresis logic to get the actual grid availability
        grid_available = self._apply_grid_availability_hysteresis(raw_grid_available)

        # Log the grid availability detection for debugging
        # Handle both Telemetry objects and dictionaries
        if hasattr(telemetry, 'inverter_mode'):
            inverter_mode = telemetry.inverter_mode
        elif isinstance(telemetry, dict):
            inverter_mode = telemetry.get('inverter_mode', 'Unknown')
        else:
            inverter_mode = 'Unknown'
        
        log.info(f"Grid availability: {grid_available} (raw: {raw_grid_available}, inverter_mode: {inverter_mode})")

        return grid_available

    def _get_raw_grid_availability(self, telemetry, tznow: pd.Timestamp, soc_pct: float, effective_min_soc: float) -> bool:
        """Get raw grid availability from telemetry without hysteresis."""
        # Method 1: Check inverter mode (primary method)
        # Check both string and numeric representations
        # Handle both Telemetry objects and dictionaries
        if hasattr(telemetry, 'inverter_mode'):
            inverter_mode = telemetry.inverter_mode
        elif isinstance(telemetry, dict):
            inverter_mode = telemetry.get('inverter_mode')
        else:
            inverter_mode = None
        if inverter_mode is not None:
            # String mode names (examples seen: 'OnGrid mode', 'OffGrid mode', 'Time-based control')
            if isinstance(inverter_mode, str):
                # Treat explicit OffGrid as grid absent
                if 'OffGrid' in inverter_mode or 'Off Grid' in inverter_mode:
                    return False
                # For any other known/non-empty mode string, assume grid present
                # This avoids misclassifying self-use/time-based with zero grid power as grid-absent
                if inverter_mode.strip() != '':
                    return True
            # Numeric mode values (0x03 = OnGrid, 0x04 = OffGrid)
            elif isinstance(inverter_mode, (int, float)):
                if inverter_mode == 0x04 or inverter_mode == 4:  # OffGrid mode
                    return False
                # Any other numeric code -> assume grid present
                return True

        # Method 2: Check grid power from telemetry
        # Look for grid power indicators (Phase R/S/T watt of grid from specs 0x1300-0x1304)
        grid_power_indicators = [
            'phase_r_watt_of_grid', 'phase_s_watt_of_grid', 'phase_t_watt_of_grid',
            'grid_power', 'grid_watt', 'grid_power_w'
        ]

        for indicator in grid_power_indicators:
            # Handle both Telemetry objects and dictionaries
            if isinstance(telemetry, dict) and indicator in telemetry:
                grid_power = telemetry[indicator]
                if grid_power is not None and abs(grid_power) > 10:  # Grid power > 10W indicates grid available
                    return True
            elif hasattr(telemetry, indicator):
                grid_power = getattr(telemetry, indicator)
                if grid_power is not None and abs(grid_power) > 10:  # Grid power > 10W indicates grid available
                    return True

        # Method 3: Check for grid voltage indicators
        grid_voltage_indicators = [
            'phase_a_voltage', 'phase_b_voltage', 'phase_c_voltage',
            'grid_voltage', 'l1_n_phase_voltage_of_grid', 'l2_n_phase_voltage_of_grid', 'l3_n_phase_voltage_of_grid'
        ]

        for indicator in grid_voltage_indicators:
            # Handle both Telemetry objects and dictionaries
            if isinstance(telemetry, dict) and indicator in telemetry:
                grid_voltage = telemetry[indicator]
            elif hasattr(telemetry, indicator):
                grid_voltage = getattr(telemetry, indicator)
            else:
                continue
                
                if grid_voltage is not None and grid_voltage > 100:  # Grid voltage > 100V indicates grid available
                    return True

        # Method 4: Check for grid frequency
        # Handle both Telemetry objects and dictionaries
        if hasattr(telemetry, 'extra'):
            grid_frequency = telemetry.extra.get('frequency_of_grid')
        elif isinstance(telemetry, dict):
            grid_frequency = telemetry.get('frequency_of_grid')
        else:
            grid_frequency = None
            
        if grid_frequency is not None and 45 <= grid_frequency <= 65:  # Normal grid frequency range
            return True

        # Default: assume grid is available if we can't determine otherwise
        # This is safer for preventing blackouts
        return True

    def _apply_grid_availability_hysteresis(self, raw_grid_available: bool) -> bool:
        """
        Apply hysteresis to grid availability detection to prevent brief flickers.

        Args:
            raw_grid_available: Raw grid availability from telemetry

        Returns:
            Grid availability with hysteresis applied
        """
        import time
        current_time = time.time()

        # Add current reading to history
        self._grid_availability_history.append((current_time, raw_grid_available))

        # Clean old history (keep only last 30 seconds)
        cutoff_time = current_time - 30
        self._grid_availability_history = [
            (ts, available) for ts, available in self._grid_availability_history
            if ts > cutoff_time
        ]

        # If we have enough history, analyze patterns
        if len(self._grid_availability_history) >= self._grid_hysteresis_threshold:
            # Check for consistent readings
            recent_readings = self._grid_availability_history[-self._grid_hysteresis_threshold:]
            consistent_available = all(available for _, available in recent_readings)
            consistent_unavailable = all(not available for _, available in recent_readings)

            # If we have consistent readings different from last confirmed state, update
            if consistent_available and not self._last_grid_availability:
                # Grid has been consistently available - confirm change
                self._last_grid_availability = True
                self._grid_availability_confidence = 1.0
                log.info("Grid availability confirmed: AVAILABLE (hysteresis cleared)")

            elif consistent_unavailable and self._last_grid_availability:
                # Grid has been consistently unavailable - confirm change
                self._last_grid_availability = False
                self._grid_availability_confidence = 1.0
                log.warning("Grid availability confirmed: UNAVAILABLE (hysteresis cleared)")

            # Check for flickering (rapid changes)
            if len(self._grid_availability_history) >= 6:
                recent_6 = self._grid_availability_history[-6:]
                changes = sum(1 for i in range(1, len(recent_6))
                            if recent_6[i][1] != recent_6[i-1][1])

                if changes >= 3:  # 3 or more changes in 6 readings indicates flickering
                    self._grid_availability_confidence = max(0.3, self._grid_availability_confidence - 0.2)
                    log.warning(f"Grid flickering detected ({changes} changes in 6 readings) - confidence: {self._grid_availability_confidence:.2f}")

        # For self-sufficiency optimization, be more aggressive about switching to battery
        # If grid indicators are weak/erratic, switch to battery mode if SOC is sufficient
        if (self._grid_availability_confidence < 0.5 and
            self._last_grid_availability and
            raw_grid_available):  # Raw shows available but confidence is low

            # Check if we should switch to battery mode for self-sufficiency
            # This would require SOC information, but for now just log the condition
            log.info(f"Grid availability confidence low ({self._grid_availability_confidence:.2f}) - considering battery mode for self-sufficiency")

        return self._last_grid_availability

    def _collect_daily_performance_data(self, tznow: pd.Timestamp, soc_pct: float,
                                      telemetry: Dict[str, Any], site_pv_hourly: Dict[int, float],
                                      site_load_hourly: Dict[int, float], sunset_hour: float, sunrise_hour: float):
        """Collect daily performance data for backtesting."""
        try:
            current_date = tznow.strftime('%Y-%m-%d')

            # Initialize daily data if new day
            if current_date not in self._daily_performance_data:
                self._daily_performance_data[current_date] = {
                    'soc_at_sunset': None,
                    'soc_at_sunrise': None,
                    'grid_kwh': 0.0,
                    'night_load_kwh': 0.0,
                    'outage_events': 0,
                    'forecast_accuracy': 1.0,
                    'night_load_variability': 0.0,
                    'battery_capacity_kwh': self.fc.batt_capacity_kwh,
                    'soc_readings': []
                }

            # Collect SOC readings throughout the day
            self._daily_performance_data[current_date]['soc_readings'].append({
                'time': tznow.hour,
                'soc': soc_pct
            })

            # Track SOC at sunset (dynamic time)
            sunset_window_start = int(sunset_hour - 0.5)  # 30 minutes before sunset
            sunset_window_end = int(sunset_hour + 0.5)    # 30 minutes after sunset

            if (sunset_window_start <= tznow.hour <= sunset_window_end and
                self._daily_performance_data[current_date]['soc_at_sunset'] is None):
                self._daily_performance_data[current_date]['soc_at_sunset'] = soc_pct
                log.info(f"Recorded SOC at sunset ({sunset_hour:.1f}): {soc_pct:.1f}%")

            # Track SOC at sunrise (dynamic time)
            sunrise_window_start = int(sunrise_hour - 0.5)  # 30 minutes before sunrise
            sunrise_window_end = int(sunrise_hour + 0.5)    # 30 minutes after sunrise

            if (sunrise_window_start <= tznow.hour <= sunrise_window_end and
                self._daily_performance_data[current_date]['soc_at_sunrise'] is None):
                self._daily_performance_data[current_date]['soc_at_sunrise'] = soc_pct
                log.info(f"Recorded SOC at sunrise ({sunrise_hour:.1f}): {soc_pct:.1f}%")

            # Track grid usage
            # Handle both Telemetry objects and dictionaries
            if hasattr(telemetry, 'grid_power_w'):
                grid_power = telemetry.grid_power_w or 0
            elif isinstance(telemetry, dict):
                grid_power = telemetry.get('grid_power_w', 0)
            else:
                grid_power = 0
                
            if grid_power > 0:  # Grid import
                self._daily_performance_data[current_date]['grid_kwh'] += grid_power / 1000.0 / 12.0  # Convert to kWh (assuming 5-minute intervals)

            # Track forecast accuracy
            self._track_forecast_accuracy(tznow, telemetry, site_pv_hourly, site_load_hourly)

            # Calculate night load (sunset to sunrise)

            if tznow.hour >= sunset_hour or tznow.hour <= sunrise_hour:
                current_load = site_load_hourly.get(tznow.hour, 0)
                self._daily_performance_data[current_date]['night_load_kwh'] += current_load / 12.0  # Convert to kWh

            # Track outage events with cause classification
            if not self._last_grid_availability and grid_power < 10:
                # Potential outage event - classify cause
                outage_type, cause = self.reliability.classify_outage_cause(telemetry, 1)  # Assume 1 minute for now
                self._daily_performance_data[current_date]['outage_events'] += 1

                # Record outage event with classification
                from solarhub.timezone_utils import now_configured
                self.reliability.record_outage_event(
                    now_configured(), 1, cause, outage_type
                )

                # Get equipment diagnostics for internal outages
                if outage_type == "internal":
                    diagnostics = self.reliability.get_equipment_diagnostics(tznow.hour)
                    if diagnostics["equipment_health"] != "good":
                        log.warning(f"Equipment diagnostics: {diagnostics['equipment_health']} - {diagnostics['recommendations']}")

        except Exception as e:
            log.warning(f"Failed to collect daily performance data: {e}")

    def _track_forecast_accuracy(self, tznow: pd.Timestamp, telemetry,
                               site_pv_hourly: Dict[int, float], site_load_hourly: Dict[int, float]):
        """Track forecast accuracy for PV and load predictions."""
        try:
            current_hour = tznow.hour

            # Get actual PV production (from telemetry)
            # Handle both Telemetry objects and dictionaries
            if hasattr(telemetry, 'pv_power_w'):
                actual_pv = (telemetry.pv_power_w or 0) / 1000.0  # Convert to kW
            elif isinstance(telemetry, dict):
                actual_pv = telemetry.get('pv_power_w', 0) / 1000.0  # Convert to kW
            else:
                actual_pv = 0

            # Get actual load (from telemetry)
            if hasattr(telemetry, 'load_power_w'):
                actual_load = (telemetry.load_power_w or 0) / 1000.0  # Convert to kW
            elif isinstance(telemetry, dict):
                actual_load = telemetry.get('load_power_w', 0) / 1000.0  # Convert to kW
            else:
                actual_load = 0

            # Get forecasted values for current hour
            forecasted_pv = site_pv_hourly.get(current_hour, 0)
            forecasted_load = site_load_hourly.get(current_hour, 0)

            # Calculate accuracy ratios (avoid division by zero)
            if forecasted_pv > 0:
                pv_accuracy = min(actual_pv / forecasted_pv, 2.0)  # Cap at 200% to avoid extreme outliers
                self._forecast_accuracy_history['pv_accuracy'].append(pv_accuracy)

            if forecasted_load > 0:
                load_accuracy = min(actual_load / forecasted_load, 2.0)  # Cap at 200% to avoid extreme outliers
                self._forecast_accuracy_history['load_accuracy'].append(load_accuracy)

            # Keep only recent accuracy data (last week)
            for key in self._forecast_accuracy_history:
                if len(self._forecast_accuracy_history[key]) > self._forecast_accuracy_window:
                    self._forecast_accuracy_history[key] = self._forecast_accuracy_history[key][-self._forecast_accuracy_window:]

            # Log accuracy periodically (every hour)
            if tznow.minute < 5:  # Log once per hour
                avg_pv_accuracy = sum(self._forecast_accuracy_history['pv_accuracy']) / len(self._forecast_accuracy_history['pv_accuracy']) if self._forecast_accuracy_history['pv_accuracy'] else 1.0
                avg_load_accuracy = sum(self._forecast_accuracy_history['load_accuracy']) / len(self._forecast_accuracy_history['load_accuracy']) if self._forecast_accuracy_history['load_accuracy'] else 1.0

                log.info(f"Forecast accuracy - PV: {avg_pv_accuracy:.2f}, Load: {avg_load_accuracy:.2f} (samples: {len(self._forecast_accuracy_history['pv_accuracy'])})")

        except Exception as e:
            log.warning(f"Failed to track forecast accuracy: {e}")

    def _get_forecast_uncertainty_from_accuracy(self) -> Dict[str, str]:
        """Get forecast uncertainty assessment based on historical accuracy."""
        try:
            pv_accuracies = self._forecast_accuracy_history['pv_accuracy']
            load_accuracies = self._forecast_accuracy_history['load_accuracy']

            if not pv_accuracies or not load_accuracies:
                return {'pv_confidence': 'medium', 'load_confidence': 'medium'}

            # Calculate coefficient of variation (CV) for accuracy
            def calculate_cv(values):
                if not values:
                    return 0.0
                mean_val = sum(values) / len(values)
                if mean_val == 0:
                    return 0.0
                variance = sum((x - mean_val) ** 2 for x in values) / len(values)
                std_dev = variance ** 0.5
                return std_dev / mean_val

            pv_cv = calculate_cv(pv_accuracies)
            load_cv = calculate_cv(load_accuracies)

            # Classify confidence based on CV
            def classify_confidence(cv):
                if cv < 0.2:
                    return 'high'
                elif cv < 0.4:
                    return 'medium'
                else:
                    return 'low'

            pv_confidence = classify_confidence(pv_cv)
            load_confidence = classify_confidence(load_cv)

            return {
                'pv_confidence': pv_confidence,
                'load_confidence': load_confidence,
                'pv_cv': pv_cv,
                'load_cv': load_cv
            }

        except Exception as e:
            log.warning(f"Failed to calculate forecast uncertainty from accuracy: {e}")
            return {'pv_confidence': 'medium', 'load_confidence': 'medium'}


    def _run_daily_backtest_if_needed(self, tznow: pd.Timestamp):
        """Run daily backtest if it's a new day and we have sufficient data."""
        try:
            current_date = tznow.strftime('%Y-%m-%d')

            # Only run backtest once per day
            if self._last_backtest_date == current_date:
                return

            # Only run backtest in the morning (after sunrise data is collected)
            if tznow.hour < 8:
                return

            # Check if we have data for yesterday
            yesterday = (tznow - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            if yesterday not in self._daily_performance_data:
                log.info(f"No performance data available for {yesterday}, skipping backtest")
                return

            # Get yesterday's performance data
            daily_data = self._daily_performance_data[yesterday]

            # Ensure we have required data
            if (daily_data['soc_at_sunset'] is None or
                daily_data['soc_at_sunrise'] is None):
                log.info(f"Incomplete data for {yesterday}, skipping backtest")
                return

            # Run backtest
            log.info(f"Running daily backtest for {yesterday}")
            backtest_results = self.backtest.run_daily_backtest(
                datetime.strptime(yesterday, '%Y-%m-%d'),
                daily_data
            )

            # Analyze performance trends and auto-tune if needed
            analysis = self.backtest.analyze_performance_trends()
            if analysis.get('status') == 'analysis_complete':
                recommendation = analysis.get('recommendation', {})
                if recommendation.get('action') == 'tune_parameters':
                    log.info(f"Auto-tuning parameters: {recommendation.get('reason')}")
                    success = self.backtest.auto_tune_parameters(recommendation)
                    if success:
                        log.info("Parameters auto-tuned successfully")
                    else:
                        log.warning("Failed to auto-tune parameters")

            # Update last backtest date
            self._last_backtest_date = current_date

            # Clean up old data (keep only last 7 days)
            cutoff_date = (tznow - pd.Timedelta(days=7)).strftime('%Y-%m-%d')
            self._daily_performance_data = {
                date: data for date, data in self._daily_performance_data.items()
                if date >= cutoff_date
            }

        except Exception as e:
            log.error(f"Failed to run daily backtest: {e}")

    def get_grid_availability_status(self) -> Dict[str, Any]:
        """Get current grid availability status for monitoring and logging."""
        return {
            "available": self._last_grid_availability,
            "confidence": self._grid_availability_confidence,
            "history_count": len(self._grid_availability_history),
            "hysteresis_threshold": self._grid_hysteresis_threshold,
            "last_change_time": self._grid_availability_history[-1][0] if self._grid_availability_history else None
        }


    async def tick(self):
        from solarhub.timezone_utils import now_configured
        if not self.hub.cfg.smart.policy.enabled:
            return

        # Enhanced weather forecast with caching and degraded-data fallback
        import time
        current_time = time.time()
        degraded_data_mode = False

        if (self._weather_cache is None or
            self._weather_cache_time is None or
            current_time - self._weather_cache_time > self._cache_ttl_seconds):

            # Get enhanced weather forecast
            try:
                if hasattr(self.weather, 'get_enhanced_forecast'):
                    enhanced_forecast = await self.weather.get_enhanced_forecast(days=2)
                    factors = await self.weather.day_factors()  # For compatibility
                    self._weather_cache = {"factors": factors, "enhanced": enhanced_forecast}
                else:
                    factors = await self.weather.day_factors()
                    self._weather_cache = {"factors": factors, "enhanced": None}

                self._weather_cache_time = current_time

                # Check for degraded data conditions
                degraded_data_mode = self._check_degraded_data_conditions(factors, enhanced_forecast)

            except Exception as e:
                log.warning(f"Weather forecast failed, using degraded-data fallback: {e}")
                degraded_data_mode = True
                factors = self._get_conservative_fallback_factors()
                enhanced_forecast = None
                self._weather_cache = {"factors": factors, "enhanced": None}
            self._weather_cache_time = current_time
        else:
            factors = self._weather_cache["factors"]
            enhanced_forecast = self._weather_cache.get("enhanced")

            # Re-check degraded data conditions even with cached data
            degraded_data_mode = self._check_degraded_data_conditions(factors, enhanced_forecast)

        if degraded_data_mode:
            log.warning("DEGRADED-DATA FALLBACK: Using conservative planning due to poor forecast quality")
            # Apply conservative adjustments to factors
            factors = self._apply_conservative_adjustments(factors)

        # Enhanced SOC logging with frequency control
        self._log_soc_with_mode_correlation()

        from solarhub.timezone_utils import now_configured
        tznow = pd.Timestamp(now_configured())
        doy = int(tznow.dayofyear)
        dow = int(tznow.dayofweek)

        # Calculate sunset and sunrise hours once at the beginning
        sunset_hour = self.sunset_calc.get_sunset_hour(tznow)
        sunrise_hour = self.sunset_calc.get_sunrise_hour(tznow)
        log.info(f"Sunset: {sunset_hour:.1f}, Sunrise: {sunrise_hour:.1f}")

        # PV kWh per inverter today/tomorrow with enhanced weather
        log.info("=== SOLAR FORECASTING CALCULATIONS ===")
        log.info(f"Weather factors: {factors}")
        log.info(f"Enhanced forecast available: {enhanced_forecast is not None}")

        # Filter inverters by array_id if scheduler is scoped to an array
        array_inverters = [rt for rt in self.hub.inverters 
                          if not self.array_id or getattr(rt.cfg, 'array_id', None) == self.array_id]
        
        if self.array_id and not array_inverters:
            log.warning(f"No inverters found for array {self.array_id} in scheduler")
            return
        
        # Check if weather factor seems too low based on actual conditions
        # Get current actual solar for weather factor adjustment
        try:
            current_actual_pv = 0.0
            for rt in array_inverters:
                rt_tel = rt.adapter.last_tel
                if rt_tel:
                    # Get PV power from Telemetry object attributes
                    pv_power = 0.0
                    if isinstance(rt_tel, dict):
                        pv_power = float(rt_tel.get('pv_power_w', 0) or 0)
                        if pv_power == 0:
                            extra_data = rt_tel.get('extra') or {}
                            for pv_key in ["pv_power", "pv_power_w", "PV_Power"]:
                                if pv_key in extra_data and extra_data[pv_key] is not None:
                                    pv_power = float(extra_data[pv_key])
                                    break
                    else:
                        if getattr(rt_tel, 'pv_power_w', None) is not None:
                            pv_power = float(rt_tel.pv_power_w)
                        elif hasattr(rt_tel, 'extra') and rt_tel.extra:
                            # Try extra fields if main field is not available
                            for pv_key in ["pv_power", "pv_power_w", "PV_Power"]:
                                if pv_key in rt_tel.extra and rt_tel.extra[pv_key] is not None:
                                    pv_power = float(rt_tel.extra[pv_key])
                                    break

                    current_actual_pv += pv_power

            log.info(f"Current actual PV generation: {current_actual_pv:.0f}W")
        except Exception as e:
            log.warning(f"Failed to adjust weather factor based on actual solar: {e}")

        per_today, per_tomorrow = {}, {}
        for rt in array_inverters:
            total_today = 0.0
            total_tom = 0.0
            
            # Get enhanced weather data for today and tomorrow
            today_weather = None
            tomorrow_weather = None
            
            if enhanced_forecast:
                today_str = tznow.strftime('%Y-%m-%d')
                tomorrow_str = (tznow + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                today_weather = enhanced_forecast.get(today_str)
                tomorrow_weather = enhanced_forecast.get(tomorrow_str)
                log.info(f"Enhanced weather data - Today: {today_weather is not None}, Tomorrow: {tomorrow_weather is not None}")
            
            for i, est in enumerate(self.inv_estimators[rt.cfg.id]):
                # Use enhanced weather data if available
                today_kwh = await est.estimate_daily_pv_kwh(
                    factors["today"], enhanced_weather=today_weather)
                tomorrow_kwh = await est.estimate_daily_pv_kwh(
                    factors["tomorrow"], enhanced_weather=tomorrow_weather)
                
                log.info(f"Estimator {i+1} for {rt.cfg.id}: Today={today_kwh:.2f}kWh, Tomorrow={tomorrow_kwh:.2f}kWh (factor: {factors['today']:.3f}/{factors['tomorrow']:.3f})")
                
                total_today += today_kwh
                total_tom += tomorrow_kwh
            
            per_today[rt.cfg.id] = round(total_today, 2)
            per_tomorrow[rt.cfg.id] = round(total_tom, 2)
            log.info(f"Total forecast for {rt.cfg.id}: Today={per_today[rt.cfg.id]}kWh, Tomorrow={per_tomorrow[rt.cfg.id]}kWh")
        
        # Check actual daily generation and adjust forecast if needed
        try:
            from solarhub.timezone_utils import now_configured
            tznow = pd.Timestamp(now_configured())
            
            # Get actual daily generation directly from inverter telemetry
            actual_daily_kwh = 0.0
            current_pv_w = 0.0
            
            # Get daily energy from inverter telemetry
            for rt in array_inverters:
                # Prefer adapter's cached last_tel (dict of flat keys)
                last_tel = None
                try:
                    if hasattr(rt, 'adapter') and hasattr(rt.adapter, 'last_tel'):
                        last_tel = rt.adapter.last_tel
                except Exception:
                    last_tel = None
                
                if last_tel:
                    # Try to get daily energy from extra data if available
                    if last_tel.extra:
                        daily_energy_keys = ['today_energy', 'daily_energy', 'today_pv_energy', 'pv_daily_energy']
                        for key in daily_energy_keys:
                            if key in last_tel.extra and last_tel.extra[key] is not None:
                                # Convert from Wh to kWh if needed
                                daily_energy = float(last_tel.extra[key])
                            if daily_energy > 1000:  # Likely in Wh, convert to kWh
                                daily_energy = daily_energy / 1000.0
                            actual_daily_kwh += daily_energy
                            log.info(f"Found daily energy for {rt.cfg.id}: {daily_energy:.2f}kWh from key '{key}'")
                            break
                    
                    # Get current PV power for curve analysis
                    # First try the main telemetry field
                    if last_tel.pv_power_w is not None:
                        current_pv_w += float(last_tel.pv_power_w)
                    elif last_tel.extra:
                        # Try extra fields - prefer standardized IDs
                        pv_keys = ['pv1_power_w', 'pv2_power_w', 'mppt1_power_w', 'mppt2_power_w', 'mppt1_power', 'mppt2_power', 'pv_power_w', 'pv_power', 'PV_Power']
                        for key in pv_keys:
                            if key in last_tel.extra and last_tel.extra[key] is not None:
                                current_pv_w += float(last_tel.extra[key])
                            break
                        
        except Exception as e:
            log.warning(f"Failed to get actual daily generation from inverter: {e}")
        
        total_today_kwh = sum(per_today.values())
        total_tomorrow_kwh = sum(per_tomorrow.values())
        log.info(f"Actual daily solar from inverter: {actual_daily_kwh:.2f}kWh")
        log.info(f"Site total solar forecast: Today={total_today_kwh:.2f}kWh, Tomorrow={total_tomorrow_kwh:.2f}kWh")

        # Hourly PV (kWh)
        # ---- Hourly PV via clearsky POA (sunrise->sunset), scaled to daily forecast ----
        # For each inverter: build hourly shape weights (sum=1), then multiply by its daily kWh
        log.info("=== HOURLY SOLAR FORECASTING ===")
        hours = list(range(24))
        hourly_pv_by_inv: Dict[str, Dict[int, float]] = {}

        for rt in array_inverters:
            # physics-based shape today
            shape = self._hourly_shape_today(self.inv_estimators[rt.cfg.id], tznow)
            if not shape:
                log.info(f"Physics-based shape not available for {rt.cfg.id}, using learned bias")
                # Use hybrid approach combining recent and seasonal data
                cache_key = f"{rt.cfg.id}_{tznow.dayofyear}"
                if cache_key not in self._bias_cache:
                    prof = self.bias.hourly_pv_profile_hybrid(
                        rt.cfg.id, tznow.dayofyear, recent_days=60, seasonal_years=3
                    )
                    self._bias_cache[cache_key] = prof
                    log.info(f"Generated new bias profile for {rt.cfg.id} (DOY: {tznow.dayofyear})")
                else:
                    prof = self._bias_cache[cache_key]
                    log.info(f"Using cached bias profile for {rt.cfg.id}")
                # normalize profile to weights
                s = sum(max(0.0, prof.get((tznow.dayofweek, h), 0.0)) for h in hours)
                if s <= 0:
                    log.warning(f"No valid bias data for {rt.cfg.id}, using cosine fallback")
                    # last-resort: gentle cosine-like bump across mid-day
                    shape = {h: max(0.0, 1 - ((h - 12) / 6) ** 2) for h in hours}
                    ss = sum(shape.values())
                    shape = {h: (v / ss if ss > 0 else 0.0) for h, v in shape.items()}
                else:
                    shape = {h: max(0.0, prof.get((tznow.dayofweek, h), 0.0)) / s for h in hours}
            else:
                log.info(f"Using physics-based shape for {rt.cfg.id}")

            # scale weights by forecast daily energy (kWh)
            daily_kwh = per_today[rt.cfg.id]  # from earlier daily forecast by estimator
            hourly_kwh = {h: round(daily_kwh * shape.get(h, 0.0), 4) for h in hours}
            hourly_pv_by_inv[rt.cfg.id] = hourly_kwh
            
            # Log some key hourly values (dynamic solar-peak hours)
            current_hour = tznow.hour
            current_hourly = hourly_kwh.get(current_hour, 0)
            # Determine dynamic peak solar hours from forecast (top 60% of daylight hours)
            pv_by_hour = sorted(hourly_kwh.items(), key=lambda x: x[1], reverse=True)
            peak_hours_count = max(1, int(len(hours) * 0.6))
            dynamic_peak_hours = sorted([h for h, _ in pv_by_hour[:peak_hours_count]])
            peak_hourly = [hourly_kwh.get(h, 0) for h in dynamic_peak_hours]
            log.info(f"Hourly solar for {rt.cfg.id}: Current hour {current_hour}: {current_hourly:.3f}kWh")
            log.info(f"Dynamic solar-peak hours {dynamic_peak_hours}: {[f'{h:.3f}' for h in peak_hourly]} kWh")

            # Array/Site PV per hour (kWh) - use array_pv_hourly when scoped to array, site_pv_hourly for legacy
        array_pv_hourly = {h: round(sum(hourly_pv_by_inv[i].get(h, 0.0) for i in hourly_pv_by_inv), 4) for h in
                              hours}
        site_pv_hourly = array_pv_hourly  # Alias for backward compatibility
        array_pv_today_kwh = round(sum(array_pv_hourly.values()), 3)
        site_pv_today_kwh = array_pv_today_kwh  # Alias for backward compatibility
        
        # Log array/site totals (dynamic solar-peak hours)
        current_hour = tznow.hour
        current_array_hourly = array_pv_hourly.get(current_hour, 0)
        array_pv_by_hour = sorted(array_pv_hourly.items(), key=lambda x: x[1], reverse=True)
        array_peak_hours_count = max(1, int(len(array_pv_hourly) * 0.6))
        array_dynamic_peak_hours = sorted([h for h, _ in array_pv_by_hour[:array_peak_hours_count]])
        peak_array_hourly = [array_pv_hourly.get(h, 0) for h in array_dynamic_peak_hours]
        log_prefix = f"Array {self.array_id}" if self.array_id else "Site"
        log.info(f"{log_prefix} hourly solar: Current hour {current_hour}: {current_array_hourly:.3f}kWh")
        log.info(f"{log_prefix} dynamic solar-peak hours {array_dynamic_peak_hours}: {[f'{h:.3f}' for h in peak_array_hourly]} kWh")
        log.info(f"Total {log_prefix.lower()} daily solar: {array_pv_today_kwh:.3f}kWh")

        # Hourly load (kWh) with hybrid caching
        log.info("=== LOAD FORECASTING ===")
        load_cache_key = f"load_{doy}_{dow}"
        if load_cache_key not in self._load_cache:
            load_prof = self.load.hourly_load_profile_hybrid(
                doy, dow, recent_days=60, seasonal_years=3
            )
            self._load_cache[load_cache_key] = load_prof
            log.info(f"Generated new load profile for DOY: {doy}, DOW: {dow}")
        else:
            load_prof = self._load_cache[load_cache_key]
            log.info(f"Using cached load profile for DOY: {doy}, DOW: {dow}")
        
        fallback_kw = getattr(self.hub.cfg.smart.policy, "load_fallback_kw", 1.0)
        site_load_hourly = self.load.hourly_for_day(load_prof, dow, fallback_kw=fallback_kw)
        
        # Log load forecast details
        current_hour = tznow.hour
        # Determine dynamic peak load hours (top-N load hours, e.g., top 5)
        load_by_hour = sorted(site_load_hourly.items(), key=lambda x: x[1], reverse=True)
        dynamic_peak_load_hours = sorted([h for h, _ in load_by_hour[:5]])
        current_load = site_load_hourly.get(current_hour, 0)
        peak_loads = [site_load_hourly.get(h, 0) for h in dynamic_peak_load_hours]
        total_daily_load = sum(site_load_hourly.values())
        
        log.info(f"Load forecast: Current hour {current_hour}: {current_load:.3f}kW")
        log.info(f"Dynamic peak load hours {dynamic_peak_load_hours}: {[f'{h:.3f}' for h in peak_loads]} kW")
        log.info(f"Total daily load: {total_daily_load:.3f}kWh")
        log.info(f"Load fallback kW: {fallback_kw}")

        # Net hourly (array PV - site load, or array PV - array load if per-array load is configured)
        array_net_hourly = {h: array_pv_hourly[h] - site_load_hourly[h] for h in hours}
        site_net_hourly = array_net_hourly  # Alias for backward compatibility
        # Fix: net_until should only sum from current hour to deadline, not from hour 0
        current_hour = tznow.hour
        net_until = lambda end_h: sum(v for h,v in site_net_hourly.items() if current_hour <= h <= end_h)

        # Log net energy calculations
        log.info("=== NET ENERGY CALCULATIONS ===")
        current_net = site_net_hourly.get(current_hour, 0)
        peak_net_hours = [10, 11, 12, 13, 14, 15]  # Peak solar hours
        peak_nets = [site_net_hourly.get(h, 0) for h in peak_net_hours]
        log.info(f"Net energy: Current hour {current_hour}: {current_net:.3f}kWh")
        log.info(f"Peak hours net (10-15): {[f'{h:.3f}' for h in peak_nets]} kWh")

        # Current SOC from adapter cache
        try:
            adapter = self.hub.inverters[0].adapter
            last_tel = adapter.last_tel  # Telemetry object
            log.info(f"Telemetry data type: {type(last_tel)}")
            log.info(f"Telemetry data available: {last_tel is not None}")
            if last_tel:
                # Access Telemetry object attributes directly
                log.info(f"Telemetry fields: {list(last_tel.__dict__.keys())}")
                log.info(f"Telemetry sample: SOC={last_tel.batt_soc_pct}, PV={last_tel.pv_power_w}, Load={last_tel.load_power_w}")
            else:
                log.warning("Telemetry data is empty - this will cause grid detection issues")
                log.warning(f"Adapter object: {adapter}")
                log.warning(f"Adapter has last_tel attribute: {hasattr(adapter, 'last_tel')}")
                # Try to get fresh telemetry data as fallback
                try:
                    log.info("Attempting to get fresh telemetry data...")
                    fresh_tel = await adapter.read_all_registers()
                    if fresh_tel:
                        last_tel = fresh_tel
                        log.info("Successfully retrieved fresh telemetry data")
                    else:
                        log.warning("Fresh telemetry data is also empty")
                except Exception as fresh_e:
                    log.warning(f"Failed to get fresh telemetry data: {fresh_e}")
        except Exception as e:
            log.warning(f"Failed to get telemetry data: {e}")
            last_tel = None
        
        soc_pct = float(last_tel.batt_soc_pct) if last_tel and last_tel.batt_soc_pct is not None else 0.0
        soc_kwh = self._energy_in_battery_kwh(soc_pct)

        # === UNIFIED CHARGING PLAN CALCULATION (CALCULATED ONCE) ===
        # Calculate all TOU windows, energy requirements, and solar assessments in one place
        log.info("=== UNIFIED CHARGING PLAN CALCULATION ===")
        
        # Basic parameters
        sunset_h = int(self.sunset_calc.get_sunset_hour(tznow))
        sunrise_h = int(self.sunset_calc.get_sunrise_hour(tznow))
        pol = self.hub.cfg.smart.policy
        
        # Policy parameters
        target_full_before_sunset = bool(getattr(pol, "target_full_before_sunset", True))
        overnight_min = int(getattr(pol, "overnight_min_soc_pct", 10))
        blackout_reserve_pct = int(getattr(pol, "blackout_reserve_soc_pct", overnight_min))
        tomorrow_pv_kwh = round(sum(per_tomorrow.values()), 2)
        batt_kwh = float(self.fc.batt_capacity_kwh)
        max_charge_power_w = getattr(pol, 'max_charge_power_w', 3000)
        max_discharge_power_w = getattr(pol, 'max_discharge_power_w', 5000)

        # SOC target calculation
        end_soc_target_pct = int(getattr(pol, "max_battery_soc_pct")) if target_full_before_sunset else 98
        tomorrow_ratio = tomorrow_pv_kwh / batt_kwh
        if tomorrow_ratio < 0.5:
            end_soc_target_pct = max(end_soc_target_pct, overnight_min + 10)
        charge_target_soc_pct = end_soc_target_pct
        end_soc_target_kwh = self._energy_in_battery_kwh(charge_target_soc_pct)
        
        # Calculate effective minimum SOC for discharge decisions
        effective_min_soc = max(overnight_min, blackout_reserve_pct)
        
        # Grid availability detection from telemetry and inverter registers with hysteresis
        grid_available = self._detect_grid_availability(last_tel, tznow, soc_pct, effective_min_soc)
        
        # Get unified charging plan (CALCULATED ONCE - NO DUPLICATES)
        unified_plan = self._calculate_unified_charging_plan(
            tznow=tznow,
            site_pv_hourly=site_pv_hourly,
            site_load_hourly=site_load_hourly,
            soc_pct=soc_pct,
            batt_kwh=batt_kwh,
            max_charge_power_w=max_charge_power_w,
            max_discharge_power_w=max_discharge_power_w,
            end_soc_target_pct=end_soc_target_pct,
            effective_min_soc=effective_min_soc,
            sunset_hour=sunset_h,
            sunrise_hour=sunrise_h,
            grid_available=grid_available,
            tariffs=getattr(self, 'tariffs', None)
        )
        
        # Extract all calculated values from unified plan (NO DUPLICATE CALCULATIONS)
        energy_reqs = unified_plan['energy_reqs']
        energy_needed_kwh = energy_reqs['energy_needed_kwh']
        solar_assessment = unified_plan['solar_assessment']
        daily_excess_solar_kwh = unified_plan['daily_excess_solar_kwh']
        smart_tou_windows = unified_plan.get('windows', [])
        remaining_solar_hours = unified_plan['remaining_solar_hours']
        required_power_kw = unified_plan['required_power_kw']
        available_power_kw = unified_plan['available_power_kw']
        solar_charge_deadline_h = unified_plan['solar_charge_deadline_h']  # Use from unified plan
        # Short-window override flag must be available to all later steps (caps, TOU, etc.)
        short_window = bool(remaining_solar_hours <= 2) and bool(solar_assessment.get('overall_solar_insufficient', False))
        
        log.info(f"Unified charging plan completed: {len(smart_tou_windows)} windows, "
                f"energy_needed={energy_needed_kwh:.2f}kWh, "
                f"remaining_hours={remaining_solar_hours:.2f}h, "
                f"required_power={required_power_kw:.2f}kW")

        # === GRID CHARGING DECISION (USING UNIFIED PLAN RESULTS) ===
        # Use the solar assessment from unified plan instead of duplicate calculations
        log.info("=== DECISION MAKING ===")
        log.info(f"Current SOC: {soc_pct:.1f}% ({soc_kwh:.3f}kWh)")
        log.info(f"Sunset hour: {sunset_h}")
        log.info(f"Solar-first charge deadline (h): {solar_charge_deadline_h}")
        log.info(f"Charge target SOC: {charge_target_soc_pct}% ({end_soc_target_kwh:.3f}kWh)")
        log.info(f"Tomorrow PV forecast: {tomorrow_pv_kwh:.2f}kWh (ratio: {tomorrow_ratio:.3f})")
        log.info(f"Energy needed: {energy_needed_kwh:.3f}kWh (from unified plan)")
        log.info(f"Daily excess solar: {daily_excess_solar_kwh:.3f}kWh (from unified plan)")
        log.info(f"Solar insufficient: {solar_assessment['overall_solar_insufficient']} (from unified plan)")

        # Grid charging decision based on unified plan assessment
        use_grid = solar_assessment['overall_solar_insufficient'] or energy_needed_kwh > 1.0
        
        # Apply hysteresis using unified plan results
        if self._last_use_grid is not None:
            if self._last_use_grid and energy_needed_kwh < 0.5:
                use_grid = False
            if not self._last_use_grid and energy_needed_kwh < 1.5:
                use_grid = False
        self._last_use_grid = use_grid
        
        log.info(f"Grid charging decision: {use_grid} (solar_insufficient={solar_assessment['overall_solar_insufficient']}, energy_needed={energy_needed_kwh:.2f}kWh)")

        # Post-sunset policy: block non-emergency charging
        if 'force_grid_charge' not in locals():
            force_grid_charge = False
        if tznow.hour >= sunset_h and not force_grid_charge:
            use_grid = False
            log.info("Post-sunset: blocking non-emergency grid charging (emergency overrides only)")

        # Decide charge windows (up to 3) preferring cheap tariff windows, avoiding tariff peak hours
        # Charge windows are now calculated by the unified charging plan
        # No need for separate fallback window creation logic
        charge_windows: List[Tuple[str,str]] = []

        # Discharge protection with night management and emergency grid fallback
        # Explicitly name discharging minimum SOC floor
        eod_soc = max(overnight_min, blackout_reserve_pct)
        discharge_min_soc_pct = eod_soc
        
        # RELIABILITY SYSTEM: Hard 20% SOC constraint with dynamic cushion
        current_hour = tznow.hour
        
        # Assess forecast uncertainty (with accuracy feedback)
        pv_forecast_values = list(site_pv_hourly.values())
        load_forecast_values = list(site_load_hourly.values())
        forecast_uncertainty = self.reliability.assess_forecast_uncertainty(pv_forecast_values, load_forecast_values)
        
        # Override with accuracy-based uncertainty if available
        accuracy_uncertainty = self._get_forecast_uncertainty_from_accuracy()
        if accuracy_uncertainty.get('pv_confidence') != 'medium' or accuracy_uncertainty.get('load_confidence') != 'medium':
            # Create new ForecastUncertainty with accuracy-based confidence
            from solarhub.schedulers.reliability import ForecastUncertainty
            forecast_uncertainty = ForecastUncertainty(
                pv_confidence=accuracy_uncertainty.get('pv_confidence', 'medium'),
                pv_uncertainty_pct=forecast_uncertainty.pv_uncertainty_pct,
                load_confidence=accuracy_uncertainty.get('load_confidence', 'medium'),
                load_uncertainty_pct=forecast_uncertainty.load_uncertainty_pct,
                pv_p75=forecast_uncertainty.pv_p75,
                pv_p90=forecast_uncertainty.pv_p90,
                load_p75=forecast_uncertainty.load_p75,
                load_p90=forecast_uncertainty.load_p90
            )
            log.info(f"Updated forecast uncertainty based on accuracy: PV={forecast_uncertainty.pv_confidence}, Load={forecast_uncertainty.load_confidence}")
        
        # Get effective minimum SOC (20% emergency reserve + dynamic cushion)
        effective_min_soc = self.reliability.get_effective_min_soc(current_hour, forecast_uncertainty)
        
        # Check if key parameters changed that should force command execution
        force_execution = False
        
        # Force execution if cache is older than 1 hour (safety net)
        if (self._last_command_write_ts is not None and 
            (now_configured() - self._last_command_write_ts).total_seconds() > 3600):
            force_execution = True
            log.info("Force execution: cache expired (>1 hour)")
        
        # Force execution if effective_min_soc changed significantly
        if (self._last_effective_min_soc is None or 
            abs(self._last_effective_min_soc - effective_min_soc) > 1.0):  # 1% threshold
            force_execution = True
            log.info(f"Force execution: effective_min_soc changed {self._last_effective_min_soc}% → {effective_min_soc:.1f}%")
            self._last_effective_min_soc = effective_min_soc
        
        # Log grid availability status with hysteresis information
        grid_status = self.get_grid_availability_status()
        log.info(f"Grid availability: {'Available' if grid_available else 'Unavailable'} "
                f"(confidence: {grid_status['confidence']:.2f}, history: {grid_status['history_count']} readings)")
        
        # Get current inverter work mode from telemetry (register 0x2100)
        current_work_mode = InverterManager.get_current_work_mode(last_tel)
        log.info(f"Current inverter work mode: {current_work_mode}")
        
        # Check if work mode changed (force execution if it did)
        if (self._last_work_mode is not None and 
            self._last_work_mode != current_work_mode):
            force_execution = True
            log.info(f"Force execution: work mode changed {self._last_work_mode} → {current_work_mode}")
        self._last_work_mode = current_work_mode
        
        # Get current off-grid mode status (register 0x211C)
        #off_grid_mode_enabled = InverterManager.get_off_grid_mode_status(last_tel)
        #log.info(f"Off-grid mode enabled: {off_grid_mode_enabled}")
        
        # Get off-grid start-up battery capacity (register 0x211F) or use config default
        off_grid_startup_soc = InverterManager.get_off_grid_startup_soc(last_tel)
        config_off_grid_startup_soc = getattr(self.hub.cfg.smart.policy, 'off_grid_startup_soc_pct', 30)
        off_grid_startup_soc = max(off_grid_startup_soc, config_off_grid_startup_soc)  # Use higher of the two
        log.info(f"Off-grid start-up SOC: {off_grid_startup_soc}% (inverter: {InverterManager.get_off_grid_startup_soc(last_tel)}%, config: {config_off_grid_startup_soc}%)")
        
        # Legacy threshold system for backward compatibility (but never below effective_min_soc)
        if grid_available:
            # Grid Available (Conservative Mode): Higher thresholds, consider solar outlook
            emergency_soc_threshold = max(effective_min_soc, getattr(self.hub.cfg.smart.policy, 'emergency_soc_threshold_grid_available_pct', 45))
            critical_soc_threshold = max(effective_min_soc, getattr(self.hub.cfg.smart.policy, 'critical_soc_threshold_grid_available_pct', 35))
            log.info(f"Grid available - using reliability-enhanced thresholds: emergency={emergency_soc_threshold:.1f}%, critical={critical_soc_threshold:.1f}% (effective_min={effective_min_soc:.1f}%)")
        else:
            # Grid Not Available (Must Serve Load): LOWER thresholds to allow more discharge for load
            emergency_soc_threshold = max(effective_min_soc, getattr(self.hub.cfg.smart.policy, 'emergency_soc_threshold_grid_unavailable_pct', 30))
            critical_soc_threshold = max(effective_min_soc, getattr(self.hub.cfg.smart.policy, 'critical_soc_threshold_grid_unavailable_pct', 20))
            log.warning(f"Grid NOT available - using reliability-enhanced load-serving thresholds: emergency={emergency_soc_threshold:.1f}%, critical={critical_soc_threshold:.1f}% (effective_min={effective_min_soc:.1f}%)")
        
        # TELEMETRY CROSS-CHECK: Check for grid instability during risky hours
        grid_instability_detected = False
        current_time = now_configured().timestamp()
        if self.reliability.check_grid_instability(last_tel, current_hour):
            # Only warn if cooldown period has passed
            if current_time - self._last_grid_instability_warning > self._warning_cooldown_seconds:
                log.warning(f"GRID INSTABILITY DETECTED: Switching to protective mode during high-risk hour {current_hour}")
                self._last_grid_instability_warning = current_time
                grid_instability_detected = True
                # Increase dynamic cushion for grid instability
                effective_min_soc = max(effective_min_soc, effective_min_soc + 5.0)  # Extra 5% buffer
                emergency_soc_threshold = max(emergency_soc_threshold, effective_min_soc)
                critical_soc_threshold = max(critical_soc_threshold, effective_min_soc)
            else:
                # Still apply the logic but don't spam the logs
                grid_instability_detected = True
                effective_min_soc = max(effective_min_soc, effective_min_soc + 5.0)
                emergency_soc_threshold = max(emergency_soc_threshold, effective_min_soc)
                critical_soc_threshold = max(critical_soc_threshold, effective_min_soc)
        
        # Log reliability status
        reliability_status = self.reliability.get_reliability_status()
        log.info(f"Reliability status: outage_risk={reliability_status['outage_risk_score']:.2f}, cushion={reliability_status['dynamic_cushion_pct']:.1f}%, forecast_uncertainty={forecast_uncertainty.pv_confidence}/{forecast_uncertainty.load_confidence}, grid_instability={grid_instability_detected}")
        
        # Emergency grid fallback: if SOC is very low, enable grid charging to prevent blackout
        emergency_mode_override = False
        current_soc_kwh = soc_kwh  # Define current_soc_kwh for emergency mode check
        if current_soc_kwh < (batt_kwh * emergency_soc_threshold / 100):
            if grid_available:
                # Grid available: Check solar outlook before enabling grid charging
                solar_quality_score = SolarQualityAssessor.assess_solar_production_quality(site_pv_today_kwh, site_pv_hourly, tznow, tomorrow_pv_kwh, batt_kwh)
                if solar_quality_score < 0.6:  # Poor solar outlook
                    log.warning(f"Emergency grid fallback: SOC {soc_pct:.1f}% below threshold {emergency_soc_threshold}% and poor solar outlook ({solar_quality_score:.2f}) - enabling grid charging")
                    use_grid = True
                    desired_mode = "Time-based control"
                    emergency_mode_override = True
                    log.info("Switching to time-based mode for emergency grid charging")
                else:
                    log.info(f"Emergency SOC threshold reached but good solar outlook ({solar_quality_score:.2f}) - maintaining self-use mode")
            else:
                # Grid not available: More aggressive battery preservation
                log.warning(f"Emergency battery preservation: SOC {soc_pct:.1f}% below threshold {emergency_soc_threshold}% and grid unavailable - increasing discharge limits")
                # Don't switch to grid charging (grid not available), but adjust discharge limits
                emergency_mode_override = True
        
        # Enhanced night management: ensure proper battery usage when SOC is healthy
        night_behavior_override = False
        
        if tznow.hour >= sunset_hour or tznow.hour <= sunrise_hour:  # Night hours (sunset to sunrise)
            night_load_energy = EnergyPlanner.calculate_night_load_energy(tznow, site_load_hourly, self.sunset_calc)
            current_soc_kwh = self._energy_in_battery_kwh(soc_pct)
            # Night glide calculation
            projected_sunrise_soc = self._project_sunrise_soc(soc_pct, site_net_hourly if 'site_net_hourly' in locals() else {}, self.sunset_calc, tznow)
            glide_target = min(100.0, max(effective_min_soc, 20.0) + 2.0)  # 2% safety above effective floor
            action = "glide" if soc_pct > effective_min_soc else "hold"
            log.info(f"NIGHT_DECISION tz={self.tz} h={tznow.hour:02d} eff_min={effective_min_soc:.1f}% proj_sunrise={projected_sunrise_soc:.1f}% action={action} reason=night_glide")
            
            # Use phased discharge power toward glide_target each tick at night
            min_soc_threshold_pct = float(glide_target)
            required_night_soc = night_load_energy + (batt_kwh * effective_min_soc / 100)
            
            # Night battery behavior decision
            if current_soc_kwh >= required_night_soc:
                # SOC is healthy for night - ensure we use battery instead of grid
                log.info(f"Night management: SOC {current_soc_kwh:.2f}kWh healthy for night load {night_load_energy:.2f}kWh")
                
                # Force self-use mode for night battery operation
                if current_work_mode != "Self used mode":
                    log.info(f"Night management: Forcing Self used mode for battery operation (current: {current_work_mode})")
                    night_behavior_override = True
                    desired_mode = "Self used mode"
                
                # Ensure discharge is allowed when SOC > effective minimum
                if soc_pct > effective_min_soc:
                    log.info(f"Night management: SOC {soc_pct:.1f}% > effective minimum {effective_min_soc:.1f}% - allowing battery discharge")
                    # This will be handled by the discharge limit logic below
                else:
                    log.warning(f"Night management: SOC {soc_pct:.1f}% <= effective minimum {effective_min_soc:.1f}% - limiting discharge")
            else:
                # SOC insufficient for night - need grid charging
                calculated_eod_soc = int((required_night_soc / batt_kwh) * 100)
                eod_soc = max(eod_soc, min(calculated_eod_soc, 100))  # Cap at 100%
                if calculated_eod_soc > 100:
                    log.warning(f"Night management: calculated EOD SOC {calculated_eod_soc}% exceeds 100%, capped at 100%")
                log.info(f"Night management: increased EOD SOC to {eod_soc}% to ensure {required_night_soc:.2f}kWh for night")
                
                # Force grid charging if needed
                if soc_pct < effective_min_soc + 10:  # 10% buffer above effective minimum
                    log.warning(f"Night management: SOC {soc_pct:.1f}% too low for night - forcing grid charge")
                    force_grid_charge = True
                    use_grid = True
                    desired_mode = "Time-based control"

        # Defer grid power cap calculation until after power predictions/windows are computed
        cap_w = None

        # Dynamic windows are now calculated by the unified charging plan
        # No need for separate DynamicWindowCalculator
        
        # Work mode decision: Prefer self-use mode when solar is good, time-based when grid charging needed
        # CRITICAL: Don't override emergency mode decisions or night behavior overrides
        if not emergency_mode_override and not night_behavior_override:
            # Start with self-use mode as default
            desired_mode = "Self used mode"

            if grid_available:
                # Grid available: Use already calculated unified charging plan results
                solar_quality_score = SolarQualityAssessor.assess_solar_production_quality(site_pv_today_kwh, site_pv_hourly, tznow, tomorrow_pv_kwh, batt_kwh)
                
                # Only switch to time-based mode if:
                # 1. Very poor solar quality AND need significant charging
                # 2. Solar is insufficient to reach target SOC
                # 3. Critically low SOC requiring immediate grid charging
                should_use_time_based = (
                    (solar_quality_score < 0.3 and energy_needed_kwh > 3.0) or  # Very poor solar + need >3kWh
                    solar_assessment['overall_solar_insufficient'] or  # Solar insufficient (unified assessment)
                    soc_pct < 20  # Critically low SOC (reduced from 25%)
                )
                
                if should_use_time_based:
                    desired_mode = "Time-based control"
                    log.info(f"Switching to time-based mode - poor solar ({solar_quality_score:.2f}) or insufficient excess solar ({daily_excess_solar_kwh:.1f}kWh < {energy_needed_kwh:.1f}kWh needed)")
                else:
                    log.info(f"Using self-use mode - good solar forecast: quality={solar_quality_score:.2f}, excess_solar={daily_excess_solar_kwh:.1f}kWh, needed={energy_needed_kwh:.1f}kWh")
                    
                    # If SOC is low and we have excess solar, prioritize maximum charging
                    if soc_pct < (end_soc_target_pct - 15) and daily_excess_solar_kwh > energy_needed_kwh:
                        log.info(f"Low SOC ({soc_pct:.1f}%) with sufficient excess solar - prioritizing maximum charging over TOU windows")
                    
                    # All discharge windows are now handled by the unified charging plan
                    log.info(f"Discharge windows handled by unified charging plan: {len([w for w in smart_tou_windows if w.get('type') == 'discharge'])} windows")
            else:
                # Grid not available: Define max charge and discharge power for self-use mode
                max_charge_power_w = getattr(self.hub.cfg.smart.policy, 'max_charge_power_w', 3000)
                max_discharge_power_w = getattr(self.hub.cfg.smart.policy, 'max_discharge_power_w', 5000)
                log.info("Grid not available - using self-use mode with unified charging plan")
                    
        elif night_behavior_override:
            log.info("Night behavior override active - using Self used mode for battery operation")
        else:
            log.info("Emergency mode override active - maintaining time-based mode for grid charging")
        
        # Enforce self-use as the base work mode; TOU windows will override during their periods
        desired_mode = "Self used mode"
        log.info("=== FINAL DECISIONS ===")
        log.info(f"Work mode: {desired_mode}")
        log.info(f"Charge windows: {charge_windows}")
        if cap_w is not None:
            log.info(f"Grid power cap: {cap_w}W")
        log.info(f"End-of-day SOC target: {eod_soc}%")
        
        # Compare actual vs forecasted values
        log.info("=== ACTUAL VS FORECAST COMPARISON ===")
        try:
            # Debug: Log what's in the telemetry data
            if last_tel:
                log.info(f"Telemetry data type: {type(last_tel)}")
                log.info(f"Telemetry fields: {list(last_tel.__dict__.keys())}")
                if last_tel.extra:
                    log.info(f"Extra telemetry keys: {list(last_tel.extra.keys())}")
            else:
                log.info("No telemetry data available")
            
            # Get current actual values from telemetry using correct Telemetry object attributes
            actual_pv_w = last_tel.pv_power_w or 0 if last_tel else 0
            actual_load_w = last_tel.load_power_w or 0 if last_tel else 0
            actual_grid_w = last_tel.grid_power_w or 0 if last_tel else 0
            
            # If we need to get additional data from extra fields
            if last_tel and last_tel.extra:
                # Try to get MPPT power from extra data - prefer standardized IDs
                mppt1_power = last_tel.extra.get("pv1_power_w") or last_tel.extra.get("mppt1_power_w") or last_tel.extra.get("mppt1_power", 0) or 0
                mppt2_power = last_tel.extra.get("pv2_power_w") or last_tel.extra.get("mppt2_power_w") or last_tel.extra.get("mppt2_power", 0) or 0
                if mppt1_power or mppt2_power:
                    actual_pv_w = float(mppt1_power) + float(mppt2_power)
                
                # Try to get load power from extra data if not available in main fields
                if actual_load_w == 0:
                    for load_key in ["phase_r_watt_of_eps", "phase_r_watt_of_load", "phase_a_power"]:
                        if load_key in last_tel.extra:
                            actual_load_w = float(last_tel.extra.get(load_key, 0))
                        break
            
                # Try to get grid power from extra data if not available in main fields
                if actual_grid_w == 0:
                    for grid_key in ["phase_r_watt_of_grid"]:
                        if grid_key in last_tel.extra:
                            actual_grid_w = float(last_tel.extra.get(grid_key, 0))
                            break
            
            log.info(f"Raw telemetry values: PV={actual_pv_w}W, Load={actual_load_w}W, Grid={actual_grid_w}W")
            
            # Debug: Show which keys were found
            if actual_pv_w > 0:
                log.info(f"Found PV power in telemetry data")
            if actual_load_w > 0:
                log.info(f"Found Load power in telemetry data")
            if actual_grid_w > 0:
                log.info(f"Found Grid power in telemetry data")
            
            # If still zero, try to get from the most recent telemetry object
            if actual_pv_w == 0 and actual_load_w == 0:
                try:
                    # Get the most recent telemetry object directly
                    for rt in self.hub.inverters:
                        if hasattr(rt.adapter, 'last_tel') and rt.adapter.last_tel:
                            tel_obj = rt.adapter.last_tel
                            log.info(f"Telemetry object type: {type(tel_obj)}")
                            log.info(f"Telemetry object attributes: {dir(tel_obj)}")
                            
                            # Try to access as object attributes
                            if hasattr(tel_obj, 'pv_power_w'):
                                actual_pv_w = float(tel_obj.pv_power_w or 0)
                            if hasattr(tel_obj, 'load_power_w'):
                                actual_load_w = float(tel_obj.load_power_w or 0)
                            if hasattr(tel_obj, 'grid_power_w'):
                                actual_grid_w = float(tel_obj.grid_power_w or 0)
                                
                            log.info(f"Object telemetry values: PV={actual_pv_w}W, Load={actual_load_w}W, Grid={actual_grid_w}W")
                            break
                except Exception as e:
                    log.warning(f"Failed to get telemetry from object: {e}")
            
            # Convert to kW for comparison (instantaneous PV) and estimate hourly energy
            actual_pv_kw = actual_pv_w / 1000.0
            actual_pv_hour_kwh = self._estimate_hourly_pv_kwh_from_instant(actual_pv_w, tznow)
            actual_load_kw = actual_load_w / 1000.0
            actual_grid_kw = actual_grid_w / 1000.0
            
            # Get forecasted values for current hour
            forecasted_pv_kw = site_pv_hourly.get(current_hour, 0)
            forecasted_load_kw = site_load_hourly.get(current_hour, 0)
            forecasted_net_kw = site_net_hourly.get(current_hour, 0)
            
            log.info(f"Current hour {current_hour} comparison:")
            log.info(f"  PV: Actual={actual_pv_kw:.3f}kW (instant), Hourly~={actual_pv_hour_kwh:.3f}kWh, Forecast={forecasted_pv_kw:.3f}kW")
            log.info(f"  Load: Actual={actual_load_kw:.3f}kW, Forecast={forecasted_load_kw:.3f}kW, Diff={actual_load_kw-forecasted_load_kw:.3f}kW")
            log.info(f"  Net: Actual={actual_pv_kw-actual_load_kw:.3f}kW, Forecast={forecasted_net_kw:.3f}kW, Diff={(actual_pv_kw-actual_load_kw)-forecasted_net_kw:.3f}kW")
            log.info(f"  Grid: Actual={actual_grid_kw:.3f}kW")
            
            # Calculate forecast accuracy ratios using instantaneous power
            if forecasted_pv_kw > 0:
                pv_accuracy = actual_pv_kw / forecasted_pv_kw
                log.info(f"  PV forecast accuracy ratio (instant): {pv_accuracy:.3f} (1.0 = perfect, >1.0 = actual higher)")
            if forecasted_load_kw > 0:
                load_accuracy = actual_load_kw / forecasted_load_kw
                log.info(f"  Load forecast accuracy ratio: {load_accuracy:.3f} (1.0 = perfect, >1.0 = actual higher)")
                
        except Exception as e:
            log.warning(f"Failed to compare actual vs forecast values: {e}")

        # === POWER SPLITTING (per-inverter power distribution) ===
        # If this scheduler is scoped to an array and has split config, split array-level targets
        split_plan: Optional[Dict[str, Any]] = None
        split_allocations: Dict[str, Dict[str, float]] = {}  # {inverter_id: {'charge': w, 'discharge': w}}
        
        if self.array_id and array_inverters and len(array_inverters) > 1:
            # Get array config to check for split config
            array_cfg = self.hub.arrays.get(self.array_id) if hasattr(self.hub, 'arrays') else None
            split_cfg = None
            if array_cfg and array_cfg.scheduler_config:
                split_cfg = array_cfg.scheduler_config.inverter_split
            
            if split_cfg:
                log.info(f"=== POWER SPLITTING for array {self.array_id} ===")
                # Get inverter capabilities
                capabilities = self._get_inverter_capabilities(array_inverters)
                
                if capabilities:
                    # Calculate array-level targets (these are calculated later in the loop, so we'll do a preliminary calculation)
                    # For now, we'll split the final caps that will be calculated
                    # We need to get these values from the variables that will be set
                    # Actually, we need to split after final_charge_cap_w and final_discharge_cap_w are calculated
                    # So we'll do the splitting inside the loop, but prepare capabilities here
                    log.info(f"Got capabilities for {len(capabilities)} inverters")
                else:
                    log.warning("No inverter capabilities available for power splitting")
            else:
                log.debug(f"Power splitting not configured for array {self.array_id} or single inverter")
        else:
            log.debug("Power splitting skipped: not an array scheduler or single inverter")

        # Build commands with proper inverter register integration
        cmds_by_inv: Dict[str, List[Dict[str, Any]]] = {}
        for rt in array_inverters if self.array_id else self.hub.inverters:
            cmds: List[Dict[str, Any]] = []
            
            # Set hybrid work mode (register 0x2100)
            work_mode_map = {
                "Self used mode": 0x0000,
                "Feed-in priority mode": 0x0001,
                "Time-based control": 0x0002,
                "Back-up mode": 0x0003,
                "Battery Discharge mode": 0x0004
            }
            work_mode_value = work_mode_map.get(desired_mode, 0x0000)
            cmds.append({"action":"set_work_mode","mode": desired_mode, "register_value": work_mode_value})


            # PRE-SUNSET ASSURANCE: Check if we need to force top-up before sunset
            sunset_hour_int = int(sunset_hour)  # Convert float to int for range()
            if tznow.hour < sunset_hour:
                # Project SOC at sunset based on current SOC and expected net energy
                hours_to_sunset = sunset_hour - tznow.hour
                projected_net_energy = sum(site_net_hourly.get(h, 0) for h in range(tznow.hour, sunset_hour_int))
                projected_sunset_soc = soc_pct + (projected_net_energy / batt_kwh * 100)
                
                # Estimate night load (evening + overnight)
                night_load_estimate = sum(site_load_hourly.get(h, 0) for h in range(sunset_hour_int, 24)) + sum(site_load_hourly.get(h, 0) for h in range(0, 6))
                
                # Check if pre-sunset assurance is needed
                if self.reliability.check_presunset_assurance(soc_pct, projected_sunset_soc, night_load_estimate, batt_kwh):
                    # Only warn if cooldown period has passed
                    if current_time - self._last_presunset_assurance_warning > self._warning_cooldown_seconds:
                        log.warning(f"PRE-SUNSET ASSURANCE: Forcing grid charge to ensure sufficient energy for night load")
                        self._last_presunset_assurance_warning = current_time
                    force_grid_charge = True
                    use_grid = True
                    desired_mode = "Time-based control"
            
            # PRE-DAWN INSURANCE: single early top-up if projection below target
            log.info("=== PRE-DAWN INSURANCE CALCULATION ===")
            predawn_insurance_needed = False
            try:
                sunrise_h = int(self.sunset_calc.get_sunrise_hour(tznow))
                log.info(f"Sunrise hour calculated: {sunrise_h}")
            except Exception as e:
                sunrise_h = 6
                log.warning(f"Failed to calculate sunrise hour, using default: {e}")
            # Target uses effective min + uncertainty cushion
            # Backward compatible: if helper not present, compute cushion directly
            log.info("Calculating uncertainty cushion for pre-dawn insurance")
            try:
                if hasattr(self.reliability, "get_uncertainty_cushion_pct") and callable(getattr(self.reliability, "get_uncertainty_cushion_pct")):
                    cushion_pct = float(self.reliability.get_uncertainty_cushion_pct())
                    log.info(f"Using get_uncertainty_cushion_pct: {cushion_pct}%")
                else:
                    cushion_pct = float(self.reliability.calculate_dynamic_cushion(5, 
                        ForecastUncertainty(
                            pv_confidence="medium", pv_uncertainty_pct=5.0,
                            load_confidence="medium", load_uncertainty_pct=5.0,
                            pv_p75=0.0, pv_p90=0.0, load_p75=0.0, load_p90=0.0
                        )
                    ))
                    log.info(f"Using calculate_dynamic_cushion: {cushion_pct}%")
            except Exception as e:
                cushion_pct = 2.0
                log.warning(f"Failed to calculate cushion, using default: {e}")
            insurance_target = max(effective_min_soc, 20.0) + max(2.0, cushion_pct)
            log.info(f"Insurance target calculated: {insurance_target:.1f}% (effective_min_soc={effective_min_soc:.1f}%, cushion={cushion_pct:.1f}%)")
            
            # Project SoC at sunrise
            log.info("Projecting SOC at sunrise")
            proj_0530 = self._project_sunrise_soc(soc_pct, site_net_hourly if 'site_net_hourly' in locals() else {}, self.sunset_calc, tznow)
            log.info(f"Projected SOC at sunrise: {proj_0530:.1f}%")

            # Use a pre-dawn check window relative to sunrise instead of fixed 03–04
            # Trigger during the last 2 hours before sunrise
            predawn_window_hours = {max(0, sunrise_h - 2) % 24, max(0, sunrise_h - 1) % 24}
            if tznow.hour in predawn_window_hours and proj_0530 < insurance_target:
                predawn_insurance_needed = True
                log.warning(f"PRE-DAWN INSURANCE: scheduling single top-up {(min(predawn_window_hours)):02d}:30–{(max(predawn_window_hours)):02d}:30 target={insurance_target:.1f}% proj={proj_0530:.1f}% reason=low_projection")
                force_grid_charge = True
                use_grid = True
                desired_mode = "Time-based control"
            else:
                log.info(f"Pre-dawn insurance not needed: hour={tznow.hour}, proj={proj_0530:.1f}% >= target={insurance_target:.1f}% or outside pre-dawn window")
            
            # NO-OUTAGE GUARDRAILS: Check explicit guardrails with proactive alerts
            night_load_energy = EnergyPlanner.calculate_night_load_energy(tznow, site_load_hourly, self.sunset_calc)
            guardrail_check = self.reliability.check_no_outage_guardrails(
                soc_pct, soc_pct, night_load_energy, batt_kwh, 
                False, tznow.hour  # Grid charge windows are now handled by unified plan
            )
            
            if guardrail_check["alert_level"] == "critical":
                # CRITICAL: Allow costlier windows to prevent blackout
                log.critical(f"NO-OUTAGE GUARDRAIL: {guardrail_check['recommendations'][0]}")
                force_grid_charge = True
                use_grid = True
                desired_mode = "Time-based control"
                # Allow costlier windows by expanding tariff window search
                log.critical("EXPANDING TARIFF WINDOW SEARCH to include costlier options")
                
            elif guardrail_check["alert_level"] == "warning":
                # WARNING: Consider costlier windows if no cheap ones available
                log.warning(f"NO-OUTAGE GUARDRAIL: {guardrail_check['recommendations'][0]}")
                if guardrail_check["allow_costlier_windows"]:
                    log.warning("ALLOWING COSTLIER WINDOWS due to guardrail warning")
                    force_grid_charge = True
                    use_grid = True
                    desired_mode = "Time-based control"
            
            # Grid charge enable + end SOC
            # Initialize force_grid_charge if not already set
            if 'force_grid_charge' not in locals():
                force_grid_charge = False
            # Critical safety: Always enable grid charging if SOC is dangerously low
            force_grid_charge = force_grid_charge or (soc_pct < critical_soc_threshold)
            
            # Set discharge limit based on grid availability and emergency status
            # NEVER allow discharge below the effective minimum SOC (20% + dynamic cushion)
            log.info("=== DISCHARGE LIMIT CALCULATION ===")
            log.info(f"Emergency mode override: {emergency_mode_override}, Force grid charge: {force_grid_charge}")
            log.info(f"Grid available: {grid_available}, EOD SOC: {eod_soc}%, Effective min SOC: {effective_min_soc}%")
            
            if emergency_mode_override or force_grid_charge:
                if grid_available:
                    # Grid available: Higher limit during emergency to allow grid charging
                    discharge_limit = max(eod_soc, effective_min_soc + 10)  # Extra 10% buffer during emergency
                    log.info(f"Emergency discharge limit set to {discharge_limit:.1f}% (grid available, effective_min={effective_min_soc:.1f}%)")
                else:
                    # Grid not available: Use effective minimum SOC (never below 20% + cushion)
                    discharge_limit = max(eod_soc, effective_min_soc)
                    log.warning(f"Emergency discharge limit set to {discharge_limit:.1f}% (grid unavailable, effective_min={effective_min_soc:.1f}%)")
            else:
                if grid_available:
                    # Grid available: Use effective minimum SOC with small buffer
                    discharge_limit = max(eod_soc, effective_min_soc + 5)  # 5% buffer above effective minimum
                    log.info(f"Normal discharge limit set to {discharge_limit:.1f}% (grid available, effective_min={effective_min_soc:.1f}%)")
                else:
                    # Grid not available: Use effective minimum SOC (never below 20% + cushion)
                    discharge_limit = max(eod_soc, effective_min_soc)
                    log.info(f"Grid unavailable - discharge limit set to {discharge_limit:.1f}% (effective_min={effective_min_soc:.1f}%)")
            
            # Set capacity of discharger end (register 0x211B) - EOD (cap at 100%)
            discharge_limit_capped = min(discharge_limit, 100)
            if discharge_limit > 100:
                log.warning(f"Discharge limit {discharge_limit}% exceeds 100%, capped at 100%")
            log.info(f"Final discharge limit (capped): {discharge_limit_capped}%")
            cmds.append({"action":"set_discharge_limits","end_soc": discharge_limit_capped, "register_value": discharge_limit_capped})
            
            # Log discharge decision with detailed reasoning
            current_mode = InverterManager.get_current_work_mode(last_tel)
            mode_str = "Self used mode" if current_mode == 0 else "Time-based control" if current_mode == 1 else f"Mode {current_mode}"
            
            # Determine discharge decision
            if soc_pct <= discharge_limit_capped:
                decision = "BLOCKED"
                reason = f"SOC {soc_pct:.1f}% at or below discharge limit {discharge_limit_capped:.1f}%"
            elif emergency_mode_override or force_grid_charge:
                decision = "LIMITED"
                reason = f"Emergency mode - discharge limited to preserve battery"
            else:
                decision = "ALLOWED"
                reason = f"Normal operation - discharge allowed above {discharge_limit_capped:.1f}%"
            
            # Log the discharge decision
            self._log_discharge_decision(
                decision=decision,
                reason=reason,
                soc_pct=soc_pct,
                discharge_limit=discharge_limit_capped,
                grid_available=grid_available,
                current_mode=mode_str,
                effective_min_soc=effective_min_soc,
                emergency_mode=emergency_mode_override or force_grid_charge,
                tariff_restriction=False,  # TODO: Add tariff restriction logic
                time_restriction=False     # TODO: Add time restriction logic
            )
            
            # Collect daily performance data for backtesting
            self._collect_daily_performance_data(tznow, soc_pct, last_tel, site_pv_hourly, site_load_hourly, sunset_hour, sunrise_hour)
            
            # Run daily backtest if it's a new day
            self._run_daily_backtest_if_needed(tznow)
            
            log.info("=== CRITICAL GRID CHARGING LOGIC ===")
            log.info(f"Force grid charge: {force_grid_charge}, Grid available: {grid_available}")
            log.info(f"Current SOC: {soc_pct:.1f}%, Critical threshold: {critical_soc_threshold}%")
            
            # Define solar_insufficient_for_target at the beginning so it's available throughout
            solar_insufficient_for_target = getattr(self, '_grid_charge_needed_for_target', False)
            
            if force_grid_charge:
                if grid_available:
                    log.warning(f"CRITICAL: SOC {soc_pct:.1f}% below {critical_soc_threshold}% - FORCING grid charging to prevent blackout")
                    grid_charge_enabled = True
                    # Override mode to time-based for critical grid charging
                    desired_mode = "Time-based control"
                    cmds[0] = {"action":"set_work_mode","mode": desired_mode}  # Update the work mode command
                    log.info("CRITICAL: Switching to time-based mode for emergency grid charging")
                    # Set immediate charge window for critical situations
                    from solarhub.timezone_utils import now_configured
                    now_local = pd.Timestamp(now_configured())
                    chg_start = f"{now_local.hour:02d}:{(now_local.minute//5)*5:02d}"
                    # Use deadline today; if already past, run to end of day
                    chg_end = f"{solar_charge_deadline_h:02d}:00"
                    if solar_charge_deadline_h <= now_local.hour:
                        chg_end = "23:59"
                    # Compute a safe emergency grid charge power
                    configured_grid_cap = getattr(self.hub.cfg.smart.policy, "max_grid_charge_w", None)
                    emergency_model_cap = int(configured_grid_cap) if configured_grid_cap is not None else int(locals().get('actual_charge_power', 0)) or 1500
                    emergency_power_w = GridManager.cap_grid_power_w(last_tel, emergency_model_cap)
                    cmds.append({
                        "action":"set_tou_window1",
                        "chg_start": chg_start,
                        "chg_end": chg_end,
                        "charge_power_w": emergency_power_w,
                        "charge_end_soc": charge_target_soc_pct,
                        "frequency": "Everyday"
                    })
                    log.info(f"CRITICAL: Setting emergency charge window {chg_start}-{chg_end} at {emergency_power_w}W to target {charge_target_soc_pct}%")
                else:
                    log.error(f"CRITICAL: SOC {soc_pct:.1f}% below {critical_soc_threshold}% but GRID NOT AVAILABLE - cannot charge from grid!")
                    grid_charge_enabled = False
                    # Keep in self-use mode but with very high discharge limits
                    log.warning("CRITICAL: Grid unavailable - maintaining self-use mode with maximum battery preservation")
            else:
                # Normal logic: Enable grid charging if:
                # 1. Time-based mode and use_grid is enabled, OR
                # 2. Solar power is insufficient to reach target SOC
                
                if solar_insufficient_for_target and grid_available:
                    # Solar is insufficient - enable grid charging to reach target SOC
                    grid_charge_enabled = True
                    shortfall_kwh = getattr(self, '_grid_charge_shortfall_kwh', 0)
                    log.warning(f"Solar insufficient for target SOC - enabling grid charging for {shortfall_kwh:.2f}kWh shortfall")
                else:
                    # Normal logic: Only enable grid charging in time-based mode and when grid is available
                    grid_charge_enabled = (use_grid and grid_available)
                    log.info(f"Normal grid charging logic: use_grid={use_grid}, grid_available={grid_available} -> enabled={grid_charge_enabled}")
            
            # Set grid charge (register 0x2115) and related parameters
            grid_charge_value = 0x0001 if grid_charge_enabled else 0x0000
            cmds.append({"action":"set_grid_charge","enable": grid_charge_enabled, "end_soc": end_soc_target_pct, "register_value": grid_charge_value})
            
            # Set maximum grid charger power (register 0x2116)
            # Compute cap_w now using telemetry and configured limits; avoid hardcoded defaults
            # Prefer configured max_grid_charge_w; if absent, derive from programmed window charge power caps or predicted charge power
            configured_grid_cap = getattr(self.hub.cfg.smart.policy, "max_grid_charge_w", None)
            # Determine dynamic cap from windows/predictions
            dynamic_grid_cap = None
            if 'smart_tou_windows' in locals() and smart_tou_windows:
                dynamic_grid_cap = max((w.get('charge_power_w', 0) for w in smart_tou_windows if w.get('charge_power_w', 0) > 0), default=0) or None
            else:
                dynamic_grid_cap = int(locals().get('actual_charge_power', 0)) or None

            # Base model cap selection
            model_cap = int(configured_grid_cap) if configured_grid_cap is not None else int(dynamic_grid_cap) if dynamic_grid_cap is not None else int(locals().get('actual_charge_power', 0))
            cap_w = GridManager.cap_grid_power_w(last_tel, model_cap)
            max_grid_charge_power = cap_w if configured_grid_cap is None else min(cap_w, int(configured_grid_cap))
            
            # If solar is insufficient, calculate appropriate grid charge power for the shortfall
            if solar_insufficient_for_target and grid_available:
                shortfall_kwh = getattr(self, '_grid_charge_shortfall_kwh', 0)
                # Calculate grid charge power needed to make up the shortfall
                # Assume we have until sunset to charge from grid
                remaining_hours_until_sunset = max(1, sunset_hour - tznow.hour)
                required_grid_power_kw = shortfall_kwh / remaining_hours_until_sunset
                required_grid_power_w = int(required_grid_power_kw * 1000)
                
                # Use the higher of required power or configured power, but cap at model maximum
                max_grid_charge_power = max(required_grid_power_w, max_grid_charge_power)
                max_grid_charge_power = min(max_grid_charge_power, cap_w)
                
                log.info(f"Grid charge power for solar shortfall: required={required_grid_power_w}W, final={max_grid_charge_power}W")
            
            # Align grid charge cap with short-window override if active
            cmds.append({"action":"set_max_grid_charge_power_w","value": (max_charge_power_w if 'short_window' in locals() and short_window else max_grid_charge_power)})
            
            # Set capacity of grid charger end (register 0x2117)
            cmds.append({"action":"set_grid_charge_end_soc","value": end_soc_target_pct})
            
            if grid_charge_enabled:
                if force_grid_charge:
                    log.info(f"CRITICAL grid charging enabled (target SOC: {end_soc_target_pct}%, power: {max_grid_charge_power}W)")
                else:
                    log.info(f"Grid charging enabled for time-based mode (target SOC: {end_soc_target_pct}%, power: {max_grid_charge_power}W)")
            else:
                log.info("Grid charging disabled - using self-use mode or insufficient need")
            # Program up to 3 windows (clears are handled conditionally later to avoid churn)
            
            # PRE-DAWN INSURANCE WINDOW: Always reserve one window for emergency pre-dawn charging
            if predawn_insurance_needed and grid_charge_enabled:
                predawn_start, predawn_end = self.reliability.get_predawn_insurance_window(tznow, self.sunset_calc)
                cmds.append({
                    "action": "set_tou_window1",
                    "chg_start": predawn_start,
                    "chg_end": predawn_end,
                    "frequency": "Everyday",
                    "charge_power_w": min(actual_charge_power, 2000),  # Conservative power for insurance
                    "charge_end_soc": min(end_soc_target_pct + 10, 100)  # Extra 10% for insurance
                })
                log.warning(f"PRE-DAWN INSURANCE: Set emergency charge window {predawn_start}-{predawn_end}")
                # Adjust remaining windows
                charge_windows = charge_windows[1:] if charge_windows else []  # Remove first window if we used it for insurance
            # Set max charge and discharge power based on configuration
            log.info("=== CHARGE POWER PREDICTION ===")
            max_charge_power_w = getattr(self.hub.cfg.smart.policy, 'max_charge_power_w', 3000)
            max_discharge_power_w = getattr(self.hub.cfg.smart.policy, 'max_discharge_power_w', 5000)
            log.info(f"Max charge power from config: {max_charge_power_w}W")
            log.info(f"Max discharge power from config: {max_discharge_power_w}W")
            
            # AI-based charge power prediction based on solar and load patterns
            log.info("Starting AI-based charge power prediction")
            predicted_charge_power_w = self._predict_optimal_charge_power(
                site_pv_hourly, site_load_hourly, soc_pct, max_charge_power_w
            )
            log.info(f"AI predicted charge power: {predicted_charge_power_w}W")
            
            # Set predicted charge power; final global caps may be overridden by smart/dynamic window computations below
            actual_charge_power = min(predicted_charge_power_w, max_charge_power_w)
            # If very little time remains and solar is insufficient, force max charging power
            short_window = bool(unified_plan.get('remaining_hours', 24) <= 2) and bool(unified_plan.get('solar_assessment', {}).get('overall_solar_insufficient', False))
            if short_window:
                actual_charge_power = max_charge_power_w
                log.info(f"Short window fallback active (<=2h, solar insufficient) - forcing charge power to max: {actual_charge_power}W")
            log.info(f"Final charge power (min of predicted and max){' [short-window override]' if 'short_window' in locals() and short_window else ''}: {actual_charge_power}W")
            # Defer setting global caps until after window computations to avoid contradictions
            need_to_clear_windows = False
            
            # Set TOU windows regardless of base mode; TOU overrides self-use during its period
            if charge_windows:
                need_to_clear_windows = True
                for idx, (s,e) in enumerate(charge_windows[:3], start=1):
                    # Enhanced TOU window with frequency, charge power, and end SOC
                    cmds.append({
                        "action": f"set_tou_window{idx}",
                        "chg_start": s, 
                        "chg_end": e,
                        "frequency": "Everyday",
                        "charge_power_w": actual_charge_power,
                        "charge_end_soc": end_soc_target_pct
                    })
                log.info(f"Set {len(charge_windows)} TOU charge windows for time-based mode")
            elif force_grid_charge:
                need_to_clear_windows = True
                # Critical grid charging: set immediate charge window
                from solarhub.timezone_utils import now_configured
                now_local = pd.Timestamp(now_configured())
                chg_start = f"{now_local.hour:02d}:{(now_local.minute//5)*5:02d}"
                chg_end = "23:59"  # Charge until end of day
                cmds.append({
                    "action": "set_tou_window1", 
                    "chg_start": chg_start, 
                    "chg_end": chg_end,
                    "frequency": "Everyday",
                    "charge_power_w": actual_charge_power,
                    "charge_end_soc": end_soc_target_pct
                })
                log.warning(f"CRITICAL: Set emergency charge window {chg_start}-{chg_end} for immediate grid charging")
            elif desired_mode == "Self used mode":
                # SELF USE MODE: Use already calculated unified charging plan results
                log.info("=== SELF USE MODE - USING UNIFIED CHARGING PLAN ===")
                log.info(f"Using pre-calculated unified charging plan with {len(smart_tou_windows)} windows")
                
                # Update grid charging flags from unified plan
                if unified_plan.get('grid_charge_needed', False):
                    self._grid_charge_needed_for_target = True
                    self._grid_charge_shortfall_kwh = unified_plan.get('energy_shortfall_kwh', 0)
                
                if smart_tou_windows:
                    need_to_clear_windows = True
                    log.info(f"Self-use mode: Setting {len(smart_tou_windows)} smart TOU windows with calculated power and SOC")
                    
                    # Initialize smart charge/discharge caps (will be set in both paths)
                    smart_charge_cap_w = 0
                    smart_discharge_cap_w = 0
                    charge_windows_set = 0
                    discharge_windows_set = 0
                    
                    # Get adapter capabilities for TOU windows
                    adapter = self.hub.inverters[0].adapter if self.hub.inverters else None
                    capability = adapter.get_tou_window_capability() if adapter else {
                        "max_windows": 3,
                        "bidirectional": False,
                        "separate_charge_discharge": True,
                        "max_charge_windows": 3,
                        "max_discharge_windows": 3
                    }
                    
                    # Set smart TOU windows based on adapter capabilities
                    if capability.get("bidirectional", False):
                        # Powdrive-style: bidirectional windows (up to 6)
                        # Combine charge and discharge windows, set direction via target SOC
                        all_windows = [w for w in smart_tou_windows if w.get('type') in ('charge', 'discharge', 'auto')]
                        max_windows = min(capability.get("max_windows", 6), len(all_windows))
                        
                        # Compute global caps from smart windows for bidirectional case
                        for window in all_windows:
                            power_w = abs(window.get('power_w', 0))
                            if power_w > 0:
                                window_type = window.get('type', 'auto')
                                if window_type == 'charge' or (window_type == 'auto' and window.get('target_soc_pct', 100) > soc_pct):
                                    smart_charge_cap_w = max(smart_charge_cap_w, power_w)
                                else:
                                    smart_discharge_cap_w = max(smart_discharge_cap_w, power_w)
                        
                        # Log the windows being processed
                        log.info(f"Processing {len(all_windows)} windows for bidirectional TOU (max: {max_windows})")
                        for win_idx, win in enumerate(all_windows[:max_windows], 1):
                            log.debug(f"Window {win_idx} raw data: {win}")
                        
                        for idx, window in enumerate(all_windows[:max_windows], 1):
                            # Normalize window to generalized format
                            normalized = adapter.normalize_tou_window(window, current_soc_pct=soc_pct) if adapter else window
                            
                            # Validate window has required fields - prefer normalized, fallback to original
                            start_time = normalized.get('start_time') or window.get('start_time')
                            end_time = normalized.get('end_time') or window.get('end_time')
                            power_w = normalized.get('power_w') or window.get('charge_power_w') or window.get('discharge_power_w') or 0
                            target_soc_pct = normalized.get('target_soc_pct') or window.get('target_soc') or 100
                            
                            log.debug(f"Window {idx} normalized: start={start_time}, end={end_time}, power={power_w}W, target_soc={target_soc_pct}%")
                            
                            # Skip windows with invalid times or zero power (unless explicitly clearing)
                            if not start_time or not end_time or (start_time == '00:00' and end_time == '00:00'):
                                log.warning(f"Skipping window {idx} with invalid time: {start_time}-{end_time}")
                                continue
                            
                            if power_w == 0 and not need_to_clear_windows:
                                log.warning(f"Skipping window {idx} with zero power (not clearing)")
                                continue
                            
                            cmds.append({
                                "action": f"set_tou_window{idx}",
                                "start_time": start_time,
                                "end_time": end_time,
                                "power_w": int(abs(power_w)),
                                "target_soc_pct": int(target_soc_pct),
                                "type": normalized.get('type', 'auto')
                            })
                            log.info(f"Queued bidirectional TOU window {idx}: {start_time}-{end_time} "
                                    f"(power: {int(abs(power_w))}W, target SOC: {int(target_soc_pct)}%, type: {normalized.get('type', 'auto')})")
                        charge_windows_set = len(all_windows[:max_windows])
                        discharge_windows_set = len(all_windows[:max_windows])  # Same windows, just counted
                    else:
                        # Senergy-style: separate charge and discharge windows
                        # Set smart TOU charge windows (up to 3)
                        charge_windows = [w for w in smart_tou_windows if w.get('type') == 'charge' or w.get('charge_power_w', 0) > 0]
                        # Compute global caps from smart windows
                        smart_charge_cap_w = max((w.get('charge_power_w', 0) for w in charge_windows), default=0)
                        max_charge_windows = min(capability.get("max_charge_windows", 3), len(charge_windows))
                        for idx, window in enumerate(charge_windows[:max_charge_windows], 1):
                            cmds.append({
                                "action": f"set_tou_window{idx}",
                                "chg_start": window['start_time'],
                                "chg_end": window['end_time'],
                                "frequency": "Everyday",
                                "charge_power_w": (max_charge_power_w if 'short_window' in locals() and short_window else window.get('charge_power_w', actual_charge_power or 0)) or 0,
                                "charge_end_soc": window.get('target_soc', 100)
                            })
                            charge_windows_set += 1
                            log.info(f"Set smart TOU charge window {idx}: {window['start_time']}-{window['end_time']} (power: {window.get('charge_power_w', 0)}W, target SOC: {window.get('target_soc', 100)}%)")
                        
                        # Set smart TOU discharge windows (up to 3)
                        discharge_windows = [w for w in smart_tou_windows if w.get('type') == 'discharge' or w.get('discharge_power_w', 0) > 0]
                        smart_discharge_cap_w = max((w.get('discharge_power_w', 0) for w in discharge_windows), default=0)
                        max_discharge_windows = min(capability.get("max_discharge_windows", 3), len(discharge_windows))
                        for idx, window in enumerate(discharge_windows[:max_discharge_windows], 1):
                            cmds.append({
                                "action": f"set_tou_discharge_window{idx}",
                                "dch_start": window['start_time'],
                                "dch_end": window['end_time'],
                                "frequency": "Everyday",
                                "discharge_power_w": window.get('discharge_power_w', 0),
                                "discharge_end_soc": int(max(window.get('target_soc', 0), math.ceil(effective_min_soc)))
                            })
                            discharge_windows_set += 1
                            log.info(f"Set smart TOU discharge window {idx}: {window['start_time']}-{window['end_time']} (power: {window.get('discharge_power_w', 0)}W, target SOC: {window.get('target_soc', 30)}%)")
                    
                    # Override global caps to reflect calculated smart window powers (use max across programmed windows)
                    # Note: These will be set later in the final caps section to avoid duplicates
                    if smart_charge_cap_w > 0:
                        log.info(f"Self-use mode: Will set global max charge power from smart windows: {int(min(max_charge_power_w, smart_charge_cap_w))}W")
                    if smart_discharge_cap_w > 0:
                        log.info(f"Self-use mode: Will set global max discharge power from smart windows: {int(min(max_discharge_power_w, smart_discharge_cap_w))}W")

                    log.info(f"Self-use mode: Set {charge_windows_set} smart charge windows and {discharge_windows_set} smart discharge windows")
                else:
                    log.info("Self-use mode: No smart TOU windows calculated - using global power and SOC settings")
            
            # Clear ALL windows first to ensure clean slate, then set new ones
            log.info("=== WINDOW CLEARING LOGIC ===")
            log.info(f"Need to clear windows: {need_to_clear_windows}")
            
            # Additional conditions that should trigger window clearing
            should_force_clear = (
                need_to_clear_windows or
                self._detect_past_tou_windows(rt.adapter.last_tel, tznow) or
                self._detect_mode_change(rt.adapter.last_tel, desired_mode) or
                self._detect_significant_time_change(tznow)
            )
            
            if should_force_clear:
                # Check for past/invalid TOU windows in current telemetry
                past_windows_detected = self._detect_past_tou_windows(rt.adapter.last_tel, tznow)
                mode_changed = self._detect_mode_change(rt.adapter.last_tel, desired_mode)
                time_changed = self._detect_significant_time_change(tznow)
                
                log.info(f"Window clearing triggered - Past windows: {past_windows_detected}, Mode change: {mode_changed}, Time change: {time_changed}")
                
                # Clear windows only if we have windows to set, otherwise skip clearing
                # Get max windows from adapter capability (Senergy=3, Powdrive=6)
                capability = adapter.get_tou_window_capability() if adapter else None
                max_windows = capability.get("max_windows", 3) if capability else 3  # Default to 3 for Senergy
                bidirectional = capability.get("bidirectional", False) if capability else False
                
                # Determine how many windows we'll actually set
                windows_to_set_count = 0
                if desired_mode == "Time-based control" and charge_windows:
                    windows_to_set_count = len(charge_windows)
                elif force_grid_charge:
                    windows_to_set_count = 1
                elif desired_mode == "Self used mode" and 'smart_tou_windows' in locals() and smart_tou_windows:
                    if bidirectional:
                        valid_windows = [w for w in smart_tou_windows if w.get('type') in ('charge', 'discharge', 'auto')]
                        windows_to_set_count = min(len(valid_windows), max_windows)
                    else:
                        charge_windows_count = sum(1 for w in smart_tou_windows if w.get('type') == 'charge' or w.get('charge_power_w', 0) > 0)
                        windows_to_set_count = min(charge_windows_count, 3)
                
                # Only clear windows if we have windows to set
                if windows_to_set_count > 0:
                    log.info(f"Clearing {max_windows} existing TOU windows before setting {windows_to_set_count} new windows")
                    for idx in range(1, max_windows + 1):
                        if bidirectional:
                            # Powdrive-style: clear by setting power to 0
                            cmds.append({
                                "action": f"set_tou_window{idx}",
                                "start_time": "00:00",
                                "end_time": "00:00",
                                "power_w": 0,
                                "target_soc_pct": 100,
                                "type": "auto"
                            })
                        else:
                            # Senergy-style: clear by setting time to 00:00 and power to 0
                            cmds.append({
                                "action": f"set_tou_window{idx}",
                                "chg_start": "00:00",
                                "chg_end": "00:00",
                                "charge_power_w": 0,
                                "charge_end_soc": 100
                            })
                        log.info(f"Queued clear command for window {idx}")
                else:
                    log.info("No windows to set - skipping clear operation")
                
                # Use the windows_to_set_count we calculated earlier
                windows_to_set = windows_to_set_count
                log.info(f"Total windows to set after clearing: {windows_to_set}")
                # Re-apply the actual windows immediately after clearing
                if windows_to_set > 0:
                    if desired_mode == "Time-based control" and charge_windows:
                        for idx, (s, e) in enumerate(charge_windows[:3], start=1):
                            cmds.append({
                                "action": f"set_tou_window{idx}",
                                "chg_start": s,
                                "chg_end": e,
                                "frequency": "Everyday",
                                "charge_power_w": (max_charge_power_w if short_window else actual_charge_power),
                                "charge_end_soc": end_soc_target_pct
                            })
                            log.info(f"Re-set TOU charge window {idx}: {s}-{e} (power: {(max_charge_power_w if short_window else actual_charge_power)}W, target SOC: {end_soc_target_pct}%)")
                    elif desired_mode == "Self used mode" and bidirectional and 'smart_tou_windows' in locals() and smart_tou_windows:
                        # Re-apply bidirectional windows after clearing
                        all_windows = [w for w in smart_tou_windows if w.get('type') in ('charge', 'discharge', 'auto')]
                        for idx, window in enumerate(all_windows[:max_windows], 1):
                            normalized = adapter.normalize_tou_window(window, current_soc_pct=soc_pct) if adapter else window
                            start_time = normalized.get('start_time') or window.get('start_time')
                            end_time = normalized.get('end_time') or window.get('end_time')
                            power_w = normalized.get('power_w') or window.get('charge_power_w') or window.get('discharge_power_w') or 0
                            target_soc_pct = normalized.get('target_soc_pct') or window.get('target_soc') or 100
                            
                            if not start_time or not end_time or (start_time == '00:00' and end_time == '00:00') or power_w == 0:
                                continue  # Skip invalid windows
                            
                            cmds.append({
                                "action": f"set_tou_window{idx}",
                                "start_time": start_time,
                                "end_time": end_time,
                                "power_w": int(abs(power_w)),
                                "target_soc_pct": int(target_soc_pct),
                                "type": normalized.get('type', 'auto')
                            })
                            log.info(f"Re-set bidirectional TOU window {idx}: {start_time}-{end_time} (power: {int(abs(power_w))}W, target SOC: {int(target_soc_pct)}%)")
                    elif force_grid_charge:
                        from solarhub.timezone_utils import now_configured
                        now_local = pd.Timestamp(now_configured())
                        chg_start = f"{now_local.hour:02d}:{(now_local.minute//5)*5:02d}"
                        chg_end = "23:59"
                        cmds.append({
                            "action": "set_tou_window1",
                            "chg_start": chg_start,
                            "chg_end": chg_end,
                            "frequency": "Everyday",
                            "charge_power_w": (max_charge_power_w if short_window else actual_charge_power),
                            "charge_end_soc": end_soc_target_pct
                        })
                        log.warning(f"CRITICAL: Re-set emergency charge window {chg_start}-{chg_end}")
                    elif desired_mode == "Self used mode" and 'smart_tou_windows' in locals() and smart_tou_windows:
                        charge_ws = [w for w in smart_tou_windows if w.get('type') == 'charge' or w.get('charge_power_w', 0) > 0][:3]
                        for idx, w in enumerate(charge_ws, start=1):
                            cmds.append({
                                "action": f"set_tou_window{idx}",
                                "chg_start": w['start_time'],
                                "chg_end": w['end_time'],
                                "frequency": "Everyday",
                                "charge_power_w": (max_charge_power_w if short_window else w.get('charge_power_w', actual_charge_power or 0)),
                                "charge_end_soc": w.get('target_soc', end_soc_target_pct)
                            })
                            log.info(f"Re-set smart TOU charge window {idx}: {w['start_time']}-{w['end_time']} (power: {(max_charge_power_w if short_window else w.get('charge_power_w', actual_charge_power or 0))}W, target SOC: {w.get('target_soc', end_soc_target_pct)}%)")
            else:
                log.info("No window clearing needed")
            
            # Note: max grid charge power already set above alongside grid_charge/end_soc
            
            # Set global max limits as fallback values for Self used mode
            if desired_mode == "Self used mode":
                # If we already computed caps from windows above, they have been set.
                # If not, fall back to predicted/configured caps.
                
                # If SOC is low and we have excess solar, use maximum charge power instead of predicted
                if soc_pct < (end_soc_target_pct - 15):
                    # Check if we have excess solar available
                    current_pv_kw = site_pv_hourly.get(tznow.hour, 0)
                    current_load_kw = site_load_hourly.get(tznow.hour, 0)
                    excess_solar_kw = max(0, current_pv_kw - current_load_kw)
                    
                    if excess_solar_kw > 1.0:  # More than 1kW excess solar
                        # Use maximum charge power to reach target SOC quickly
                        final_charge_power = max_charge_power_w
                        log.info(f"Low SOC ({soc_pct:.1f}%) with excess solar ({excess_solar_kw:.1f}kW) - using max charge power: {max_charge_power_w}W")
                    else:
                        final_charge_power = actual_charge_power
                        log.info(f"Set global max charge power (fallback): {actual_charge_power}W (Self used mode)")
                else:
                    final_charge_power = actual_charge_power
                    log.info(f"Set global max charge power (fallback): {actual_charge_power}W (Self used mode)")
                
                cmds.append({"action": "set_max_charge_power_w", "value": final_charge_power})
                # Note: max discharge power is set later in the final caps section to avoid duplicates
                log.info(f"Set global max charge power (fallback): {final_charge_power}W (Self used mode)")
                
                # Set global charge end SOC (fallback when no TOU window is active)
                cmds.append({"action": "set_charge_end_soc", "value": end_soc_target_pct})
                log.info(f"Set global charge end SOC: {end_soc_target_pct}% (fallback for Self used mode)")
                
                # Set global discharge end SOC (fallback when no TOU window is active)
                # This should be the minimum SOC for discharge, not a charging target
                discharge_end_soc = int(math.ceil(effective_min_soc))
                cmds.append({"action": "set_discharge_end_soc", "value": discharge_end_soc})
                log.info(f"Set global discharge end SOC: {discharge_end_soc}% (minimum SOC for discharge, fallback for Self used mode)")

            # Smart discharge power calculation based on phased strategy
            log.info("=== DISCHARGE POWER CALCULATION ===")
            # Use critical threshold as minimum floor during peak/post-peak
            min_soc_threshold_pct = float(critical_soc_threshold)
            log.info(f"Min SOC threshold for discharge: {min_soc_threshold_pct}%")
            log.info(f"Max discharge power: {max_discharge_power_w}W")
            log.info(f"Current SOC: {soc_pct}%, Battery capacity: {batt_kwh}kWh")
            
            # Prefer external helper for clarity and testability
            log.info("Starting phased discharge power calculation")
            discharge_power_w = EnergyPlanner.calculate_phased_discharge_power(
                soc_pct=soc_pct,
                batt_kwh=batt_kwh,
                site_load_hourly=site_load_hourly,
                max_discharge_power_w=max_discharge_power_w,
                tznow=tznow,
                min_soc_threshold_pct=min_soc_threshold_pct,
                tariffs=self.tariffs if hasattr(self, "tariffs") else None,
                sunset_calc=self.sunset_calc,
            )
            log.info(f"Phased discharge power calculation completed: {discharge_power_w}W")
            
            # Set final global caps now (after window-specific overrides computed)
            # Ensure charge cap never undercuts active/soon charge windows or short-window override
            window_charge_cap_w = 0
            try:
                window_charge_cap_w = max(
                    (w.get('charge_power_w', 0) for w in smart_tou_windows if w.get('type') == 'charge' or w.get('charge_power_w', 0) > 0),
                    default=0
                )
            except Exception:
                window_charge_cap_w = 0

            if 'short_window' in locals() and short_window:
                final_charge_cap_w = int(max_charge_power_w)
            else:
                final_charge_cap_w = int(min(max_charge_power_w, max(actual_charge_power, window_charge_cap_w)))
            final_discharge_cap_w = int(min(max_discharge_power_w, discharge_power_w))
            
            # If discharge is blocked (SOC at/below limit), set cap to 0W to prevent discharge
            if soc_pct <= discharge_limit_capped:
                final_discharge_cap_w = 0
                
            # === POWER SPLITTING: Split array-level targets across inverters ===
            # Only split if this is an array scheduler with multiple inverters and split config
            if self.array_id and array_inverters and len(array_inverters) > 1:
                array_cfg = self.hub.arrays.get(self.array_id) if hasattr(self.hub, 'arrays') else None
                split_cfg = None
                if array_cfg and array_cfg.scheduler_config:
                    split_cfg = array_cfg.scheduler_config.inverter_split
                
                if split_cfg and rt.cfg.id == array_inverters[0].cfg.id:  # Only split once, on first inverter
                    log.info(f"=== POWER SPLITTING for array {self.array_id} ===")
                    capabilities = self._get_inverter_capabilities(array_inverters)
                    
                    if capabilities and len(capabilities) > 1:
                        # Split charge power
                        charge_allocations, charge_total, charge_unmet = split_power(
                            P_target_w=float(final_charge_cap_w),
                            inverters=capabilities,
                            mode=split_cfg.mode,
                            step_w=split_cfg.step_w,
                            min_w=split_cfg.min_w_per_inverter,
                            action="charge",
                            fairness=split_cfg.fairness
                        )
                        
                        # Split discharge power
                        discharge_allocations, discharge_total, discharge_unmet = split_power(
                            P_target_w=-float(final_discharge_cap_w),  # Negative for discharge
                            inverters=capabilities,
                            mode=split_cfg.mode,
                            step_w=split_cfg.step_w,
                            min_w=split_cfg.min_w_per_inverter,
                            action="discharge",
                            fairness=split_cfg.fairness
                        )
                        
                        # Store split allocations
                        for inv_id in charge_allocations.keys():
                            split_allocations[inv_id] = {
                                'charge': charge_allocations.get(inv_id, 0.0),
                                'discharge': abs(discharge_allocations.get(inv_id, 0.0))  # Store as positive
                            }
                        
                        # Build split plan for API/MQTT
                        split_plan = {
                            "array_id": self.array_id,
                            "tick_ts": now_iso(),
                            "array_target_w": {
                                "charge": final_charge_cap_w,
                                "discharge": final_discharge_cap_w
                            },
                            "mode": split_cfg.mode,
                            "per_inverter": [
                                {
                                    "inverter_id": inv.inverter_id,
                                    "target_w": {
                                        "charge": charge_allocations.get(inv.inverter_id, 0.0),
                                        "discharge": abs(discharge_allocations.get(inv.inverter_id, 0.0))
                                    },
                                    "headroom_w": {
                                        "charge": calculate_headroom(inv, "charge"),
                                        "discharge": calculate_headroom(inv, "discharge")
                                    },
                                    "rated_w": {
                                        "charge": inv.rated_charge_kw * 1000,
                                        "discharge": inv.rated_discharge_kw * 1000
                                    }
                                }
                                for inv in capabilities
                            ],
                            "unmet_w": {
                                "charge": charge_unmet,
                                "discharge": discharge_unmet
                            }
                        }
                        self._last_split_plan = split_plan
                        
                        # Log setpoints to database
                        ts_iso = now_iso()
                        for inv in capabilities:
                            inv_id = inv.inverter_id
                            charge_target = int(charge_allocations.get(inv_id, 0.0))
                            discharge_target = int(abs(discharge_allocations.get(inv_id, 0.0)))
                            charge_headroom = int(calculate_headroom(inv, "charge"))
                            discharge_headroom = int(calculate_headroom(inv, "discharge"))
                            
                            if charge_target > 0:
                                self.dbLogger.insert_inverter_setpoint(
                                    array_id=self.array_id,
                                    inverter_id=inv_id,
                                    ts_iso=ts_iso,
                                    action="charge",
                                    target_w=charge_target,
                                    headroom_w=charge_headroom,
                                    unmet_w=int(charge_unmet) if inv_id == capabilities[0].inverter_id else 0
                                )
                            
                            if discharge_target > 0:
                                self.dbLogger.insert_inverter_setpoint(
                                    array_id=self.array_id,
                                    inverter_id=inv_id,
                                    ts_iso=ts_iso,
                                    action="discharge",
                                    target_w=discharge_target,
                                    headroom_w=discharge_headroom,
                                    unmet_w=int(discharge_unmet) if inv_id == capabilities[0].inverter_id else 0
                                )
                        
                        log.info(f"Power split complete: charge {final_charge_cap_w}W -> {charge_total:.0f}W allocated ({charge_unmet:.0f}W unmet), "
                                f"discharge {final_discharge_cap_w}W -> {discharge_total:.0f}W allocated ({discharge_unmet:.0f}W unmet)")
                    else:
                        log.warning("Power splitting skipped: insufficient capabilities")
            
            # Use split values if available, otherwise use array-level values
            if rt.cfg.id in split_allocations:
                split_charge_cap = int(split_allocations[rt.cfg.id]['charge'])
                split_discharge_cap = int(split_allocations[rt.cfg.id]['discharge'])
                log.info(f"Using split values for {rt.cfg.id}: charge={split_charge_cap}W, discharge={split_discharge_cap}W")
            else:
                split_charge_cap = final_charge_cap_w
                split_discharge_cap = final_discharge_cap_w
            
            cmds.append({"action": "set_max_charge_power_w", "value": split_charge_cap})
            cmds.append({"action": "set_max_discharge_power_w", "value": split_discharge_cap})
            log.info(f"Final caps: charge={split_charge_cap}W, discharge={split_discharge_cap}W")
            
            # === DISCHARGE WINDOWS (FROM UNIFIED CHARGING PLAN) ===
            # All discharge windows are now calculated by the unified charging plan
            # No need for separate discharge window creation logic
            discharge_windows_from_unified = [w for w in smart_tou_windows if w.get('type') == 'discharge' or w.get('discharge_power_w', 0) > 0]
            
            if discharge_windows_from_unified and desired_mode == "Time-based control":
                for idx, window in enumerate(discharge_windows_from_unified[:3], 1):
                    cmds.append({
                        "action": f"set_tou_discharge_window{idx}", 
                        "dch_start": window['start_time'], 
                        "dch_end": window['end_time'],
                        "frequency": "Everyday",
                        "discharge_power_w": window.get('discharge_power_w', 0),
                        "discharge_end_soc": window.get('target_soc', int(effective_min_soc))
                    })
                log.info(f"Set {len(discharge_windows_from_unified)} TOU discharge windows from unified plan")
            elif desired_mode == "Self used mode":
                log.info(f"Self-use mode: Inverter will manage discharge timing automatically with optimal power: {discharge_power_w}W")
            else:
                # Avoid writing no-op 00:00–00:00 discharge windows at night
                pass

            # Comprehensive command throttling: skip ALL commands if identical to last execution
            # Include work mode, TOU windows, end SOCs, power caps in signature
            normalized_cmds = []
            for cmd in cmds:
                normalized = cmd.copy()
                # Remove dynamic/timestamp fields that shouldn't affect caching
                normalized.pop('timestamp', None)
                normalized.pop('ts', None)
                # Normalize power values to nearest 100W to avoid minor fluctuations
                if 'value' in normalized and isinstance(normalized['value'], (int, float)):
                    if normalized.get('action', '').endswith('_power_w'):
                        normalized['value'] = round(normalized['value'] / 100) * 100
                # Coerce strings for hashing stability
                for k, v in list(normalized.items()):
                    if isinstance(v, float):
                        normalized[k] = round(v, 3)
                normalized_cmds.append(normalized)
            
            sig_src = json.dumps(normalized_cmds, sort_keys=True)
            sig_hash = hashlib.sha1(sig_src.encode("utf-8")).hexdigest()
            
            # Skip ALL commands if identical to last execution (unless forced)
            if not force_execution and self._last_command_signature == sig_hash:
                skipped = len(cmds)
                if skipped > 0:
                    log.info(f"Command throttling: skipped {skipped} redundant commands (unchanged plan)")
                cmds_by_inv[rt.cfg.id] = []  # No commands to execute
            else:
                cmds_by_inv[rt.cfg.id] = cmds
                self._last_command_signature = sig_hash
                self._last_command_write_ts = now_configured()
                reason = "forced execution" if force_execution else "plan changed"
                log.info(f"Command execution: {len(cmds)} commands ({reason})")

        # Execute & publish plan
        log.info("=== COMMAND EXECUTION ===")
        total_commands = sum(len(cmds) for cmds in cmds_by_inv.values())
        log.info(f"Total commands to execute: {total_commands}")
        
        for rt in self.hub.inverters:
            inverter_cmds = cmds_by_inv[rt.cfg.id]
            # Canonicalize & deduplicate commands to prevent contradictory writes
            canonical: Dict[str, Dict[str, Any]] = {}
            def key_for(cmd: Dict[str, Any]) -> str:
                action = cmd.get('action', '')
                # Use action and window index (if present) as identity
                return action
            for c in inverter_cmds:
                canonical[key_for(c)] = c  # last one wins
            canonical_cmds = list(canonical.values())
            log.info(f"Executing {len(canonical_cmds)} commands for inverter {rt.cfg.id}")

            for i, c in enumerate(canonical_cmds, 1):
                log.info(f"Executing command {i}/{len(canonical_cmds)} for {rt.cfg.id}: {c.get('action', 'unknown')}")
                try:
                    result = await rt.adapter.handle_command(c)
                    # Check if command actually succeeded
                    if result and result.get("ok", False):
                        log.info(f"Command {i} executed successfully for {rt.cfg.id}")
                    else:
                        reason = result.get("reason", "Unknown error") if result else "No response"
                        log.warning(f"Command {i} failed for {rt.cfg.id}: {reason}")
                        log.warning(f"Failed command was: {c}")
                    # Add small delay between commands to avoid Modbus communication issues
                    import asyncio
                    await asyncio.sleep(0.2)  # 200ms delay between commands
                except Exception as e:
                    log.error(f"Command {i} exception for {rt.cfg.id}: {e}", exc_info=True)
                # Publish what we tried
                self.hub.mqtt.pub(f"{self.hub.cfg.mqtt.base_topic}/{rt.cfg.id}/smart_cmd",
                                  {"ts": now_iso(), **c})
            
            log.info(f"Completed command execution for inverter {rt.cfg.id}")
        
        log.info("=== COMMAND EXECUTION COMPLETED ===")

        # Publish split plan via MQTT if available
        if self._last_split_plan and self.array_id:
            plan_topic = f"{self.hub.cfg.mqtt.base_topic}/arrays/{self.array_id}/plan"
            self.hub.mqtt.pub(plan_topic, self._last_split_plan)
            log.info(f"Published split plan to {plan_topic}")

        # Telemetry about plan/forecast
        log.debug("=== MQTT PUBLISHING ===")
        log.debug("Publishing forecast data")
        self.hub.mqtt.pub(f"{self.hub.cfg.mqtt.base_topic}/forecast", {
            "ts": now_iso(),
            "pv_today_kwh": site_pv_today_kwh,
            "per_inverter_today": per_today,
            "pv_tomorrow_kwh": round(sum(per_tomorrow.values()), 2),
            "site_pv_hourly_kwh": site_pv_hourly,  # NEW: nice to visualize
        })
        log.debug("Forecast data published successfully")
        
        # Enhanced forecast data for Home Assistant
        log.debug("Preparing enhanced forecast data")
        enhanced_forecast_data = {
            "ts": now_iso(),
            "self_sufficiency_pct": 0.0,  # Will be updated by battery optimizer
            "dynamic_soc_target_pct": end_soc_target_pct,
            "daily_grid_usage_kwh": 0.0,  # Will be updated by battery optimizer
            "daily_pv_usage_kwh": site_pv_today_kwh,
            "emergency_reserve_hours": self.hub.cfg.smart.policy.emergency_reserve_hours,
            "load_shift_opportunities": 0,  # Placeholder
            "peak_shaving_plan": "none"  # Placeholder
        }
        
        # Add enhanced weather data if available
        if enhanced_forecast:
            today_str = tznow.strftime('%Y-%m-%d')
            tomorrow_str = (tznow + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
            today_weather = enhanced_forecast.get(today_str, {})
            tomorrow_weather = enhanced_forecast.get(tomorrow_str, {})
            
            enhanced_forecast_data.update({
                "today_weather": today_weather,
                "tomorrow_weather": tomorrow_weather,
                "weather_forecast_available": True
            })
            log.debug("Enhanced weather data added to forecast")
        else:
            enhanced_forecast_data["weather_forecast_available"] = False
            log.debug("No enhanced weather data available")
        
        log.debug(f"Publishing enhanced forecast data to {self.hub.cfg.mqtt.base_topic}/enhanced_forecast")
        self.hub.mqtt.pub(f"{self.hub.cfg.mqtt.base_topic}/enhanced_forecast", enhanced_forecast_data)
        log.debug(f"Enhanced forecast data published successfully")
        
        log.debug("Publishing plan data")
        self.hub.mqtt.pub(f"{self.hub.cfg.mqtt.base_topic}/plan", {
            "ts": now_iso(),
            "sunset_hour": sunset_h,
            "soc_now_pct": soc_pct,
            "end_soc_target_pct": end_soc_target_pct,
            "required_grid_kwh": round(energy_needed_kwh, 2),
            "use_grid": use_grid,
            "charge_windows": charge_windows,
            "grid_power_cap_w": cap_w,
        })
        log.debug("Plan data published successfully")
        
        # Publish battery optimization discovery and configuration data
        log.debug("=== BATTERY OPTIMIZATION DATA PUBLISHING ===")
        await self._publish_battery_optimization_data()
        log.debug("=== BATTERY OPTIMIZATION DATA PUBLISHING COMPLETED ===")
    
    async def _publish_battery_optimization_data(self):
        """Publish battery optimization discovery and configuration data."""
        try:
            # Publish battery optimization discovery messages
            log.debug("Publishing battery optimization discovery messages")
            self.battery_ha.publish_all_battery_optimization_discovery()
            self.battery_ha.verify_discovery_messages()
            log.debug("Battery optimization discovery messages published successfully")
            
            # Publish configuration discovery messages
            log.debug("Publishing configuration discovery messages")
            self.config_ha.publish_all_config_discovery()
            self.config_ha.publish_current_config()
            log.debug("Configuration discovery messages published successfully")
            
            # Publish inverter configuration discovery messages
            log.debug("Publishing inverter configuration discovery messages")
            # Ensure command handler is initialized
            self._initialize_inverter_config_handler()
            for inverter in self.hub.inverters:
                if hasattr(inverter.adapter, 'regs') and inverter.adapter.regs:
                    self.inverter_config_ha.publish_inverter_config_sensors(inverter.cfg.id, inverter.adapter.regs)
            log.debug("Inverter configuration discovery messages published successfully")
            
            # Configuration data is published via individual subtopics in publish_current_config()
            
        except Exception as e:
            log.error(f"Failed to publish battery optimization data: {e}")
    
    
    async def handle_config_command(self, topic: str, payload: Any):
        """Handle configuration commands from Home Assistant."""
        try:
            if isinstance(payload, (str, bytes)):
                data = json.loads(payload)
            else:
                data = payload
            
            # Check if this is a general configuration command
            if "setting" in data:
                # Handle general configuration commands
                await self.config_handler.handle_config_command(topic, data)
            else:
                # Handle battery optimization configuration commands (legacy)
                await self._update_battery_optimization_config(data)
            
        except Exception as e:
            log.warning("Bad config command payload: %s (%s)", payload, e)
    
    async def _update_battery_optimization_config(self, data: Dict[str, Any]):
        """Update battery optimization configuration using database persistence."""
        log.info(f"Updating battery optimization configuration with data: {data}")
        
        try:
            # Update each configuration value using the configuration manager
            for key, value in data.items():
                config_key = f"smart.policy.{key}"
                
                # Special handling for tariffs (convert to TariffConfig objects)
                if key == "tariffs":
                    try:
                        from solarhub.config import TariffConfig
                        
                        # Parse tariff data (could be JSON string or list)
                        tariff_data = value
                        if isinstance(tariff_data, str):
                            tariff_data = json.loads(tariff_data)
                        
                        # Convert to TariffConfig objects
                        new_tariffs = []
                        for tariff_dict in tariff_data:
                            new_tariffs.append(TariffConfig(**tariff_dict))
                        
                        # Update using configuration manager
                        self.config_manager.update_config(config_key, [tariff.model_dump() for tariff in new_tariffs])
                        
                        # Update in-memory config
                        self.hub.cfg.smart.policy.tariffs = new_tariffs
                        
                        log.info(f"Updated tariffs: {len(new_tariffs)} tariff windows")
                        for i, tariff in enumerate(new_tariffs):
                            log.info(f"  Tariff {i+1}: {tariff.kind} ({tariff.start}-{tariff.end}) price={tariff.price}")
                            
                    except Exception as e:
                        log.error(f"Failed to update tariffs: {e}")
                        continue
                else:
                    # Type conversion for other values
                    if key in ["dynamic_soc_enabled", "enable_auto_mode_switching"]:
                        value = bool(value)
                    elif key in ["target_self_sufficiency_pct", "min_self_sufficiency_pct", "max_grid_usage_kwh_per_day", 
                                "emergency_reserve_hours", "smart_tick_interval_secs", "max_charge_power_w", 
                                "max_discharge_power_w", "max_battery_soc_pct", "solar_target_threshold_pct", 
                                "poor_weather_threshold_kwh", "close_to_target_threshold_pct"]:
                        value = float(value)
                    elif key in ["primary_mode"]:
                        value = str(value)
                    
                    # Update using configuration manager (persists to database)
                    self.config_manager.update_config(config_key, value)
                    
                    # Update in-memory config
                    self._update_nested_config(self.hub.cfg, config_key, value)
                    
                    log.info(f"Updated {key}: {value}")
            
            log.info("Battery optimization configuration updated successfully and persisted to database")
            
            # Configuration values are automatically republished via publish_current_config() in config command handler
            
        except Exception as e:
            log.error(f"Failed to update battery optimization configuration: {e}")
    
    def _update_nested_config(self, config, key: str, value: Any):
        """Update nested configuration value."""
        keys = key.split('.')
        current = config
        
        # Navigate to the parent object
        for k in keys[:-1]:
            current = getattr(current, k)
        
        # Set the final value
        setattr(current, keys[-1], value)








    def _predict_optimal_charge_power(self, site_pv_hourly: Dict[int, float], 
                                    site_load_hourly: Dict[int, float], 
                                    current_soc_pct: float, 
                                    max_charge_power_w: float) -> float:
        """
        AI-based charge power prediction based on solar generation and load patterns.
        
        This method predicts the optimal charge power by analyzing:
        1. Available solar power during charging hours
        2. Load patterns and grid usage
        3. Current SOC and target SOC
        4. Time-of-day patterns
        
        Returns the predicted optimal charge power in watts.
        """
        try:
            from solarhub.timezone_utils import now_configured
            tznow = pd.Timestamp(now_configured())
            current_hour = tznow.hour
            
            # Calculate available solar power for charging (sunrise to sunset)
            sunrise_hour = int(self.sunset_calc.get_sunrise_hour(tznow))
            sunset_hour = int(self.sunset_calc.get_sunset_hour(tznow))
            charging_hours = list(range(sunrise_hour, sunset_hour + 1))
            available_solar_power = []
            
            for hour in charging_hours:
                pv_power = site_pv_hourly.get(hour, 0.0) * 1000  # Convert kWh to W
                load_power = site_load_hourly.get(hour, 0.0) * 1000  # Convert kWh to W
                net_solar = max(0, pv_power - load_power)  # Available for charging
                available_solar_power.append(net_solar)
            
            # Calculate average available solar power during charging hours
            avg_available_solar = sum(available_solar_power) / len(available_solar_power) if available_solar_power else 0
            
            # Adjust based on current SOC
            soc_factor = 1.0
            if current_soc_pct > 90:
                soc_factor = 0.3  # Reduce charging when nearly full
            elif current_soc_pct > 80:
                soc_factor = 0.6  # Moderate charging
            elif current_soc_pct < 20:
                soc_factor = 1.5  # Increase charging when low
            
            # Time-of-day adjustment
            time_factor = 1.0
            if 6 <= current_hour <= 10:
                time_factor = 1.2  # Morning boost
            elif 10 <= current_hour <= 14:
                time_factor = 1.0  # Peak solar hours
            elif 14 <= current_hour <= 18:
                time_factor = 0.8  # Afternoon tapering
            
            # Predict optimal charge power
            # Base prediction on available solar, with grid supplement if needed
            predicted_power = avg_available_solar * soc_factor * time_factor
            
            # Ensure we don't exceed maximum charge power
            predicted_power = min(predicted_power, max_charge_power_w)
            
            # Minimum charge power to ensure some charging happens
            min_charge_power = 500  # 500W minimum
            predicted_power = max(predicted_power, min_charge_power)
            
            log.info(f"Charge power prediction: avg_solar={avg_available_solar:.0f}W, "
                    f"soc_factor={soc_factor:.2f}, time_factor={time_factor:.2f}, "
                    f"predicted={predicted_power:.0f}W")
            
            return int(predicted_power)
            
        except Exception as e:
            log.warning(f"Error in charge power prediction: {e}")
            # Fallback to 50% of max charge power
            return int(max_charge_power_w * 0.5)
    
    def sync_config_to_file(self):
        """Sync current configuration back to config.yaml file."""
        try:
            self.config_manager.sync_to_file()
            log.info("Configuration synced to config.yaml file")
        except Exception as e:
            log.error(f"Failed to sync configuration to file: {e}")
    
    def _check_degraded_data_conditions(self, factors: Dict[str, float], enhanced_forecast: Optional[Dict]) -> bool:
        """
        Check if forecast data is degraded and requires conservative fallback.
        
        Args:
            factors: Weather factors for today/tomorrow
            enhanced_forecast: Enhanced forecast data
            
        Returns:
            True if degraded data conditions are detected
        """
        try:
            # Check 1: Very low weather factors (indicating poor conditions or API issues)
            if factors.get("today", 0) < 0.1 or factors.get("tomorrow", 0) < 0.1:
                log.warning(f"Degraded data detected: Very low weather factors - today: {factors.get('today', 0):.3f}, tomorrow: {factors.get('tomorrow', 0):.3f}")
                return True
            
            # Check 2: Missing enhanced forecast data
            if enhanced_forecast is None:
                log.warning("Degraded data detected: No enhanced forecast data available")
                return True
            
            # Check 3: Enhanced forecast has insufficient data
            if isinstance(enhanced_forecast, dict):
                from solarhub.timezone_utils import now_configured
                today_str = pd.Timestamp(now_configured()).strftime('%Y-%m-%d')
                tomorrow_str = (pd.Timestamp(now_configured()) + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                
                today_data = enhanced_forecast.get(today_str, {})
                tomorrow_data = enhanced_forecast.get(tomorrow_str, {})
                
                # Check if forecast data is missing key fields
                required_fields = ['irradiance', 'temperature', 'cloud_cover']
                today_missing = sum(1 for field in required_fields if field not in today_data or today_data[field] is None)
                tomorrow_missing = sum(1 for field in required_fields if field not in tomorrow_data or tomorrow_data[field] is None)
                
                if today_missing >= 2 or tomorrow_missing >= 2:
                    log.warning(f"Degraded data detected: Missing forecast fields - today: {today_missing}, tomorrow: {tomorrow_missing}")
                    return True
            
            # Check 4: Extreme weather factor differences (indicating forecast instability)
            today_factor = factors.get("today", 0)
            tomorrow_factor = factors.get("tomorrow", 0)
            if abs(today_factor - tomorrow_factor) > 0.8:  # Very different conditions
                log.warning(f"Degraded data detected: Extreme weather factor difference - today: {today_factor:.3f}, tomorrow: {tomorrow_factor:.3f}")
                return True
            
            return False
            
        except Exception as e:
            log.warning(f"Error checking degraded data conditions: {e}")
            return True  # Conservative: assume degraded if we can't check
    
    def _get_conservative_fallback_factors(self) -> Dict[str, float]:
        """
        Get conservative fallback weather factors when forecast data is unavailable.
        
        Returns:
            Conservative weather factors
        """
        # Use conservative factors that assume moderate conditions
        # These are based on typical seasonal averages
        from solarhub.timezone_utils import now_configured
        tznow = pd.Timestamp(now_configured())
        doy = int(tznow.dayofyear)
        
        # Seasonal adjustment (rough approximation)
        if 80 <= doy <= 172:  # Spring (Mar 21 - Jun 21)
            base_factor = 0.6
        elif 173 <= doy <= 266:  # Summer (Jun 22 - Sep 23)
            base_factor = 0.7
        elif 267 <= doy <= 355:  # Fall (Sep 24 - Dec 21)
            base_factor = 0.5
        else:  # Winter (Dec 22 - Mar 20)
            base_factor = 0.4
        
        return {
            "today": base_factor * 0.8,  # 20% reduction for today (more conservative)
            "tomorrow": base_factor * 0.9  # 10% reduction for tomorrow
        }
    
    def _apply_conservative_adjustments(self, factors: Dict[str, float]) -> Dict[str, float]:
        """
        Apply conservative adjustments to weather factors in degraded-data mode.
        
        Args:
            factors: Original weather factors
            
        Returns:
            Conservatively adjusted factors
        """
        adjusted = factors.copy()
        
        # Reduce today's factor by 20% (more conservative for immediate planning)
        if "today" in adjusted:
            adjusted["today"] = max(0.2, adjusted["today"] * 0.8)
        
        # Reduce tomorrow's factor by 15% (slightly less conservative for future planning)
        if "tomorrow" in adjusted:
            adjusted["tomorrow"] = max(0.2, adjusted["tomorrow"] * 0.85)
        
        log.info(f"Applied conservative adjustments: today {factors.get('today', 0):.3f} -> {adjusted.get('today', 0):.3f}, "
                f"tomorrow {factors.get('tomorrow', 0):.3f} -> {adjusted.get('tomorrow', 0):.3f}")
        
        return adjusted
    
    def _log_soc_with_mode_correlation(self):
        """Log SOC with inverter mode correlation every 5 minutes."""
        import time
        current_time = time.time()
        
        # Check if it's time to log SOC
        if (self._last_soc_log_time is None or 
            current_time - self._last_soc_log_time >= self._soc_log_interval_seconds):
            
            try:
                # Get current SOC and inverter mode for all inverters
                for rt in self.hub.inverters:
                    if hasattr(rt, 'adapter') and hasattr(rt.adapter, 'last_tel'):
                        last_tel = rt.adapter.last_tel
                        if last_tel:
                            # Get SOC using correct Telemetry object attributes
                            if isinstance(last_tel, dict):
                                soc_pct = last_tel.get('batt_soc_pct', 0) or 0
                            else:
                                soc_pct = last_tel.batt_soc_pct or 0
                            soc_kwh = self._energy_in_battery_kwh(soc_pct)
                            
                            # Get inverter mode from extra data if available
                            inverter_mode = "Unknown"
                            if isinstance(last_tel, dict):
                                extra_data = last_tel.get('extra', {})
                                if extra_data:
                                    inverter_mode = extra_data.get('inverter_mode', 'Unknown')
                            elif hasattr(last_tel, 'extra') and last_tel.extra:
                                inverter_mode = last_tel.extra.get('inverter_mode', 'Unknown')
                            
                            if isinstance(inverter_mode, str):
                                mode_str = inverter_mode
                            else:
                                # Fallback to work mode if available
                                if isinstance(last_tel, dict):
                                    extra_data = last_tel.get('extra', {})
                                    if extra_data:
                                        work_mode = extra_data.get('work_mode', -1)
                                    else:
                                        work_mode = -1
                                elif hasattr(last_tel, 'extra') and last_tel.extra:
                                    work_mode = last_tel.extra.get('work_mode', -1)
                                else:
                                    work_mode = -1
                                if work_mode == 0:
                                    mode_str = "Self used mode"
                                elif work_mode == 1:
                                    mode_str = "Time-based control"
                                elif work_mode == 2:
                                    mode_str = "Backup mode"
                                elif work_mode == 3:
                                    mode_str = "Feed-in priority"
                                else:
                                    mode_str = "Unknown"
                            
                            # Get grid status using correct field names
                            if isinstance(last_tel, dict):
                                grid_power = last_tel.get('grid_power_w', 0) or 0
                                pv_power = last_tel.get('pv_power_w', 0) or 0
                                load_power = last_tel.get('load_power_w', 0) or 0
                                batt_power = last_tel.get('batt_power_w', 0) or 0
                            else:
                                grid_power = last_tel.grid_power_w or 0
                                pv_power = last_tel.pv_power_w or 0
                                load_power = last_tel.load_power_w or 0
                                batt_power = last_tel.batt_power_w or 0
                            grid_available = abs(grid_power) > 10  # Grid available if power > 10W
                            
                            # Determine power source
                            power_source = "Unknown"
                            if batt_power > 50:
                                power_source = "Battery charging"
                            elif batt_power < -50:
                                power_source = "Battery discharging"
                            elif grid_power > 50:
                                power_source = "Grid supplying"
                            elif grid_power < -50:
                                power_source = "Grid charging"
                            elif pv_power > 50:
                                power_source = "Solar only"
                            else:
                                power_source = "Idle"
                            
                            # Enhanced SOC logging
                            log.info(f"SOC_MONITOR [{rt.cfg.id}]: SOC={soc_pct:.1f}% ({soc_kwh:.2f}kWh), "
                                    f"Mode={mode_str}, Grid={'Available' if grid_available else 'Unavailable'}, "
                                    f"Source={power_source}, PV={pv_power:.0f}W, Load={load_power:.0f}W, "
                                    f"Batt={batt_power:.0f}W, Grid={grid_power:.0f}W")
                            
            except Exception as e:
                log.warning(f"Failed to log SOC with mode correlation: {e}")
            
            self._last_soc_log_time = current_time
    
    def _log_discharge_decision(self, decision: str, reason: str, soc_pct: float, 
                               discharge_limit: float, grid_available: bool, 
                               current_mode: str, **kwargs):
        """
        Log discharge decision with detailed reasoning.
        
        Args:
            decision: "ALLOWED", "BLOCKED", "LIMITED"
            reason: Detailed reason for the decision
            soc_pct: Current SOC percentage
            discharge_limit: Current discharge limit
            grid_available: Whether grid is available
            current_mode: Current inverter mode
            **kwargs: Additional context data
        """
        try:
            # Get additional context
            effective_min_soc = kwargs.get('effective_min_soc', 0)
            emergency_mode = kwargs.get('emergency_mode', False)
            tariff_restriction = kwargs.get('tariff_restriction', False)
            time_restriction = kwargs.get('time_restriction', False)
            
            # Build detailed reason string
            reason_details = []
            if emergency_mode:
                reason_details.append("emergency_mode")
            if tariff_restriction:
                reason_details.append("tariff_restriction")
            if time_restriction:
                reason_details.append("time_restriction")
            if not grid_available:
                reason_details.append("grid_unavailable")
            if soc_pct <= discharge_limit:
                reason_details.append("soc_at_limit")
            
            reason_str = f"{reason}"
            if reason_details:
                reason_str += f" (factors: {', '.join(reason_details)})"
            
            # Log the decision
            log.info(f"DISCHARGE_DECISION: {decision} - {reason_str}")
            log.info(f"DISCHARGE_CONTEXT: SOC={soc_pct:.1f}%, Limit={discharge_limit:.1f}%, "
                    f"EffectiveMin={effective_min_soc:.1f}%, Mode={current_mode}, "
                    f"Grid={'Available' if grid_available else 'Unavailable'}")
            
            # Log specific blocking reasons
            if decision == "BLOCKED":
                if soc_pct <= discharge_limit:
                    log.warning(f"DISCHARGE_BLOCKED: SOC {soc_pct:.1f}% at or below discharge limit {discharge_limit:.1f}%")
                if emergency_mode:
                    log.warning(f"DISCHARGE_BLOCKED: Emergency mode active - preserving battery for critical loads")
                if tariff_restriction:
                    log.info(f"DISCHARGE_BLOCKED: Tariff restriction - peak hours or expensive grid")
                if time_restriction:
                    log.info(f"DISCHARGE_BLOCKED: Time restriction - outside allowed discharge window")
                if not grid_available:
                    log.warning(f"DISCHARGE_BLOCKED: Grid unavailable - battery is only power source")
            
        except Exception as e:
            log.warning(f"Failed to log discharge decision: {e}")
    
    def reload_config_from_database(self):
        """Reload configuration from database."""
        try:
            new_cfg = self.config_manager.reload_config()
            self.hub.cfg = new_cfg
            
            # Update SOC logging interval if it changed
            new_interval = getattr(new_cfg.smart.policy, 'soc_log_interval_secs', 300)
            if new_interval != self._soc_log_interval_seconds:
                self._soc_log_interval_seconds = new_interval
                log.info(f"SOC logging interval updated to {new_interval} seconds")
            
            log.info("Configuration reloaded from database")
        except Exception as e:
            log.error(f"Failed to reload configuration from database: {e}")
