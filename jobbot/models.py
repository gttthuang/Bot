from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
from typing import Any

from .utils import html_to_text

JsonDict = dict[str, Any]


class EventType(StrEnum):
    JOB_CREATED = "job_created"
    JOB_UPDATED = "job_updated"
    JOB_CLOSED = "job_closed"


class JobStatus(StrEnum):
    ACTIVE = "active"
    MISSING = "missing"
    CLOSED = "closed"


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


@dataclass(slots=True)
class Settings:
    database_path: str = "data/jobbot.db"
    close_after_missing_runs: int = 3
    request_timeout_seconds: int = 30
    user_agent: str = (
        "jobbot/0.1 (+https://github.com/placeholder/jobbot; "
        "contact: update-this-user-agent-before-heavy-use)"
    )


@dataclass(slots=True)
class SourceConfig:
    name: str
    provider: str
    urls: list[str]
    enabled: bool = True
    company: str | None = None
    headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "SourceConfig":
        return cls(
            name=str(raw["name"]),
            provider=str(raw["provider"]),
            urls=_as_string_list(raw.get("urls")),
            enabled=bool(raw.get("enabled", True)),
            company=str(raw["company"]) if raw.get("company") else None,
            headers={str(key): str(value) for key, value in dict(raw.get("headers", {})).items()},
        )


@dataclass(slots=True)
class SubscriptionConfig:
    name: str
    source_names: list[str] = field(default_factory=list)
    enabled: bool = True
    experience_include: list[str] = field(default_factory=list)
    experience_exclude: list[str] = field(default_factory=list)
    company_include: list[str] = field(default_factory=list)
    company_exclude: list[str] = field(default_factory=list)
    title_include: list[str] = field(default_factory=list)
    title_exclude: list[str] = field(default_factory=list)
    location_include: list[str] = field(default_factory=list)
    location_exclude: list[str] = field(default_factory=list)
    text_include: list[str] = field(default_factory=list)
    text_exclude: list[str] = field(default_factory=list)
    notify_events: list[str] = field(
        default_factory=lambda: [event.value for event in EventType]
    )
    webhook_url_env: str = "DISCORD_WEBHOOK_URL"

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "SubscriptionConfig":
        return cls(
            name=str(raw["name"]),
            source_names=_as_string_list(raw.get("source_names")),
            enabled=bool(raw.get("enabled", True)),
            experience_include=_as_string_list(raw.get("experience_include")),
            experience_exclude=_as_string_list(raw.get("experience_exclude")),
            company_include=_as_string_list(raw.get("company_include")),
            company_exclude=_as_string_list(raw.get("company_exclude")),
            title_include=_as_string_list(raw.get("title_include")),
            title_exclude=_as_string_list(raw.get("title_exclude")),
            location_include=_as_string_list(raw.get("location_include")),
            location_exclude=_as_string_list(raw.get("location_exclude")),
            text_include=_as_string_list(raw.get("text_include")),
            text_exclude=_as_string_list(raw.get("text_exclude")),
            notify_events=_as_string_list(raw.get("notify_events"))
            or [event.value for event in EventType],
            webhook_url_env=str(raw.get("webhook_url_env", "DISCORD_WEBHOOK_URL")),
        )

    def should_notify(self, event_type: EventType) -> bool:
        return event_type.value in self.notify_events


@dataclass(slots=True)
class AppConfig:
    settings: Settings
    sources: list[SourceConfig]
    subscriptions: list[SubscriptionConfig]


@dataclass(slots=True)
class JobPosting:
    source_name: str
    source_provider: str
    external_id: str
    title: str
    url: str
    company: str
    locale: str
    experience_level: str | None = None
    locations: list[str] = field(default_factory=list)
    description_html: str = ""
    responsibilities_html: str = ""
    qualifications_html: str = ""
    source_updated_at: str | None = None

    @property
    def description_text(self) -> str:
        return html_to_text(self.description_html)

    @property
    def responsibilities_text(self) -> str:
        return html_to_text(self.responsibilities_html)

    @property
    def qualifications_text(self) -> str:
        return html_to_text(self.qualifications_html)

    @property
    def searchable_text(self) -> str:
        parts = [
            self.title,
            self.company,
            self.locale,
            self.experience_level or "",
            " ".join(self.locations),
            self.description_text,
            self.responsibilities_text,
            self.qualifications_text,
        ]
        return " ".join(part for part in parts if part)

    def snapshot(self) -> JsonDict:
        return {
            "source_name": self.source_name,
            "source_provider": self.source_provider,
            "external_id": self.external_id,
            "title": self.title,
            "url": self.url,
            "company": self.company,
            "locale": self.locale,
            "experience_level": self.experience_level,
            "locations": self.locations,
            "description_html": self.description_html,
            "responsibilities_html": self.responsibilities_html,
            "qualifications_html": self.qualifications_html,
        }

    def content_hash(self) -> str:
        payload = json.dumps(self.snapshot(), ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> JsonDict:
        payload = self.snapshot()
        payload["source_updated_at"] = self.source_updated_at
        return payload

    @classmethod
    def from_dict(cls, raw: JsonDict) -> "JobPosting":
        return cls(
            source_name=str(raw["source_name"]),
            source_provider=str(raw["source_provider"]),
            external_id=str(raw["external_id"]),
            title=str(raw["title"]),
            url=str(raw["url"]),
            company=str(raw["company"]),
            locale=str(raw.get("locale", "")),
            experience_level=(
                str(raw["experience_level"]) if raw.get("experience_level") is not None else None
            ),
            locations=_as_string_list(raw.get("locations")),
            description_html=str(raw.get("description_html", "")),
            responsibilities_html=str(raw.get("responsibilities_html", "")),
            qualifications_html=str(raw.get("qualifications_html", "")),
            source_updated_at=(
                str(raw["source_updated_at"]) if raw.get("source_updated_at") else None
            ),
        )


@dataclass(slots=True)
class JobEvent:
    event_type: EventType
    job: JobPosting


@dataclass(slots=True)
class StoredJobState:
    source_name: str
    external_id: str
    status: JobStatus
    first_seen_at: str
    last_seen_at: str
    missing_count: int
    closed_at: str | None
    content_hash: str
    payload: JsonDict

    def to_job(self) -> JobPosting:
        return JobPosting.from_dict(self.payload)


@dataclass(slots=True)
class SourceRunStats:
    source_name: str
    discovered_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    closed_count: int = 0
    notified_count: int = 0
    error: str | None = None
