from typing import Dict, List, Tuple, Optional, Any
import pandas as pd


class EnergyPlanner:
    @staticmethod
    def calculate_optimal_discharge_power(
        soc_pct: float,
        site_load_hourly: Dict[int, float],
        batt_kwh: float,
        max_discharge_power_w: float,
        tznow: pd.Timestamp,
        sunset_calc=None,
    ) -> int:
        """
        Optimal discharge considering remaining load, safety margin, and time-of-day.
        Mirrors in-file logic to keep behavior consistent.
        """
        current_soc_kwh = (soc_pct / 100.0) * batt_kwh

        remaining_hours = [h for h in range(tznow.hour, 24)]
        remaining_load_kwh = sum(site_load_hourly.get(h, 0) for h in remaining_hours)

        safety_margin_kwh = batt_kwh * 0.3
        available_for_discharge_kwh = max(0, current_soc_kwh - safety_margin_kwh)

        required_discharge_kwh = max(0, remaining_load_kwh - available_for_discharge_kwh)

        # Use dynamic sunset if available, otherwise fallback to 17:00
        if sunset_calc:
            sunset_hour = int(sunset_calc.get_sunset_hour(tznow))
        else:
            sunset_hour = 17  # Fallback
        hours_remaining = max(1, sunset_hour - tznow.hour)

        if required_discharge_kwh > 0 and hours_remaining > 0:
            optimal_power_w = int((required_discharge_kwh * 1000) / hours_remaining)
        else:
            optimal_power_w = int(max_discharge_power_w * 0.3)

        if soc_pct > 80:
            soc_factor = 1.0
        elif soc_pct > 50:
            soc_factor = 0.7
        elif soc_pct > 30:
            soc_factor = 0.4
        else:
            soc_factor = 0.2

        current_hour = tznow.hour
        if 18 <= current_hour <= 22:
            time_factor = 1.2
        elif 6 <= current_hour <= 17:
            time_factor = 0.8
        else:
            time_factor = 0.5

        final_power_w = int(optimal_power_w * soc_factor * time_factor)
        final_power_w = max(100, min(final_power_w, int(max_discharge_power_w)))
        return final_power_w

    @staticmethod
    def calculate_phased_discharge_power(
        soc_pct: float,
        batt_kwh: float,
        site_load_hourly: Dict[int, float],
        max_discharge_power_w: float,
        tznow: pd.Timestamp,
        min_soc_threshold_pct: float,
        tariffs: Optional[List] = None,
        sunset_calc=None,
    ) -> int:
        """
        Phase 1 (peak): spread allowable energy over remaining peak hours.
        Phase 2 (post-peak): glide toward min SOC threshold by sunrise/solar.
        """
        current_soc_kwh = (soc_pct / 100.0) * batt_kwh
        min_soc_kwh = (min_soc_threshold_pct / 100.0) * batt_kwh

        in_peak = False
        remaining_peak_hours = 0
        remaining_peak_energy_kwh = 0.0
        if tariffs:
            now_t = tznow.time()
            for tariff in tariffs:
                if getattr(tariff, "kind", None) == "peak":
                    start_h = tariff.start.hour
                    end_h = tariff.end.hour
                    if tariff.start <= now_t < tariff.end:
                        in_peak = True
                        for hour in range(tznow.hour, end_h):
                            remaining_peak_hours += 1
                            remaining_peak_energy_kwh += site_load_hourly.get(hour, 0.8)
                    elif now_t < tariff.start:
                        for hour in range(start_h, end_h):
                            remaining_peak_hours += 1
                            remaining_peak_energy_kwh += site_load_hourly.get(hour, 0.8)

        if in_peak and remaining_peak_hours > 0:
            allowable_discharge_kwh = max(0.0, current_soc_kwh - min_soc_kwh)
            target_discharge_kwh = min(allowable_discharge_kwh, remaining_peak_energy_kwh)
            if target_discharge_kwh <= 0:
                return 100
            power_w = int((target_discharge_kwh * 1000.0) / max(1, remaining_peak_hours))
            return max(100, min(power_w, int(max_discharge_power_w)))

        if soc_pct > min_soc_threshold_pct:
            excess_kwh = max(0.0, current_soc_kwh - min_soc_kwh)
            # Use dynamic sunrise for glide horizon if available
            if sunset_calc:
                sunrise_hour = int(sunset_calc.get_sunrise_hour(tznow))
                hours = max(1, (sunrise_hour - tznow.hour) if tznow.hour < sunrise_hour else 3)
            else:
                solar_start_hour = 8
                hours = max(1, solar_start_hour - tznow.hour) if tznow.hour < solar_start_hour else 3
            power_w = int((excess_kwh * 1000.0) / hours)
            return max(100, min(power_w, int(max_discharge_power_w)))

        return 100

    @staticmethod
    def calculate_night_load_energy(tznow: pd.Timestamp, site_load_hourly: Dict[int, float], sunset_calc=None) -> float:
        current_hour = tznow.hour
        night_energy = 0.0
        
        # Use dynamic sunset if available, otherwise fallback to 18:00
        if sunset_calc:
            sunset_hour = int(sunset_calc.get_sunset_hour(tznow))
            sunrise_hour = int(sunset_calc.get_sunrise_hour(tznow))
        else:
            sunset_hour = 18  # Fallback
            sunrise_hour = 6  # Fallback
        
        if current_hour >= sunset_hour:
            for hour in range(current_hour, 24):
                night_energy += site_load_hourly.get(hour, 0.5)
            for hour in range(0, sunrise_hour):
                night_energy += site_load_hourly.get(hour, 0.5)
        elif current_hour <= sunrise_hour:
            for hour in range(current_hour, sunrise_hour):
                night_energy += site_load_hourly.get(hour, 0.5)
        return night_energy


