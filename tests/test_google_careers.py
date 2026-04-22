from __future__ import annotations

import unittest

from jobbot.sources.google_careers import GoogleCareersSource


HTML_FIXTURE = """
<html>
  <body>
    <script>
      AF_initDataCallback({key: 'ds:1', hash: '2', data:[[[
        "12345678901234567",
        "Software Engineer, Early Career",
        "https://example.com/jobs/12345678901234567",
        [null,"<ul><li>Build backend features.</li></ul>"],
        [null,"<h3>Minimum qualifications:</h3><ul><li>2 years of experience with software development.</li></ul>"],
        "projects/example/org",
        null,
        "Google",
        "en-US",
        [["Taipei, Taiwan",["Taipei, Taiwan"],"Taipei",null,null,"TW"]],
        [null,"<p>Early career backend role.</p>"],
        [2],
        [1774881135,0],
        [1774881135,0],
        [1774881135,0],
        [null,""],
        "null",
        null,
        [null,""],
        [null,"<ul><li>2 years of experience with software development.</li></ul>"],
        1
      ]], null, 1877, 20], sideChannel: {}});
    </script>
  </body>
</html>
"""


class GoogleCareersSourceTest(unittest.TestCase):
    def test_parse_jobs_from_html(self) -> None:
        jobs = GoogleCareersSource.parse_jobs_from_html(
            html=HTML_FIXTURE,
            source_name="google",
            provider_name="google_careers",
            default_company="Google",
            search_url="https://example.com/search",
        )

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.external_id, "12345678901234567")
        self.assertEqual(job.company, "Google")
        self.assertEqual(job.locations, ["Taipei, Taiwan"])
        self.assertEqual(job.experience_level, "early")

    def test_extract_next_page_url(self) -> None:
        html = """
        <a href="https://www.google.com/about/careers/applications/jobs/results/?q=test&amp;page=2"
           aria-label="Go to next page"></a>
        """
        self.assertEqual(
            GoogleCareersSource._extract_next_page_url(
                html,
                "https://www.google.com/about/careers/applications/jobs/results/?q=test",
            ),
            "https://www.google.com/about/careers/applications/jobs/results/?q=test&page=2",
        )


if __name__ == "__main__":
    unittest.main()
