import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import main


class DigestCronTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_cron_secret_must_be_configured(self):
        with patch.dict(os.environ, {}, clear=True):
            response = self.client.post("/api/cron/digest?dry_run=true")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "CRON_SECRET is not configured")

    def test_cron_secret_must_match(self):
        with patch.dict(os.environ, {"CRON_SECRET": "expected"}, clear=True):
            response = self.client.post(
                "/api/cron/digest?dry_run=true",
                headers={"x-cron-secret": "wrong"},
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Forbidden")

    def test_dry_run_calls_digest_job_with_matching_secret(self):
        expected = {
            "checked": 0,
            "eligible": 0,
            "sent": 0,
            "skipped": 0,
            "failed": 0,
            "dry_run": True,
        }
        with patch.dict(os.environ, {"CRON_SECRET": "expected"}, clear=True):
            with patch.object(main, "_run_digest_job", return_value=expected) as run_job:
                response = self.client.post(
                    "/api/cron/digest?dry_run=true",
                    headers={"x-cron-secret": "expected"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        run_job.assert_called_once_with(dry_run=True, include_details=False, force=False)

    def test_include_details_is_forwarded_to_digest_job(self):
        expected = {
            "checked": 0,
            "eligible": 0,
            "sent": 0,
            "skipped": 0,
            "failed": 0,
            "dry_run": True,
            "details": [],
        }
        with patch.dict(os.environ, {"CRON_SECRET": "expected"}, clear=True):
            with patch.object(main, "_run_digest_job", return_value=expected) as run_job:
                response = self.client.post(
                    "/api/cron/digest?dry_run=true&include_details=true",
                    headers={"x-cron-secret": "expected"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)
        run_job.assert_called_once_with(dry_run=True, include_details=True, force=False)

    def test_parse_digest_hour_accepts_only_0_to_23(self):
        self.assertEqual(main._parse_digest_hour("0"), 0)
        self.assertEqual(main._parse_digest_hour(23), 23)
        self.assertIsNone(main._parse_digest_hour("24"))
        self.assertIsNone(main._parse_digest_hour("bad"))


if __name__ == "__main__":
    unittest.main()