class TariffManager:
    @staticmethod
    def is_in_peak_hours(tznow: pd.Timestamp, tariffs: Optional[List] = None) -> bool:
        """Check if current time is in peak hours."""
        if not tariffs:
            return False
        
        current_time = tznow.time()
        for tariff in tariffs:
            if getattr(tariff, "kind", None) == "peak":
                if tariff.start <= current_time < tariff.end:
                    return True
        return False

    @staticmethod
    def calculate_remaining_peak_energy(tznow: pd.Timestamp, site_load_hourly: Dict[int, float], tariffs: Optional[List] = None) -> Tuple[float, float]:
        """Calculate remaining peak hours and energy required."""
        if not tariffs:
            return 0.0, 0.0
        
        peak_tariffs = [t for t in tariffs if getattr(t, "kind", None) == "peak"]
        if not peak_tariffs:
            return 0.0, 0.0
        
        remaining_hours = 0.0
        remaining_energy = 0.0
        current_time = tznow
        
        for tariff in peak_tariffs:
            start_hour = tariff.start.hour
            end_hour = tariff.end.hour
            
            if current_time.hour < start_hour:
                # Peak period hasn't started yet
                remaining_hours += end_hour - start_hour
                for hour in range(start_hour, end_hour):
                    remaining_energy += site_load_hourly.get(hour, 0.8)  # Default 0.8kW if no data
            elif current_time.hour < end_hour:
                # Peak period is ongoing
                remaining_hours += end_hour - current_time.hour
                for hour in range(current_time.hour, end_hour):
                    remaining_energy += site_load_hourly.get(hour, 0.8)  # Default 0.8kW if no data
        
        return remaining_hours, remaining_energy

    @staticmethod
    def alloc_kwh_to_windows_avoiding_peak(required_kwh: float, sunset_h: int, tznow: pd.Timestamp, tariffs: Optional[List] = None) -> List[Tuple[str, str]]:
        """Allocate energy to charge windows while avoiding peak hours."""
        if not tariffs or required_kwh <= 0:
            return []
        
        # Get non-peak tariffs sorted by priority (cheapest first)
        non_peak_tariffs = [t for t in tariffs if getattr(t, "kind", None) != "peak" and getattr(t, "allow_grid_charge", True)]
        non_peak_tariffs.sort(key=lambda x: getattr(x, "price", 0))
        
        windows = []
        remaining_kwh = required_kwh
        current_time = tznow.time()
        
        for tariff in non_peak_tariffs:
            if remaining_kwh <= 0:
                break
            
            # Check if tariff window is still available (not in the past)
            if tariff.start > current_time:
                # This window is still available
                window_duration = TariffManager.calculate_window_duration_from_times(tariff.start, tariff.end)
                max_energy_in_window = window_duration * 3.0  # Assume 3kW max charge rate
                
                if max_energy_in_window >= remaining_kwh:
                    # This window can handle all remaining energy
                    windows.append((tariff.start.strftime("%H:%M"), tariff.end.strftime("%H:%M")))
                    remaining_kwh = 0
                else:
                    # Use this window and continue to next
                    windows.append((tariff.start.strftime("%H:%M"), tariff.end.strftime("%H:%M")))
                    remaining_kwh -= max_energy_in_window
        
        return windows[:3]  # Max 3 windows

    @staticmethod
    def calculate_window_duration(start_time: str, end_time: str) -> float:
        """Calculate duration of a time window in hours."""
        start_hour, start_min = map(int, start_time.split(':'))
        end_hour, end_min = map(int, end_time.split(':'))
        
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min
        
        if end_minutes <= start_minutes:
            end_minutes += 24 * 60  # Next day
        
        return (end_minutes - start_minutes) / 60.0

    @staticmethod
    def calculate_window_duration_from_times(start_time, end_time) -> float:
        """Calculate duration of a time window in hours from datetime.time objects."""
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        
        if end_minutes <= start_minutes:
            end_minutes += 24 * 60  # Next day
        
        return (end_minutes - start_minutes) / 60.0


