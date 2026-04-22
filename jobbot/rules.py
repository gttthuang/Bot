from __future__ import annotations

from .models import JobPosting, SubscriptionConfig
from .utils import contains_any


def matches_subscription(job: JobPosting, subscription: SubscriptionConfig) -> bool:
    if not subscription.enabled:
        return False

    if subscription.source_names and job.source_name not in subscription.source_names:
        return False

    if subscription.experience_include:
        if job.experience_level is None:
            return False
        if not contains_any(job.experience_level, subscription.experience_include):
            return False
    if subscription.experience_exclude and job.experience_level is not None:
        if contains_any(job.experience_level, subscription.experience_exclude):
            return False

    if subscription.company_include and not contains_any(job.company, subscription.company_include):
        return False
    if subscription.company_exclude and contains_any(job.company, subscription.company_exclude):
        return False

    if subscription.title_include and not contains_any(job.title, subscription.title_include):
        return False
    if subscription.title_exclude and contains_any(job.title, subscription.title_exclude):
        return False

    location_blob = " ".join(job.locations)
    if subscription.location_include and not contains_any(
        location_blob, subscription.location_include
    ):
        return False
    if subscription.location_exclude and contains_any(
        location_blob, subscription.location_exclude
    ):
        return False

    if subscription.text_include and not contains_any(job.searchable_text, subscription.text_include):
        return False
    if subscription.text_exclude and contains_any(job.searchable_text, subscription.text_exclude):
        return False

    return True
