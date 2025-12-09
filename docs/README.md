# SolarHub — Multi-Inverter Monitor & Smart Scheduler (Senergy Modbus RTU)

Features:
- Async Modbus RTU polling (pymodbus) with brand adapter (`SenergyAdapter`)
- MQTT telemetry & commands; Home Assistant MQTT Discovery (sensors + controls)
- Full-register snapshot → HA sensors for *every* register from your spec
- Smart scheduler with PV forecast (Open-Meteo + pvlib) and per-array parameters
- SQLite logging of samples and daily PV kWh
- Bias learner builds an hourly PV shape per day-of-year to refine forecasts
- Hourly plan executor: sets grid-charge windows, end-SOC caps, and emits plan

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m solarhub.main --config config.yaml
```

See `config.example.yaml` for all settings.


## Multiple arrays per inverter
Each inverter's `solar:` is now a list of arrays, each with its own kW/tilt/azimuth/PR. The forecast sums all arrays per inverter.