class GridManager:
    @staticmethod
    def cap_grid_power_w(last_tel, model_cap: int) -> int:
        """Safe cap from register limits: min(model cap, Imax * Vbat)."""
        # Live limits
        try:
            if not last_tel:
                return model_cap  # No telemetry data, use model cap
            
            # Get battery current and voltage from telemetry
            # Handle both Telemetry objects and dictionaries
            if hasattr(last_tel, 'batt_current_a'):
                # Telemetry object - access directly
                batt_current = float(last_tel.batt_current_a or 0)
                batt_voltage = float(last_tel.batt_voltage_v or 0)
            elif hasattr(last_tel, 'get'):
                # Dictionary - access via get method - prefer standardized IDs
                batt_current = float(last_tel.get("battery_current_a") or last_tel.get("batt_current_a") or last_tel.get("battery_current", 0))
                batt_voltage = float(last_tel.get("battery_voltage_v") or last_tel.get("batt_voltage_v") or last_tel.get("battery_voltage", 0))
            else:
                return model_cap  # Unknown type, use model cap
            
            if batt_current > 0 and batt_voltage > 0:
                # Calculate max power based on battery limits
                max_power_from_battery = int(batt_current * batt_voltage)
                return min(model_cap, max_power_from_battery)
            else:
                return model_cap
        except (ValueError, TypeError):
            return model_cap


