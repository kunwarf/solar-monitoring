from typing import Dict, Optional
import pytz, datetime as dt
import aiohttp
import time

class NaiveWeather:
    async def day_factors(self) -> Dict[str, float]:
        return {"today": 0.7, "tomorrow": 0.7}

class OpenMeteoWeather:
    def __init__(self, lat: float, lon: float, tz: str):
        self.lat, self.lon, self.tz = lat, lon, tz
        # Cache for API calls
        self._factors_cache: Optional[Dict[str, float]] = None
        self._factors_cache_time: Optional[float] = None
        self._cache_ttl_seconds = 300  # 5 minutes cache TTL
        
        # Unique cache key for this provider instance
        self._cache_key = f"openmeteo_basic_{self.lat}_{self.lon}_{self.tz}"
    
    async def day_factors(self) -> Dict[str, float]:
        try:
            # Check cache first
            current_time = time.time()
            if (self._factors_cache is not None and 
                self._factors_cache_time is not None and 
                current_time - self._factors_cache_time < self._cache_ttl_seconds):
                return self._factors_cache


            url = (f"https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lon}"
                   f"&hourly=cloud_cover&timezone={self.tz}&forecast_days=2")
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=10) as r:
                    js = await r.json()
            hours = js.get("hourly", {})
            cc = hours.get("cloud_cover", [])
            times = hours.get("time", [])
            tz = pytz.timezone(self.tz)

            today = dt.datetime.now(tz).date()
            tomorrow = today + dt.timedelta(days=1)
            def mean_for_day(day):
                vals = [c for t,c in zip(times, cc) if dt.datetime.fromisoformat(t).date()==day]
                if not vals: return 0.7
                m = sum(vals)/len(vals)
                return max(0.3, 1.0 - m/100.0)
            
            result = {"today": mean_for_day(today), "tomorrow": mean_for_day(tomorrow)}
            
            # Cache the result
            self._factors_cache = result
            self._factors_cache_time = current_time
            
            return result
        except Exception:
            return {"today": 0.7, "tomorrow": 0.7}
