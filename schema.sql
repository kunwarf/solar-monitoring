CREATE TABLE energy_samples (
                ts TEXT NOT NULL,
                inverter_id TEXT NOT NULL,
                pv_power_w INTEGER,
                load_power_w INTEGER,
                grid_power_w INTEGER,
                batt_voltage_v REAL,
                batt_current_a REAL,
                soc REAL
            , battery_soc REAL, battery_voltage_v REAL, battery_current_a REAL, inverter_mode INTEGER, inverter_temp_c REAL, grid_import_wh REAL, grid_export_wh REAL, array_id TEXT);
CREATE TABLE pv_daily (
                day TEXT NOT NULL,
                inverter_id TEXT NOT NULL,
                pv_kwh REAL NOT NULL,
                PRIMARY KEY(day, inverter_id)
            );
CREATE TABLE daily_summary (
                    date TEXT NOT NULL,
                    inverter_id TEXT NOT NULL,
                    day_of_year INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    -- PV data
                    pv_energy_kwh REAL,
                    pv_max_power_w REAL,
                    pv_avg_power_w REAL,
                    pv_peak_hour INTEGER,
                    -- Load data
                    load_energy_kwh REAL,
                    load_max_power_w REAL,
                    load_avg_power_w REAL,
                    load_peak_hour INTEGER,
                    -- Battery data
                    battery_min_soc_pct REAL,
                    battery_max_soc_pct REAL,
                    battery_avg_soc_pct REAL,
                    battery_cycles REAL,
                    -- Grid data
                    grid_energy_imported_kwh REAL,
                    grid_energy_exported_kwh REAL,
                    grid_max_import_w REAL,
                    grid_max_export_w REAL,
                    -- Weather correlation
                    weather_factor REAL,
                    -- Metadata
                    sample_count INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (date, inverter_id)
                );
CREATE TABLE configuration (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source TEXT NOT NULL
            );
