from typing import Dict, Optional
import pandas as pd, pvlib
import logging

log = logging.getLogger(__name__)

class PvlibSolarEstimator:
    def __init__(self, cfg):
        self.cfg = cfg
    
    async def estimate_daily_pv_kwh(self, weather_factor: float, 
                                   enhanced_weather: Optional[Dict] = None) -> float:
        """
        Estimate daily PV generation with enhanced weather data.
        Args:
            weather_factor: Simple weather factor (for compatibility)
            enhanced_weather: Enhanced weather data with multiple factors
            
        Returns:
            Estimated daily PV generation in kWh
        """

        try:
            from solarhub.timezone_utils import get_configured_timezone
            tz = str(get_configured_timezone())
            location = pvlib.location.Location(self.cfg.lat, self.cfg.lon, tz=tz)
            from solarhub.timezone_utils import now_configured
            start = pd.Timestamp(now_configured()).normalize()
            end = start + pd.Timedelta(days=1)
            times = pd.date_range(start, end, freq='15min', tz=tz, inclusive='left')
            
            # Get clear sky irradiance
            cs = location.get_clearsky(times, model='ineichen')
            solpos = location.get_solarposition(times)
            
            # Calculate POA irradiance
            poa = pvlib.irradiance.get_total_irradiance(
                surface_tilt=self.cfg.tilt_deg,
                surface_azimuth=self.cfg.azimuth_deg,
                solar_zenith=solpos['apparent_zenith'],
                solar_azimuth=solpos['azimuth'],
                dni=cs['dni'], ghi=cs['ghi'], dhi=cs['dhi'], albedo=self.cfg.albedo)
            
            # Apply weather factors
            if enhanced_weather:
                # Use enhanced weather data for more accurate estimation
                poa_irr = self._apply_enhanced_weather_factors(
                    poa['poa_global'], times, enhanced_weather)
            else:
                # Fallback to simple weather factor
                poa_irr = poa['poa_global'].clip(lower=0) * weather_factor
            
            # Calculate energy generation
            dt_h = (times[1]-times[0]).total_seconds()/3600.0
            kwh = float(poa_irr.sum()/1000.0 * dt_h * self.cfg.pv_perf_ratio * self.cfg.pv_dc_kw)
            
            return round(kwh, 2)
            
        except Exception as e:
            log.warning(f"PV estimation error: {e}")
            # Fallback calculation
            base_h = 5.0
            factor = enhanced_weather.get('overall_factor', weather_factor) if enhanced_weather else weather_factor
            return round(self.cfg.pv_dc_kw * self.cfg.pv_perf_ratio * base_h * factor, 2)
    
    def _apply_enhanced_weather_factors(self, poa_irradiance: pd.Series, 
                                      times: pd.DatetimeIndex, 
                                      weather_data: Dict) -> pd.Series:
        """Apply enhanced weather factors to POA irradiance."""
        # Start with clear sky irradiance
        adjusted_irr = poa_irradiance.clip(lower=0).copy()
        
        # Apply irradiance factor (cloud cover, actual radiation)
        irradiance_factor = weather_data.get('irradiance_factor', 1.0)
        adjusted_irr *= irradiance_factor
        
        # Apply temperature factor (hourly variation)
        temp_factor = weather_data.get('temperature_factor', 1.0)
        adjusted_irr *= temp_factor
        
        # Apply soiling factor (daily constant)
        soiling_factor = weather_data.get('soiling_factor', 1.0)
        adjusted_irr *= soiling_factor
        
        # Apply wind factor (cooling effect)
        wind_factor = weather_data.get('wind_factor', 1.0)
        adjusted_irr *= wind_factor
        
        # Ensure non-negative values
        return adjusted_irr.clip(lower=0)
    
    async def estimate_hourly_pv_kwh(self, weather_data: Dict) -> Dict[int, float]:
        """
        Estimate hourly PV generation for better scheduling.
        
        Args:
            weather_data: Enhanced weather data with hourly factors
            
        Returns:
            Dictionary mapping hour (0-23) to estimated kWh
        """
        try:
            from solarhub.timezone_utils import get_configured_timezone
            tz = str(get_configured_timezone())
            location = pvlib.location.Location(self.cfg.lat, self.cfg.lon, tz=tz)
            
            hourly_kwh = {}
            
            for hour in range(24):
                # Create hourly time range
                from solarhub.timezone_utils import now_configured
                start = pd.Timestamp(now_configured()).normalize() + pd.Timedelta(hours=hour)
                end = start + pd.Timedelta(hours=1)
                times = pd.date_range(start, end, freq='15min', tz=tz, inclusive='left')
                
                # Get clear sky irradiance for this hour
                cs = location.get_clearsky(times, model='ineichen')
                solpos = location.get_solarposition(times)
                
                # Calculate POA irradiance
                poa = pvlib.irradiance.get_total_irradiance(
                    surface_tilt=self.cfg.tilt_deg,
                    surface_azimuth=self.cfg.azimuth_deg,
                    solar_zenith=solpos['apparent_zenith'],
                    solar_azimuth=solpos['azimuth'],
                    dni=cs['dni'], ghi=cs['ghi'], dhi=cs['dhi'], albedo=self.cfg.albedo)
                
                # Apply weather factors
                poa_irr = self._apply_enhanced_weather_factors(
                    poa['poa_global'], times, weather_data)
                
                # Calculate hourly energy
                dt_h = (times[1]-times[0]).total_seconds()/3600.0
                kwh = float(poa_irr.sum()/1000.0 * dt_h * self.cfg.pv_perf_ratio * self.cfg.pv_dc_kw)
                
                hourly_kwh[hour] = round(kwh, 3)
            
            return hourly_kwh
            
        except Exception as e:
            log.warning(f"Hourly PV estimation error: {e}")
            # Fallback: simple bell curve
            hourly_kwh = {}
            for hour in range(24):
                # Simple bell curve centered at noon
                factor = max(0, 1 - ((hour - 12) / 6) ** 2)
                kwh = self.cfg.pv_dc_kw * self.cfg.pv_perf_ratio * factor * 0.2
                hourly_kwh[hour] = round(kwh, 3)
            return hourly_kwh
