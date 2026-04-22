from __future__ import annotations

import unittest

from jobbot.models import JobPosting, SubscriptionConfig
from jobbot.rules import matches_subscription


class RulesTest(unittest.TestCase):
    def test_subscription_match(self) -> None:
        job = JobPosting(
            source_name="google",
            source_provider="google_careers",
            external_id="1",
            title="Software Engineer, Backend",
            url="https://example.com/jobs/1",
            company="Google",
            locale="en-US",
            experience_level="early",
            locations=["Taipei, Taiwan"],
        )
        subscription = SubscriptionConfig(
            name="google_l3_early",
            source_names=["google"],
            experience_include=["early"],
            title_include=["software engineer"],
            location_include=["taipei"],
        )

        self.assertTrue(matches_subscription(job, subscription))

    def test_missing_experience_fails_when_filter_requires_it(self) -> None:
        job = JobPosting(
            source_name="google",
            source_provider="google_careers",
            external_id="2",
            title="Software Engineer",
            url="https://example.com/jobs/2",
            company="Google",
            locale="en-US",
            locations=["Singapore"],
        )
        subscription = SubscriptionConfig(
            name="exp_bound",
            source_names=["google"],
            experience_include=["early"],
        )

        self.assertFalse(matches_subscription(job, subscription))

    def test_experience_filter_uses_official_badge(self) -> None:
        job = JobPosting(
            source_name="google",
            source_provider="google_careers",
            external_id="3",
            title="Software Engineer",
            url="https://example.com/jobs/3",
            company="Google",
            locale="en-US",
            experience_level="early",
            locations=["Taipei, Taiwan"],
        )
        subscription = SubscriptionConfig(
            name="official_experience",
            source_names=["google"],
            experience_include=["early"],
        )

        self.assertTrue(matches_subscription(job, subscription))


if __name__ == "__main__":
    unittest.main()