CREATE TABLE api_keys (
                    service TEXT PRIMARY KEY,
                    encrypted_key TEXT NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
CREATE TABLE inverter_config (
                inverter_id TEXT NOT NULL,
                sensor_id TEXT NOT NULL,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'api',
                PRIMARY KEY (inverter_id, sensor_id)
            );
CREATE TABLE system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                component TEXT NOT NULL,
                message TEXT NOT NULL,
                data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE schema_version (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL,
                description TEXT
            );
CREATE INDEX idx_daily_summary_doy
                ON daily_summary(day_of_year, inverter_id)
            ;
CREATE INDEX idx_daily_summary_date
                ON daily_summary(date DESC, inverter_id)
            ;
CREATE INDEX idx_daily_summary_year_doy
                ON daily_summary(year, day_of_year, inverter_id)
            ;
CREATE INDEX idx_energy_samples_inverter_ts
                ON energy_samples(inverter_id, ts DESC)
            ;
CREATE INDEX idx_energy_samples_ts
                ON energy_samples(ts DESC)
            ;
CREATE INDEX idx_energy_samples_timestamp
                ON energy_samples(ts)
            ;
CREATE INDEX idx_config_source
            ON configuration(source)
        ;
CREATE INDEX idx_inverter_config_inverter_id
            ON inverter_config(inverter_id)
        ;
CREATE INDEX idx_inverter_config_updated_at
            ON inverter_config(updated_at)
        ;
CREATE INDEX idx_system_logs_timestamp
            ON system_logs(timestamp)
        ;
CREATE INDEX idx_system_logs_level
            ON system_logs(level)
        ;
CREATE INDEX idx_system_logs_component
            ON system_logs(component)
        ;
CREATE TABLE sqlite_stat1(tbl,idx,stat);
CREATE TABLE IF NOT EXISTS "hourly_energy" (
                        inverter_id TEXT NOT NULL,
                        date TEXT NOT NULL,
                        hour_start INTEGER NOT NULL,
                        -- Energy data in kWh
                        solar_energy_kwh REAL,
                        load_energy_kwh REAL,
                        battery_charge_energy_kwh REAL,
                        battery_discharge_energy_kwh REAL,
                        grid_import_energy_kwh REAL,
                        grid_export_energy_kwh REAL,
                        -- Power data in watts (for reference)
                        avg_solar_power_w REAL,
                        avg_load_power_w REAL,
                        avg_battery_power_w REAL,
                        avg_grid_power_w REAL,
                        -- Metadata
                        sample_count INTEGER,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (inverter_id, date, hour_start)
                    );
CREATE INDEX idx_hourly_energy_inverter_date
            ON hourly_energy(inverter_id, date)
        ;
CREATE INDEX idx_hourly_energy_date_hour
            ON hourly_energy(date, hour_start)
        ;
CREATE INDEX idx_hourly_energy_inverter_id
            ON hourly_energy(inverter_id)
        ;
CREATE INDEX idx_hourly_energy_hour
                ON hourly_energy(hour_start, inverter_id)
            ;
CREATE TABLE battery_bank_samples (
                ts TEXT NOT NULL,
                bank_id TEXT NOT NULL,
                voltage REAL,
                current REAL,
                temperature REAL,
                soc REAL,
                batteries_count INTEGER,
                cells_per_battery INTEGER
            , pack_id TEXT, array_id TEXT);
CREATE TABLE battery_unit_samples (
                ts TEXT NOT NULL,
                bank_id TEXT NOT NULL,
                power INTEGER NOT NULL,
                voltage REAL,
                current REAL,
                temperature REAL,
                soc REAL,
                basic_st TEXT,
                volt_st TEXT,
                current_st TEXT,
                temp_st TEXT,
                soh_st TEXT,
                coul_st TEXT,
                heater_st TEXT,
                bat_events INTEGER,
                power_events INTEGER,
                sys_events INTEGER
            );
CREATE TABLE battery_cell_samples (
                ts TEXT NOT NULL,
                bank_id TEXT NOT NULL,
                power INTEGER NOT NULL,
                cell INTEGER NOT NULL,
                voltage REAL,
                temperature REAL,
                soc REAL,
                volt_st TEXT,
                temp_st TEXT
            );
CREATE TABLE arrays (
                array_id TEXT PRIMARY KEY,
                name TEXT
            );
CREATE TABLE battery_packs (
                pack_id TEXT PRIMARY KEY,
                name TEXT,
                chemistry TEXT,
                nominal_kwh REAL,
                max_charge_kw REAL,
                max_discharge_kw REAL
            );
CREATE TABLE battery_pack_attachments (
                pack_id TEXT,
                array_id TEXT,
                attached_since TEXT NOT NULL,
                detached_at TEXT,
                PRIMARY KEY (pack_id, attached_since)
            );
CREATE TABLE array_samples (
                ts TEXT NOT NULL,
                array_id TEXT NOT NULL,
                pv_power_w INTEGER,
                load_power_w INTEGER,
                grid_power_w INTEGER,
                batt_power_w INTEGER,
                batt_soc_pct REAL,
                batt_voltage_v REAL,
                batt_current_a REAL,
                PRIMARY KEY (ts, array_id)
            );
CREATE INDEX idx_energy_samples_array_id
            ON energy_samples(array_id)
        ;
CREATE INDEX idx_array_samples_array_id
            ON array_samples(array_id)
        ;
CREATE INDEX idx_array_samples_ts
            ON array_samples(ts)
        ;
CREATE INDEX idx_battery_pack_attachments_pack_id
            ON battery_pack_attachments(pack_id)
        ;
CREATE INDEX idx_battery_pack_attachments_array_id
            ON battery_pack_attachments(array_id)
        ;
CREATE TABLE inverter_setpoints (
                ts TEXT NOT NULL,
                array_id TEXT NOT NULL,
                inverter_id TEXT NOT NULL,
                action TEXT CHECK(action IN ('charge','discharge')),
                target_w INTEGER NOT NULL,
                headroom_w INTEGER,
                unmet_w INTEGER DEFAULT 0,
                PRIMARY KEY (ts, inverter_id, action)
            );
CREATE TABLE billing_daily (
                site_id TEXT NOT NULL DEFAULT 'default',
                date TEXT NOT NULL,
                billing_month_id TEXT,
                import_off_kwh REAL DEFAULT 0.0,
                export_off_kwh REAL DEFAULT 0.0,
                import_peak_kwh REAL DEFAULT 0.0,
                export_peak_kwh REAL DEFAULT 0.0,
                net_import_off_kwh REAL DEFAULT 0.0,
                net_import_peak_kwh REAL DEFAULT 0.0,
                credits_off_cycle_kwh_balance REAL DEFAULT 0.0,
                credits_peak_cycle_kwh_balance REAL DEFAULT 0.0,
                bill_off_energy_rs REAL DEFAULT 0.0,
                bill_peak_energy_rs REAL DEFAULT 0.0,
                fixed_prorated_rs REAL DEFAULT 0.0,
                expected_cycle_credit_rs REAL DEFAULT 0.0,
                bill_raw_rs_to_date REAL DEFAULT 0.0,
                bill_credit_balance_rs_to_date REAL DEFAULT 0.0,
                bill_final_rs_to_date REAL DEFAULT 0.0,
                surplus_deficit_flag TEXT CHECK(surplus_deficit_flag IN ('SURPLUS', 'DEFICIT', 'NEUTRAL')),
                generated_at_ts TEXT DEFAULT CURRENT_TIMESTAMP, home_id TEXT,
                PRIMARY KEY (site_id, date)
            );
CREATE TABLE billing_months (
                id TEXT PRIMARY KEY,
                billing_month TEXT NOT NULL,
                year INTEGER NOT NULL,
                month_number INTEGER NOT NULL,
                anchor_start TEXT NOT NULL,
                anchor_end TEXT NOT NULL,
                import_off_kwh REAL DEFAULT 0.0,
                export_off_kwh REAL DEFAULT 0.0,
                import_peak_kwh REAL DEFAULT 0.0,
                export_peak_kwh REAL DEFAULT 0.0,
                net_import_off_kwh REAL DEFAULT 0.0,
                net_import_peak_kwh REAL DEFAULT 0.0,
                solar_kwh REAL DEFAULT 0.0,
                load_kwh REAL DEFAULT 0.0,
                fixed_charge_rs REAL DEFAULT 0.0,
                cycle_credit_off_rs REAL DEFAULT 0.0,
                cycle_credit_peak_rs REAL DEFAULT 0.0,
                raw_bill_rs REAL DEFAULT 0.0,
                final_bill_rs REAL DEFAULT 0.0,
                credit_balance_after_rs REAL DEFAULT 0.0,
                config_hash TEXT,
                finalized_at_ts TEXT DEFAULT CURRENT_TIMESTAMP
            );
CREATE TABLE billing_cycles (
                id TEXT PRIMARY KEY,
                cycle_number INTEGER NOT NULL,
                year INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                credits_off_consumed_kwh REAL DEFAULT 0.0,
                credits_off_created_kwh REAL DEFAULT 0.0,
                credits_off_settled_rs REAL DEFAULT 0.0,
                credits_peak_consumed_kwh REAL DEFAULT 0.0,
                credits_peak_created_kwh REAL DEFAULT 0.0,
                credits_peak_settled_rs REAL DEFAULT 0.0,
                finalized_at_ts TEXT DEFAULT CURRENT_TIMESTAMP
            );
CREATE INDEX idx_billing_daily_date
            ON billing_daily(date)
        ;
CREATE INDEX idx_billing_daily_month_id
            ON billing_daily(billing_month_id)
        ;
CREATE INDEX idx_billing_months_year_month
            ON billing_months(year, month_number)
        ;
CREATE INDEX idx_billing_cycles_year
            ON billing_cycles(year)
        ;
CREATE TABLE device_discovery (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL UNIQUE,
                device_type TEXT NOT NULL,
                serial_number TEXT NOT NULL,
                port TEXT,
                last_known_port TEXT,
                port_history TEXT,
                adapter_config TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                failure_count INTEGER DEFAULT 0,
                next_retry_time TEXT,
                first_discovered TEXT NOT NULL,
                last_seen TEXT,
                discovery_timestamp TEXT NOT NULL,
                is_auto_discovered INTEGER DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
CREATE INDEX idx_device_discovery_serial
            ON device_discovery(serial_number, device_type)
        ;
CREATE INDEX idx_device_discovery_status
            ON device_discovery(status)
        ;
CREATE INDEX idx_device_discovery_port
            ON device_discovery(port)
        ;
CREATE TABLE meter_samples (
                ts TEXT NOT NULL,
                meter_id TEXT NOT NULL,
                array_id TEXT,
                grid_power_w INTEGER,
                grid_voltage_v REAL,
                grid_current_a REAL,
                grid_frequency_hz REAL,
                grid_import_wh INTEGER,
                grid_export_wh INTEGER,
                energy_kwh REAL,
                power_factor REAL,
                voltage_phase_a REAL,
                voltage_phase_b REAL,
                voltage_phase_c REAL,
                current_phase_a REAL,
                current_phase_b REAL,
                current_phase_c REAL,
                power_phase_a INTEGER,
                power_phase_b INTEGER,
                power_phase_c INTEGER
            );
CREATE TABLE meter_daily (
                day TEXT NOT NULL,
                meter_id TEXT NOT NULL,
                array_id TEXT,
                import_energy_kwh REAL NOT NULL DEFAULT 0,
                export_energy_kwh REAL NOT NULL DEFAULT 0,
                net_energy_kwh REAL NOT NULL DEFAULT 0,
                max_import_power_w INTEGER,
                max_export_power_w INTEGER,
                avg_voltage_v REAL,
                avg_current_a REAL,
                avg_frequency_hz REAL,
                sample_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(day, meter_id)
            );
CREATE INDEX idx_meter_samples_ts
            ON meter_samples(ts DESC, meter_id)
        ;
CREATE INDEX idx_meter_daily_day
            ON meter_daily(day DESC, meter_id)
        ;
CREATE INDEX idx_meter_daily_meter
            ON meter_daily(meter_id, day DESC)
        ;
CREATE TABLE meter_hourly_energy (
                meter_id TEXT NOT NULL,
                date TEXT NOT NULL,
                hour_start INTEGER NOT NULL,
                import_energy_kwh REAL DEFAULT 0.0,
                export_energy_kwh REAL DEFAULT 0.0,
                avg_power_w REAL,
                sample_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (meter_id, date, hour_start)
            );
CREATE INDEX idx_meter_hourly_energy_meter_date
            ON meter_hourly_energy(meter_id, date)
        ;
CREATE INDEX idx_meter_hourly_energy_date_hour
            ON meter_hourly_energy(date, hour_start)
        ;
CREATE UNIQUE INDEX idx_billing_daily_home_date
                ON billing_daily(home_id, date)
            ;
CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            );
CREATE INDEX idx_users_email ON users(email);
CREATE TABLE user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
CREATE INDEX idx_sessions_token ON user_sessions(token);
CREATE INDEX idx_sessions_user_id ON user_sessions(user_id);