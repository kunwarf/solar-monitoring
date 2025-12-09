#!/usr/bin/env python3
"""
Rebuild hourly_energy from energy_samples using Riemann sum integration.

Steps:
1) Purge all rows from hourly_energy
2) For each inverter_id and each hour between min(ts) and max(ts):
   - Calculate energy for that hour from power samples
   - Store into hourly_energy

Usage:
  python rebuild_hourly_energy.py [--db-path PATH] [--inverter ID] [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--no-purge]

Defaults:
  db path: ~/.solarhub/solarhub.db
  time range: inferred from energy_samples (configured timezone)
"""

import argparse
import logging
import os
import sqlite3
from datetime import datetime, timedelta

# Local imports
from solarhub.energy_calculator import EnergyCalculator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


def parse_date(s: str) -> datetime:
    return datetime.strptime(s, '%Y-%m-%d')


def get_db_connection(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def get_inverter_ids(conn: sqlite3.Connection) -> list[str]:
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT inverter_id FROM energy_samples WHERE inverter_id IS NOT NULL")
    rows = cur.fetchall()
    return [r[0] for r in rows if r and r[0] is not None]


def get_time_range(conn: sqlite3.Connection, inverter_id: str | None = None) -> tuple[datetime, datetime] | None:
    cur = conn.cursor()
    if inverter_id:
        cur.execute(
            "SELECT MIN(ts), MAX(ts) FROM energy_samples WHERE inverter_id = ? AND ts IS NOT NULL",
            (inverter_id,),
        )
    else:
        cur.execute("SELECT MIN(ts), MAX(ts) FROM energy_samples WHERE ts IS NOT NULL")
    row = cur.fetchone()
    if not row or not row[0] or not row[1]:
        return None
    # Timestamps in DB are ISO in configured timezone
    start = datetime.fromisoformat(str(row[0]))
    end = datetime.fromisoformat(str(row[1]))
    return (start, end)


def purge_hourly_energy(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM hourly_energy")
    conn.commit()
    log.info("Purged hourly_energy table")


def main():
    parser = argparse.ArgumentParser(description='Rebuild hourly_energy from energy_samples')
    default_db_path = os.path.expanduser('~/.solarhub/solarhub.db')
    parser.add_argument('--db-path', default=default_db_path, help=f'Database path (default: {default_db_path})')
    parser.add_argument('--inverter', default=None, help='Only process a specific inverter_id')
    parser.add_argument('--start', default=None, help='Start date (YYYY-MM-DD) inclusive, configured timezone')
    parser.add_argument('--end', default=None, help='End date (YYYY-MM-DD) inclusive, configured timezone')
    parser.add_argument('--no-purge', action='store_true', help='Do not purge hourly_energy before rebuilding')

    args = parser.parse_args()

    calc = EnergyCalculator(args.db_path)
    conn = get_db_connection(args.db_path)

    try:
        # Determine inverters
        inverter_ids = [args.inverter] if args.inverter else get_inverter_ids(conn)
        if not inverter_ids:
            log.info("No inverter_ids found in energy_samples. Nothing to do.")
            return 0

        # Global time range
        if args.start and args.end:
            start_dt = parse_date(args.start)
            end_dt = (parse_date(args.end) + timedelta(days=1))  # exclusive end
        else:
            tr = get_time_range(conn)
            if not tr:
                log.info("No timestamps found in energy_samples. Nothing to do.")
                return 0
            start_dt, max_dt = tr
            # Normalize to start of first day and end of last day
            start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end_dt = (max_dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))

        # Purge existing hourly data unless requested otherwise
        if not args.no_purge:
            purge_hourly_energy(conn)

        total_hours = 0
        for inv in inverter_ids:
            # Per-inverter time range if not explicitly provided
            if not (args.start and args.end):
                inv_tr = get_time_range(conn, inv)
                if not inv_tr:
                    log.info(f"No timestamps for inverter {inv}, skipping")
                    continue
                inv_start, inv_end = inv_tr
                inv_start = inv_start.replace(hour=0, minute=0, second=0, microsecond=0)
                inv_end = (inv_end.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
                s_dt, e_dt = inv_start, inv_end
            else:
                s_dt, e_dt = start_dt, end_dt

            log.info(f"Rebuilding hourly energy for inverter {inv} from {s_dt} to {e_dt}")

            current = s_dt
            while current < e_dt:
                try:
                    # Calculate and store for this hour
                    calc.calculate_and_store_hourly_energy(inv, current)
                except Exception as e:
                    log.warning(f"Failed hour {current} for inverter {inv}: {e}")
                current += timedelta(hours=1)
                total_hours += 1

        log.info(f"Rebuild completed. Hours processed: {total_hours}")
        return 0

    finally:
        conn.close()


if __name__ == '__main__':
    raise SystemExit(main())