class InverterManager:
    @staticmethod
    def get_current_work_mode(telemetry) -> str:
        """Get current inverter work mode from telemetry (register 0x2100)."""
        if not telemetry:
            return "Unknown"
        
        # Handle both Telemetry objects and dictionaries
        if hasattr(telemetry, 'inverter_mode'):
            # Telemetry object - access directly
            work_mode = telemetry.inverter_mode
        elif isinstance(telemetry, dict):
            # Dictionary - check for standardized 'inverter_mode' first, then fallback to 'hybrid_work_mode'
            work_mode = telemetry.get("inverter_mode") or telemetry.get("hybrid_work_mode")
        else:
            return "Unknown"
        
        if work_mode is None:
            return "Unknown"
        
        # If it's already a string (enum value), return it directly
        if isinstance(work_mode, str):
            return work_mode
        
        # If it's a numeric value, map it to the string
        try:
            mode_map = {
                0: "Self used mode",
                1: "Time-based control", 
                2: "Backup mode",
                3: "Feed-in priority mode"
            }
            return mode_map.get(int(work_mode), f"Unknown mode ({work_mode})")
        except (ValueError, TypeError):
            # If conversion fails, return the value as-is
            return str(work_mode)

    @staticmethod
    def get_off_grid_mode_status(telemetry) -> bool:
        """Get off-grid mode status from telemetry (register 0x211C)."""
        if not telemetry:
            return False
        
        # Handle both Telemetry objects and dictionaries
        if hasattr(telemetry, 'extra') and telemetry.extra:
            # Telemetry object - access via extra field
            off_grid_mode = telemetry.extra.get("off_grid_mode")
        elif isinstance(telemetry, dict):
            # Dictionary - access via get method
            off_grid_mode = telemetry.get("off_grid_mode")
        else:
            return False
        
        return bool(off_grid_mode) if off_grid_mode is not None else False

    @staticmethod
    def get_off_grid_startup_soc(telemetry) -> int:
        """Get off-grid start-up battery capacity from telemetry (register 0x211F)."""
        if not telemetry:
            return 30  # Default 30%
        
        # Handle both Telemetry objects and dictionaries
        if hasattr(telemetry, 'extra') and telemetry.extra:
            # Telemetry object - access via extra field
            startup_soc = telemetry.extra.get("off_grid_start_up_battery_capacity")
        elif isinstance(telemetry, dict):
            # Dictionary - access via get method
            startup_soc = telemetry.get("off_grid_start_up_battery_capacity")
        else:
            return 30
        
        return int(startup_soc) if startup_soc is not None else 30


class SolarQualityAssessor:
    @staticmethod
    def assess_solar_production_quality(site_pv_today_kwh: float, 
                                       site_pv_hourly: Dict[int, float], 
                                       tznow: pd.Timestamp, 
                                       tomorrow_pv_kwh: float, 
                                       batt_kwh: float) -> float:
        """
        Assess solar production quality based on:
        - Today's actual vs forecasted production
        - Tomorrow's forecast
        - Time of day
        - Consistency of hourly production
        """
        # Today's production quality (actual vs forecast)
        today_forecast = sum(site_pv_hourly.values())
        if today_forecast > 0:
            today_ratio = min(site_pv_today_kwh / today_forecast, 2.0)  # Cap at 200%
        else:
            today_ratio = 0.0
        
        # Tomorrow's forecast quality (relative to battery capacity)
        tomorrow_ratio = min(tomorrow_pv_kwh / batt_kwh, 2.0)  # Cap at 200%
        
        # Time-based quality (better in morning/afternoon)
        current_hour = tznow.hour
        if 6 <= current_hour <= 10:  # Morning
            time_factor = 1.0
        elif 10 < current_hour <= 16:  # Peak solar hours
            time_factor = 1.2
        elif 16 < current_hour <= 18:  # Afternoon
            time_factor = 0.8
        else:  # Evening/night
            time_factor = 0.3
        
        # Consistency factor (how steady is the production)
        hourly_values = list(site_pv_hourly.values())
        if len(hourly_values) > 1:
            mean_production = sum(hourly_values) / len(hourly_values)
            variance = sum((x - mean_production) ** 2 for x in hourly_values) / len(hourly_values)
            consistency = 1.0 / (1.0 + variance / max(mean_production, 0.1))
        else:
            consistency = 0.5
        
        # Overall quality score (0.0 to 1.0+)
        overall_quality = (today_ratio * 0.3 + tomorrow_ratio * 0.3 + time_factor * 0.2 + consistency * 0.2)
        
        return min(overall_quality, 2.0)  # Cap at 200%


