from __future__ import annotations

import os
from pathlib import Path

import yaml

from .models import AppConfig, Settings, SourceConfig, SubscriptionConfig

DEFAULT_USER_AGENT = "jobbot/0.1 (+https://github.com/placeholder/jobbot; contact: update-this-user-agent-before-heavy-use)"


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path).expanduser().resolve()
    raw_text = os.path.expandvars(config_path.read_text(encoding="utf-8"))
    data = yaml.safe_load(raw_text) or {}

    settings_raw = dict(data.get("settings", {}))
    database_path = settings_raw.get("database_path", "data/jobbot.db")
    database_path = Path(database_path)
    if not database_path.is_absolute():
        database_path = (config_path.parent / database_path).resolve()

    settings = Settings(
        database_path=str(database_path),
        close_after_missing_runs=int(settings_raw.get("close_after_missing_runs", 3)),
        request_timeout_seconds=int(settings_raw.get("request_timeout_seconds", 30)),
        user_agent=str(
            settings_raw.get(
                "user_agent",
                DEFAULT_USER_AGENT,
            )
        ),
    )

    sources = [SourceConfig.from_mapping(item) for item in data.get("sources", [])]
    subscriptions = [
        SubscriptionConfig.from_mapping(item) for item in data.get("subscriptions", [])
    ]

    if not sources:
        raise ValueError(f"No sources configured in {config_path}")
    if not subscriptions:
        raise ValueError(f"No subscriptions configured in {config_path}")

    return AppConfig(settings=settings, sources=sources, subscriptions=subscriptions)
