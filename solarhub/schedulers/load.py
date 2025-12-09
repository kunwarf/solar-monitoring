# solarhub/schedulers/load.py
from typing import Dict, Tuple, List
import pandas as pd
import sqlite3
from solarhub.daily_aggregator import DailyAggregator

class LoadLearner:
    """
    Learns hourly load (kW) per day-of-week from logged samples with seasonal learning.
    Falls back to a flat profile if no data.
    """
    def __init__(self, logger, tz: str = "Asia/Karachi") -> None:
        self.dblogger = logger
        self.tz = tz
        self.daily_aggregator = DailyAggregator(logger.path, tz)

    def hourly_load_profile(self, inverter_id: str | None = None, days_back: int = 60) -> Dict[Tuple[int,int], float]:
        """
        Learn hourly load profile from recent data only.
        Args:
            inverter_id: Inverter identifier (unused, kept for compatibility)
            days_back: Number of days of historical data to use (default: 60 days)
        """
        con = sqlite3.connect(self.dblogger.path)
        # Only load data from the last N days to avoid exponential slowdown
        from solarhub.timezone_utils import now_configured
        cutoff_date = (pd.Timestamp(now_configured()) - pd.Timedelta(days=days_back)).strftime('%Y-%m-%d %H:%M:%S')
        query = """
            SELECT ts, load_power_w 
            FROM energy_samples 
            WHERE ts >= ?
            ORDER BY ts DESC
            LIMIT 50000
        """
        df = pd.read_sql_query(query, con, params=[cutoff_date])
        con.close()
        if df.empty:
            return {}
        df['ts'] = pd.to_datetime(df['ts'], format='ISO8601', errors='coerce')
        # Convert to configured timezone if not already timezone-aware
        if df['ts'].dt.tz is None:
            df['ts'] = df['ts'].dt.tz_localize(self.tz)
        elif df['ts'].dt.tz != self.tz:
            df['ts'] = df['ts'].dt.tz_convert(self.tz)
        df['dow'] = df['ts'].dt.dayofweek  # 0=Mon ... 6=Sun
        df['hour'] = df['ts'].dt.hour
        # Use median to reduce outliers
        prof = df.groupby(['dow','hour'])['load_power_w'].median().fillna(0) / 1000.0  # -> kW
        # Normalize per-day-of-week to preserve relative shape (optional)
        return {(int(k[0]), int(k[1])): float(v) for k, v in prof.items()}

    def hourly_load_profile_hybrid(self, day_of_year: int, day_of_week: int,
                                  recent_days: int = 60, seasonal_years: int = 3) -> Dict[Tuple[int,int], float]:
        """
        Learn hourly load profile using hybrid approach:
        - Recent data (last N days) for current patterns
        - Seasonal data (same day-of-year from previous years) for seasonal patterns
        
        Args:
            day_of_year: Target day of year (1-366)
            day_of_week: Target day of week (0=Monday, 6=Sunday)
            recent_days: Number of recent days to use
            seasonal_years: Number of years to look back for seasonal data
            
        Returns:
            Dictionary mapping (day_of_week, hour) to load weights
        """
        # Get recent data (last N days)
        recent_data = self.daily_aggregator.get_recent_data(None, recent_days)
        
        # Get seasonal data (same day-of-year from previous years)
        seasonal_data = self.daily_aggregator.get_seasonal_data(day_of_year, None, seasonal_years)
        
        # Combine both approaches
        combined_profile = {}
        
        # Weight factors
        recent_weight = 0.7  # 70% weight to recent data
        seasonal_weight = 0.3  # 30% weight to seasonal data
        
        # Process recent data
        if recent_data:
            recent_profile = self._extract_hourly_load_profile_from_daily(recent_data)
            for (dow, hour), weight in recent_profile.items():
                combined_profile[(dow, hour)] = weight * recent_weight
        
        # Process seasonal data
        if seasonal_data:
            seasonal_profile = self._extract_hourly_load_profile_from_daily(seasonal_data)
            for (dow, hour), weight in seasonal_profile.items():
                key = (dow, hour)
                if key in combined_profile:
                    combined_profile[key] += weight * seasonal_weight
                else:
                    combined_profile[key] = weight * seasonal_weight
        
        # If no data available, fall back to original method
        if not combined_profile:
            return self.hourly_load_profile(None, recent_days)
        
        # Normalize the combined profile
        return self._normalize_load_profile(combined_profile)

    def _extract_hourly_load_profile_from_daily(self, daily_data: List[Dict]) -> Dict[Tuple[int,int], float]:
        """
        Extract hourly load profile from daily summary data.
        
        Args:
            daily_data: List of daily summary records
            
        Returns:
            Dictionary mapping (day_of_week, hour) to load weights
        """
        profile = {}
        
        for record in daily_data:
            # Calculate day of week from date
            date_str = record['date']
            dow = pd.Timestamp(date_str).dayofweek
            
            peak_hour = record.get('load_peak_hour')
            energy = record.get('load_energy_kwh', 0)
            
            if peak_hour is not None and energy > 0:
                # Create a simple bell curve around peak hour
                for hour in range(24):
                    # Gaussian-like distribution centered on peak hour
                    distance = abs(hour - peak_hour)
                    weight = max(0, 1 - (distance / 6) ** 2)  # 6-hour spread
                    key = (dow, hour)
                    if key in profile:
                        profile[key] += weight * energy
                    else:
                        profile[key] = weight * energy
        
        return profile

    def _normalize_load_profile(self, profile: Dict[Tuple[int,int], float]) -> Dict[Tuple[int,int], float]:
        """Normalize load profile so weights sum to 1.0 for each day of week."""
        # Group by day of week
        by_dow = {}
        for (dow, hour), weight in profile.items():
            if dow not in by_dow:
                by_dow[dow] = {}
            by_dow[dow][hour] = weight
        
        # Normalize each day
        normalized = {}
        for dow, hourly_weights in by_dow.items():
            total = sum(hourly_weights.values())
            if total > 0:
                for hour, weight in hourly_weights.items():
                    normalized[(dow, hour)] = weight / total
        
        return normalized

    def hourly_for_day(self, prof: Dict[Tuple[int,int], float], dow: int, fallback_kw: float = 1.0) -> Dict[int, float]:
        # If we don't have data, assume ~1 kW base load shape centered on evening
        hours = list(range(24))
        out = {}
        have = any((dow, h) in prof for h in hours)
        if not have:
            import numpy as np
            w = np.array([max(0, 1 - ((h-19)/6)**2) for h in hours])  # small evening bump
            w = w / (w.sum() + 1e-9)
            for h, ww in zip(hours, w):
                out[h] = float(fallback_kw * ww * 24)  # sum to fallback_kw * 24 kWh/day
            return out
        for h in hours:
            out[h] = float(prof.get((dow,h), 0.5))  # kW
        return out
