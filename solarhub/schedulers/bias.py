from typing import Dict, Tuple, List
import pandas as pd
from solarhub.logging.logger import DataLogger
import sqlite3
import numpy as np
from solarhub.daily_aggregator import DailyAggregator

class BiasLearner:
    """Learns hourly PV profile per day-of-year from logged samples with seasonal learning."""
    def __init__(self, logger: DataLogger, tz: str = "Asia/Karachi") -> None:
        self.dblogger = logger
        self.tz = tz
        self.daily_aggregator = DailyAggregator(logger.path, tz)

    def hourly_pv_profile(self, inverter_id: str, days_back: int = 60) -> Dict[Tuple[int,int], float]:
        """
        Learn hourly PV profile from recent data only.
        Args:
            inverter_id: Inverter identifier
            days_back: Number of days of historical data to use (default: 60 days)
        """
        con = sqlite3.connect(self.dblogger.path)
        # Only load data from the last N days to avoid exponential slowdown
        from solarhub.timezone_utils import now_configured
        cutoff_date = (pd.Timestamp(now_configured()) - pd.Timedelta(days=days_back)).strftime('%Y-%m-%d %H:%M:%S')
        query = """
            SELECT ts, inverter_id, pv_power_w 
            FROM energy_samples 
            WHERE inverter_id = ? AND ts >= ?
            ORDER BY ts DESC
            LIMIT 50000
        """
        df = pd.read_sql_query(query, con, params=[inverter_id, cutoff_date])
        con.close()
        if df.empty:
            return {}
        df['ts'] = pd.to_datetime(df['ts'], format='ISO8601', errors='coerce')
        # Convert to configured timezone if not already timezone-aware
        if df['ts'].dt.tz is None:
            df['ts'] = df['ts'].dt.tz_localize(self.tz)
        elif df['ts'].dt.tz != self.tz:
            df['ts'] = df['ts'].dt.tz_convert(self.tz)
        df['doy'] = df['ts'].dt.dayofyear
        df['hour'] = df['ts'].dt.hour
        prof = df.groupby(['doy','hour'])['pv_power_w'].median().fillna(0)
        prof = prof / (prof.groupby(level=0).sum() + 1e-6)
        return {(int(k[0]), int(k[1])): float(v) for k,v in prof.items()}

    def hourly_pv_profile_hybrid(self, inverter_id: str, day_of_year: int, 
                                recent_days: int = 60, seasonal_years: int = 3) -> Dict[Tuple[int,int], float]:
        """
        Learn hourly PV profile using hybrid approach:
        - Recent data (last N days) for current patterns
        - Seasonal data (same day-of-year from previous years) for seasonal patterns
        
        Args:
            inverter_id: Inverter identifier
            day_of_year: Target day of year (1-366)
            recent_days: Number of recent days to use
            seasonal_years: Number of years to look back for seasonal data
            
        Returns:
            Dictionary mapping (day_of_year, hour) to normalized power weights
        """
        # Get recent data (last N days)
        recent_data = self.daily_aggregator.get_recent_data(inverter_id, recent_days)
        
        # Get seasonal data (same day-of-year from previous years)
        seasonal_data = self.daily_aggregator.get_seasonal_data(day_of_year, inverter_id, seasonal_years)
        
        # Combine both approaches
        combined_profile = {}
        
        # Weight factors
        recent_weight = 0.7  # 70% weight to recent data
        seasonal_weight = 0.3  # 30% weight to seasonal data
        
        # Process recent data
        if recent_data:
            recent_profile = self._extract_hourly_profile_from_daily(recent_data, 'pv')
            for (doy, hour), weight in recent_profile.items():
                combined_profile[(doy, hour)] = weight * recent_weight
        
        # Process seasonal data
        if seasonal_data:
            seasonal_profile = self._extract_hourly_profile_from_daily(seasonal_data, 'pv')
            for (doy, hour), weight in seasonal_profile.items():
                key = (doy, hour)
                if key in combined_profile:
                    combined_profile[key] += weight * seasonal_weight
                else:
                    combined_profile[key] = weight * seasonal_weight
        
        # If no data available, fall back to original method
        if not combined_profile:
            return self.hourly_pv_profile(inverter_id, recent_days)
        
        # Normalize the combined profile
        return self._normalize_profile(combined_profile)

    def _extract_hourly_profile_from_daily(self, daily_data: List[Dict], data_type: str) -> Dict[Tuple[int,int], float]:
        """
        Extract hourly profile from daily summary data.
        
        Args:
            daily_data: List of daily summary records
            data_type: Type of data ('pv' or 'load')
            
        Returns:
            Dictionary mapping (day_of_year, hour) to weights
        """
        profile = {}
        
        for record in daily_data:
            doy = record['day_of_year']
            
            # For now, create a simple profile based on peak hour
            # This could be enhanced with actual hourly data if available
            if data_type == 'pv':
                peak_hour = record.get('pv_peak_hour')
                energy = record.get('pv_energy_kwh', 0)
            else:
                peak_hour = record.get('load_peak_hour')
                energy = record.get('load_energy_kwh', 0)
            
            if peak_hour is not None and energy > 0:
                # Create a simple bell curve around peak hour
                for hour in range(24):
                    # Gaussian-like distribution centered on peak hour
                    distance = abs(hour - peak_hour)
                    weight = max(0, 1 - (distance / 6) ** 2)  # 6-hour spread
                    key = (doy, hour)
                    if key in profile:
                        profile[key] += weight * energy
                    else:
                        profile[key] = weight * energy
        
        return profile

    def _normalize_profile(self, profile: Dict[Tuple[int,int], float]) -> Dict[Tuple[int,int], float]:
        """Normalize profile so weights sum to 1.0 for each day of year."""
        # Group by day of year
        by_doy = {}
        for (doy, hour), weight in profile.items():
            if doy not in by_doy:
                by_doy[doy] = {}
            by_doy[doy][hour] = weight
        
        # Normalize each day
        normalized = {}
        for doy, hourly_weights in by_doy.items():
            total = sum(hourly_weights.values())
            if total > 0:
                for hour, weight in hourly_weights.items():
                    normalized[(doy, hour)] = weight / total
        
        return normalized

    def blend_forecast(self, pv_kwh_forecast: float, prof: Dict[Tuple[int,int], float], day_of_year: int) -> Dict[int, float]:
        import numpy as np
        hours = list(range(24))
        weights = np.array([prof.get((day_of_year,h), 0.0) for h in hours])
        if weights.sum() <= 0:
            weights = np.array([max(0, 1 - ((h-12)/6)**2) for h in hours])
        weights = weights / (weights.sum() + 1e-9)
        kwh_by_hour = {h: float(pv_kwh_forecast * w) for h,w in zip(hours, weights)}
        return kwh_by_hour
