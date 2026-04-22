from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import JobPosting, Settings, SourceConfig


class JobSource(ABC):
    def __init__(self, config: SourceConfig, settings: Settings) -> None:
        self.config = config
        self.settings = settings

    @abstractmethod
    def fetch_jobs(self) -> list[JobPosting]:
        raise NotImplementedError