class DynamicWindowCalculator:
    @staticmethod
    def calculate_dynamic_self_use_windows(current_soc_pct: float, site_pv_hourly: Dict[int, float], 
                                          site_load_hourly: Dict[int, float], batt_kwh: float, 
                                          charge_target_soc_pct: float, grid_available: bool, 
                                          discharge_min_soc_pct: float = 20.0, solar_charge_deadline_h: int = 15) -> Dict[str, Any]:
        """
        Calculate dynamic charge/discharge windows for self-use mode based on:
        - Current SOC and target SOC
        - Hourly PV and load forecasts
        - Grid availability
        - Effective minimum SOC from ReliabilityManager
        """
        current_soc_kwh = (current_soc_pct / 100.0) * batt_kwh
        target_soc_kwh = (charge_target_soc_pct / 100.0) * batt_kwh
        energy_needed = target_soc_kwh - current_soc_kwh
        
        charge_windows = []
        discharge_windows = []
        grid_charge_windows = []
        
        # Calculate daily totals
        daily_pv_kwh = sum(site_pv_hourly.values())
        daily_load_kwh = sum(site_load_hourly.values())
        
        # If we need to charge and have excess PV
        if energy_needed > 0 and daily_pv_kwh > daily_load_kwh:
            excess_pv = daily_pv_kwh - daily_load_kwh
            if excess_pv >= energy_needed:
                # We have enough PV to reach target
                # Find best charging hours (high PV, low load) - only before solar charge deadline
                for hour in range(solar_charge_deadline_h + 1):  # Include deadline hour
                    pv_power = site_pv_hourly.get(hour, 0)
                    load_power = site_load_hourly.get(hour, 0)
                    net_pv = pv_power - load_power
                    
                    if net_pv > 0.5:  # At least 500W excess
                        charge_power = net_pv
                        charge_windows.append({
                            "start_hour": hour,
                            "end_hour": hour + 1,
                            "power_w": int(charge_power * 1000),
                            "target_soc": charge_target_soc_pct
                        })
        
        # If we have excess energy and grid is available, consider grid charging
        # Only use grid if solar is clearly insufficient (with margin for safety)
        elif energy_needed > 0 and grid_available and daily_pv_kwh < (daily_load_kwh * 0.8):
            # Use grid charging during off-peak hours
            for hour in range(22, 24):  # Late night
                grid_charge_windows.append({
                    "start_hour": hour,
                    "end_hour": hour + 1,
                    "power_w": int(1000),
                    "target_soc": charge_target_soc_pct
                })
            for hour in range(0, 6):  # Early morning
                grid_charge_windows.append({
                    "start_hour": hour,
                    "end_hour": hour + 1,
                    "power_w": int(1000),
                    "target_soc": charge_target_soc_pct
                })
        
        # If we have excess SOC, plan discharge windows
        elif energy_needed < 0:
            excess_energy = abs(energy_needed)
            # Find best discharge hours (high load, low PV)
            for hour in range(24):
                pv_power = site_pv_hourly.get(hour, 0)
                load_power = site_load_hourly.get(hour, 0)
                net_load = load_power - pv_power
                
                if net_load > 0.5:  # At least 500W net load
                    discharge_power = net_load
                    discharge_windows.append({
                        "start_hour": hour,
                        "end_hour": hour + 1,
                        "power_w": int(discharge_power * 1000),
                        "min_soc": max(discharge_min_soc_pct, current_soc_pct - 10)  # Don't go below minimum
                    })
        
        return {
            "charge_windows": charge_windows[:3],  # Max 3 windows
            "discharge_windows": discharge_windows[:3],
            "grid_charge_windows": grid_charge_windows[:3]
        }


