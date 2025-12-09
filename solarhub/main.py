import os
import argparse
import asyncio
import logging
from pathlib import Path
import yaml

from solarhub.config import HubConfig
from solarhub.app import SolarApp
from solarhub.config_manager import ConfigurationManager
from solarhub.logging.logger import DataLogger


def _resolve_config_path(cli_path: str | None) -> Path:
    """
    Resolve config path with the following precedence:
    1) CLI: --config /path/to/config.yaml
    2) ENV: SOLARHUB_CONFIG=/path/to/config.yaml
    3) Default: <project_root>/config.yaml  (parent of the 'solarhub' package dir)
    """
    if cli_path:
        return Path(cli_path).expanduser().resolve()

    env = os.getenv("SOLARHUB_CONFIG")
    if env:
        return Path(env).expanduser().resolve()

    # project root = parent of this package directory
    return Path(__file__).resolve().parents[1] / "config.yaml"


def load_config(path: str | Path) -> HubConfig:
    """Load configuration from database with fallback to config.yaml file."""
    # Initialize database logger
    db_logger = DataLogger()

    # Normalize to string for ConfigurationManager (if it expects a str)
    path_str = str(Path(path).expanduser().resolve())

    # Initialize configuration manager
    config_manager = ConfigurationManager(path_str, db_logger)

    # Load configuration (database first, then file fallback)
    cfg = config_manager.load_config()

    # Migrate to array-based structure if needed (backward compatibility)
    from solarhub.config_migration import migrate_config_to_arrays
    cfg = migrate_config_to_arrays(cfg)

    # Backfill array_id in database if needed
    from solarhub.config_migration import build_inverter_to_array_map
    from solarhub.database_migrations import backfill_array_ids
    inverter_to_array_map = build_inverter_to_array_map(cfg)
    if inverter_to_array_map:
        try:
            backfill_array_ids(db_logger.path, inverter_to_array_map)
        except Exception as e:
            log = logging.getLogger(__name__)
            log.warning(f"Failed to backfill array_id in database: {e}")

    # Debug: Log which provider is being used
    log = logging.getLogger(__name__)
    try:
        log.info(f"Configuration loaded - Weather provider: {cfg.smart.forecast.provider}")
        if cfg.arrays:
            log.info(f"Configuration has {len(cfg.arrays)} arrays defined")
    except Exception:
        # Avoid crashing if structure differs
        log.info("Configuration loaded.")

    return cfg


async def amain(cfg_path: str | Path | None) -> None:
    log = logging.getLogger(__name__)
    try:
        cfg = load_config(_resolve_config_path(str(cfg_path) if cfg_path else None))
        app = SolarApp(cfg)
        log.info("Starting application initialization...")
        await app.init()
        log.info("Application initialization completed, starting main loop...")
        await app.run()
    except KeyboardInterrupt:
        log.info("Application interrupted by user")
        raise
    except Exception as e:
        log.error(f"Fatal error in application: {e}", exc_info=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="SolarHub")
    parser.add_argument(
        "--config",
        help="Path to config.yaml (overrides SOLARHUB_CONFIG and default).",
        required=False,
    )
    args = parser.parse_args()

    asyncio.run(amain(args.config))


if __name__ == "__main__":
    main()
