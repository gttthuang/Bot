from __future__ import annotations

import logging
import os

import httpx

from .models import EventType, JobEvent, SubscriptionConfig
from .utils import truncate

LOGGER = logging.getLogger(__name__)

COLORS = {
    EventType.JOB_CREATED: 0x2ECC71,
    EventType.JOB_UPDATED: 0xF39C12,
    EventType.JOB_CLOSED: 0xE74C3C,
}

LABELS = {
    EventType.JOB_CREATED: "NEW",
    EventType.JOB_UPDATED: "UPDATED",
    EventType.JOB_CLOSED: "CLOSED",
}


class DiscordWebhookNotifier:
    def __init__(self, timeout_seconds: int, dry_run: bool = False) -> None:
        self.timeout_seconds = timeout_seconds
        self.dry_run = dry_run

    def send(self, subscription: SubscriptionConfig, event: JobEvent) -> bool:
        if self.dry_run:
            LOGGER.info(
                "Dry run notification subscription=%s event=%s title=%s",
                subscription.name,
                event.event_type.value,
                event.job.title,
            )
            return True

        webhook_url = os.getenv(subscription.webhook_url_env)
        if not webhook_url:
            LOGGER.warning(
                "Skipping notification for subscription=%s because %s is unset",
                subscription.name,
                subscription.webhook_url_env,
            )
            return False

        payload = self._build_payload(subscription, event)
        response = httpx.post(webhook_url, json=payload, timeout=self.timeout_seconds)
        response.raise_for_status()
        return True

    def _build_payload(self, subscription: SubscriptionConfig, event: JobEvent) -> dict:
        job = event.job
        experience = job.experience_level or "unknown"
        locations = ", ".join(job.locations) or "unknown"

        embed = {
            "title": f"[{LABELS[event.event_type]}] {job.title}",
            "url": job.url,
            "color": COLORS[event.event_type],
            "fields": [
                {"name": "Company", "value": job.company or "unknown", "inline": True},
                {"name": "Source", "value": job.source_name, "inline": True},
                {"name": "Match", "value": subscription.name, "inline": True},
                {"name": "Experience", "value": experience, "inline": True},
                {"name": "Locations", "value": truncate(locations, 1000), "inline": False},
            ],
            "footer": {"text": f"event={event.event_type.value}"},
        }

        if job.source_updated_at:
            embed["timestamp"] = job.source_updated_at

        return {
            "username": "jobbot",
            "embeds": [embed],
        }
