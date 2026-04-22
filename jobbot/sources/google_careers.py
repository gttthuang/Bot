from __future__ import annotations

from datetime import UTC, datetime
from html import unescape
import re
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit

import chompjs
import httpx

from ..models import JobPosting
from ..utils import dedupe_preserve_order
from .base import JobSource

CALLBACK_RE = re.compile(r"AF_initDataCallback\((\{.*?\})\);", re.DOTALL)
NEXT_PAGE_RE = re.compile(
    r'href="([^"]+page=\d+[^"]*)"[^>]*aria-label="Go to next page"',
    re.IGNORECASE,
)
EXPERIENCE_LEVEL_MAP = {
    1: "early",
    2: "mid",
    3: "advanced",
}


class GoogleCareersSource(JobSource):
    def fetch_jobs(self) -> list[JobPosting]:
        jobs_by_id: dict[str, JobPosting] = {}
        pending_urls = list(self.config.urls)
        visited_urls: set[str] = set()
        headers = {
            "user-agent": self.settings.user_agent,
            "accept-language": "en-US,en;q=0.9",
            **self.config.headers,
        }

        with httpx.Client(
            follow_redirects=True,
            timeout=self.settings.request_timeout_seconds,
            headers=headers,
        ) as client:
            while pending_urls:
                url = pending_urls.pop(0)
                if url in visited_urls:
                    continue
                visited_urls.add(url)
                response = client.get(url)
                response.raise_for_status()
                for job in self.parse_jobs_from_html(
                    html=response.text,
                    source_name=self.config.name,
                    provider_name=self.config.provider,
                    default_company=self.config.company,
                    search_url=url,
                ):
                    jobs_by_id[job.external_id] = job
                next_page_url = self._extract_next_page_url(response.text, url)
                if next_page_url and next_page_url not in visited_urls:
                    pending_urls.append(next_page_url)

        return list(jobs_by_id.values())

    @classmethod
    def parse_jobs_from_html(
        cls,
        html: str,
        source_name: str,
        provider_name: str,
        default_company: str | None,
        search_url: str,
    ) -> list[JobPosting]:
        ds1_payload: dict | None = None

        for match in CALLBACK_RE.finditer(html):
            chunk = chompjs.parse_js_object(match.group(1))
            if chunk.get("key") == "ds:1":
                ds1_payload = chunk
                break

        if ds1_payload is None:
            raise ValueError("Could not find ds:1 payload in Google Careers HTML")

        data = ds1_payload.get("data", [])
        if not data or not isinstance(data[0], list):
            return []

        jobs: list[JobPosting] = []
        for raw_job in data[0]:
            if not isinstance(raw_job, list) or len(raw_job) < 15:
                continue

            locations = cls._extract_locations(raw_job[9])
            responsibilities_html = cls._extract_html_blob(raw_job[3])
            qualifications_html = cls._extract_html_blob(raw_job[4])
            description_html = cls._extract_html_blob(raw_job[10])
            experience_level = cls._extract_experience_level(
                raw_job[20] if len(raw_job) > 20 else None
            )

            jobs.append(
                JobPosting(
                    source_name=source_name,
                    source_provider=provider_name,
                    external_id=str(raw_job[0]),
                    title=str(raw_job[1]),
                    url=cls._build_public_job_url(
                        external_id=str(raw_job[0]),
                        title=str(raw_job[1]),
                        search_url=search_url,
                    ),
                    company=str(raw_job[7] or default_company or source_name),
                    locale=str(raw_job[8] or ""),
                    experience_level=experience_level,
                    locations=locations,
                    description_html=description_html,
                    responsibilities_html=responsibilities_html,
                    qualifications_html=qualifications_html,
                    source_updated_at=cls._extract_latest_timestamp(raw_job[12:15]),
                )
            )

        return jobs

    @staticmethod
    def _extract_html_blob(value: object) -> str:
        if isinstance(value, list) and len(value) > 1 and isinstance(value[1], str):
            return value[1]
        if isinstance(value, str) and value != "null":
            return value
        return ""

    @staticmethod
    def _extract_locations(value: object) -> list[str]:
        if not isinstance(value, list):
            return []

        locations: list[str] = []
        for item in value:
            if isinstance(item, list) and item and item[0]:
                locations.append(str(item[0]))
        return dedupe_preserve_order(locations)

    @staticmethod
    def _extract_latest_timestamp(values: list[object]) -> str | None:
        timestamps: list[int] = []
        for value in values:
            if isinstance(value, list) and value and isinstance(value[0], int):
                timestamps.append(value[0])
        if not timestamps:
            return None

        latest = max(timestamps)
        return datetime.fromtimestamp(latest, UTC).replace(microsecond=0).isoformat()

    @classmethod
    def _extract_experience_level(cls, value: object) -> str | None:
        if not isinstance(value, int):
            return None
        return EXPERIENCE_LEVEL_MAP.get(value)

    @staticmethod
    def _extract_next_page_url(html: str, current_url: str) -> str | None:
        match = NEXT_PAGE_RE.search(html)
        if not match:
            return None
        return urljoin(current_url, unescape(match.group(1)))

    @staticmethod
    def _slugify_title(title: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")
        return slug or "job"

    @classmethod
    def _build_public_job_url(
        cls,
        external_id: str,
        title: str,
        search_url: str,
    ) -> str:
        base_url = (
            "https://www.google.com/about/careers/applications/jobs/results/"
            f"{external_id}-{cls._slugify_title(title)}"
        )
        parsed = urlsplit(search_url)
        query_pairs = parse_qsl(parsed.query, keep_blank_values=False)
        if not query_pairs:
            return base_url
        return f"{base_url}?{urlencode(query_pairs)}"
