from __future__ import annotations

import logging

from .models import (
    AppConfig,
    EventType,
    JobEvent,
    JobStatus,
    SourceConfig,
    SourceRunStats,
    StoredJobState,
)
from .notifiers import DiscordWebhookNotifier
from .rules import matches_subscription
from .store import SQLiteStore
from .sources import GoogleCareersSource
from .utils import utc_now_iso

LOGGER = logging.getLogger(__name__)

SOURCE_REGISTRY = {
    "google_careers": GoogleCareersSource,
}


class JobMonitorService:
    def __init__(
        self,
        config: AppConfig,
        store: SQLiteStore,
        notifier: DiscordWebhookNotifier,
    ) -> None:
        self.config = config
        self.store = store
        self.notifier = notifier

    def run_once(self) -> list[SourceRunStats]:
        run_at = utc_now_iso()
        summaries: list[SourceRunStats] = []

        for source_config in self.config.sources:
            if not source_config.enabled:
                continue
            summary = self._run_source(source_config, run_at)
            self.store.record_run(run_at, summary)
            summaries.append(summary)

        return summaries

    def _run_source(self, source_config: SourceConfig, run_at: str) -> SourceRunStats:
        summary = SourceRunStats(source_name=source_config.name)

        try:
            source_cls = SOURCE_REGISTRY[source_config.provider]
        except KeyError:
            summary.error = f"Unsupported provider: {source_config.provider}"
            LOGGER.error(summary.error)
            return summary

        try:
            source = source_cls(source_config, self.config.settings)
            jobs = source.fetch_jobs()
        except Exception as exc:
            summary.error = str(exc)
            LOGGER.exception("Source crawl failed source=%s", source_config.name)
            return summary

        summary.discovered_count = len(jobs)
        events = self._reconcile_source(source_config, jobs, run_at, summary)
        summary.notified_count = self._dispatch(events)
        return summary

    def _reconcile_source(
        self,
        source_config: SourceConfig,
        jobs: list,
        run_at: str,
        summary: SourceRunStats,
    ) -> list[JobEvent]:
        existing = self.store.load_states_for_source(source_config.name)
        current_ids: set[str] = set()
        events: list[JobEvent] = []

        for job in jobs:
            current_ids.add(job.external_id)
            current_hash = job.content_hash()
            previous = existing.get(job.external_id)

            if previous is None or previous.status == JobStatus.CLOSED:
                state = StoredJobState(
                    source_name=job.source_name,
                    external_id=job.external_id,
                    status=JobStatus.ACTIVE,
                    first_seen_at=run_at,
                    last_seen_at=run_at,
                    missing_count=0,
                    closed_at=None,
                    content_hash=current_hash,
                    payload=job.to_dict(),
                )
                self.store.save_state(state)
                events.append(JobEvent(EventType.JOB_CREATED, job))
                summary.created_count += 1
                continue

            event_type: EventType | None = None
            if previous.content_hash != current_hash:
                event_type = EventType.JOB_UPDATED
                summary.updated_count += 1

            state = StoredJobState(
                source_name=job.source_name,
                external_id=job.external_id,
                status=JobStatus.ACTIVE,
                first_seen_at=previous.first_seen_at,
                last_seen_at=run_at,
                missing_count=0,
                closed_at=None,
                content_hash=current_hash,
                payload=job.to_dict(),
            )
            self.store.save_state(state)

            if event_type is not None:
                events.append(JobEvent(event_type, job))

        for external_id, previous in existing.items():
            if external_id in current_ids or previous.status == JobStatus.CLOSED:
                continue

            missing_count = previous.missing_count + 1
            if missing_count >= self.config.settings.close_after_missing_runs:
                closed_state = StoredJobState(
                    source_name=previous.source_name,
                    external_id=previous.external_id,
                    status=JobStatus.CLOSED,
                    first_seen_at=previous.first_seen_at,
                    last_seen_at=previous.last_seen_at,
                    missing_count=missing_count,
                    closed_at=run_at,
                    content_hash=previous.content_hash,
                    payload=previous.payload,
                )
                self.store.save_state(closed_state)
                events.append(
                    JobEvent(
                        EventType.JOB_CLOSED,
                        previous.to_job(),
                    )
                )
                summary.closed_count += 1
            else:
                missing_state = StoredJobState(
                    source_name=previous.source_name,
                    external_id=previous.external_id,
                    status=JobStatus.MISSING,
                    first_seen_at=previous.first_seen_at,
                    last_seen_at=previous.last_seen_at,
                    missing_count=missing_count,
                    closed_at=None,
                    content_hash=previous.content_hash,
                    payload=previous.payload,
                )
                self.store.save_state(missing_state)

        return events

    def _dispatch(self, events: list[JobEvent]) -> int:
        delivered = 0

        for event in events:
            for subscription in self.config.subscriptions:
                if not subscription.enabled:
                    continue
                if not subscription.should_notify(event.event_type):
                    continue
                if not matches_subscription(event.job, subscription):
                    continue
                try:
                    if self.notifier.send(subscription, event):
                        delivered += 1
                except Exception:
                    LOGGER.exception(
                        "Notification failed subscription=%s event=%s job=%s",
                        subscription.name,
                        event.event_type.value,
                        event.job.external_id,
                    )

        return delivered
