from __future__ import annotations

import logging
import os

from .config import load_config
from .models import SourceRunStats
from .notifiers import DiscordWebhookNotifier
from .service import JobMonitorService
from .store import SQLiteStore

DEFAULT_CONFIG_PATH = "configs/config.yaml"


def main() -> int:
    config_path = os.getenv("JOBBOT_CONFIG", DEFAULT_CONFIG_PATH)
    dry_run = _env_flag("JOBBOT_DRY_RUN")
    log_level = os.getenv("JOBBOT_LOG_LEVEL", "INFO").upper()

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    config = load_config(config_path)
    store = SQLiteStore(config.settings.database_path)
    notifier = DiscordWebhookNotifier(
        timeout_seconds=config.settings.request_timeout_seconds,
        dry_run=dry_run,
    )
    service = JobMonitorService(config=config, store=store, notifier=notifier)

    try:
        _print_stats(service.run_once())
    finally:
        store.close()

    return 0


def _env_flag(name: str) -> bool:
    value = os.getenv(name, "")
    return value.casefold() in {"1", "true", "yes", "on"}


def _print_stats(stats: list[SourceRunStats]) -> None:
    for item in stats:
        logging.info(
            "source=%s discovered=%s created=%s updated=%s closed=%s notified=%s error=%s",
            item.source_name,
            item.discovered_count,
            item.created_count,
            item.updated_count,
            item.closed_count,
            item.notified_count,
            item.error or "-",
        )
