import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from automation import story_pilot as pilot


NOW = datetime(2026, 10, 17, 15, 0, tzinfo=timezone.utc)


def story(**changes):
    result = {"username": "haytap", "story_pk": "1234567890", "is_private": False,
              "media_type": "image", "media_url": "https://scontent.cdninstagram.com/photo.jpg",
              "taken_at": (NOW - timedelta(hours=1)).isoformat(),
              "expiring_at": (NOW + timedelta(hours=23)).isoformat(), "caption": "Hayvan refahı"}
    result.update(changes)
    return result


class StoryPilotTests(unittest.TestCase):
    def test_paid_and_unknown_accounts_do_not_start(self):
        for data in ({}, {"isPaying": True}, {"isPaying": 0}, {"isPaying": "false"}):
            with self.subTest(data=data), self.assertRaises(pilot.PilotError):
                pilot.require_free_account({"data": data})
        pilot.require_free_account({"data": {"isPaying": False}})

    def test_quota_reservations_include_failed_attempts_and_local_date(self):
        state = pilot.reserve_scan({}, NOW)
        state = pilot.reserve_scan(state, NOW)
        with self.assertRaises(pilot.PilotError):
            pilot.reserve_scan(state, NOW)
        state = pilot.reserve_scan(state, NOW.replace(hour=22))  # next day in Istanbul
        self.assertEqual(state["daily"]["date"], "2026-10-18")
        self.assertEqual(state["daily"]["runs"], 1)
        state["monthly"]["runs"] = 60
        with self.assertRaises(pilot.PilotError):
            pilot.reserve_scan(state, NOW + timedelta(days=1))

    def test_untrusted_expired_and_private_rows_are_rejected(self):
        bad = [story(username="unknown"), story(is_private=True), story(is_private=None),
               story(expiring_at=NOW.isoformat()), story(taken_at=NOW.strftime("%Y-%m-%d")),
               story(media_url="http://127.0.0.1/secret"),
               story(media_url="https://cdninstagram.com.evil.example/p.jpg"),
               story(media_url="https://key@cdninstagram.com/p.jpg"), story(story_pk="../123")]
        self.assertEqual(pilot.normalize_stories(bad, ["haytap"], {}, NOW), [])
        rows = pilot.normalize_stories([story(), story()], ["haytap"], {}, NOW)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["approval"], "not_requested")
        self.assertEqual(pilot.normalize_stories([story()], ["haytap"], {"1234567890": "seen"}, NOW), [])

    def test_provider_denial_is_not_treated_as_zero_stories(self):
        apify = Mock()
        run = {"status": "SUCCEEDED", "defaultDatasetId": "dataset1", "defaultKeyValueStoreId": "store1"}
        for output in (None, {"outcome": "denied"}, {"outcome": "ok", "failed_targets": ["haytap"]}):
            apify.record.return_value = output
            with self.subTest(output=output), self.assertRaises(pilot.PilotError):
                pilot.inspect_output(apify, run)
        apify.call.assert_not_called()
        apify.record.return_value = {"outcome": "ok", "failed_targets": []}
        apify.call.return_value = []
        self.assertEqual(pilot.inspect_output(apify, run), [])

    def test_actor_request_is_bounded_and_ambiguous_start_is_not_retried(self):
        apify = Mock()
        apify.call.side_effect = pilot.PilotError("start response lost")
        with self.assertRaises(pilot.PilotError):
            pilot.scan(apify, ["haytap"])
        apify.call.assert_called_once()
        path, payload, method = apify.call.call_args.args
        self.assertIn("maxTotalChargeUsd=0.06", path)
        self.assertIn("restartOnError=false", path)
        self.assertEqual(payload, {"usernames": ["haytap"], "maxResults": 10})
        self.assertEqual(method, "POST")

    def test_successful_scan_restricts_both_output_resources(self):
        apify = Mock()
        apify.call.side_effect = [
            {"data": {"id": "run1", "status": "SUCCEEDED", "defaultDatasetId": "dataset1",
                      "defaultKeyValueStoreId": "store1"}}, [story()]]
        apify.record.return_value = {"outcome": "ok", "failed_targets": []}
        rows, run = pilot.scan(apify, ["haytap"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(run["status"], "SUCCEEDED")
        self.assertEqual(apify.restrict.call_count, 2)
        apify.restrict.assert_any_call("datasets", "dataset1")
        apify.restrict.assert_any_call("key-value-stores", "store1")

    def test_storage_must_be_restricted(self):
        apify = pilot.Apify("example-test-value")
        apify.call = Mock(return_value={"data": {"generalAccess": "ANYONE_WITH_ID_CAN_READ"}})
        with self.assertRaises(pilot.PilotError):
            apify.restrict("key-value-stores", "abc123")

    def test_report_escapes_untrusted_content_and_has_no_approval_action(self):
        rows = pilot.normalize_stories([story()], ["haytap"], {}, NOW)
        rows[0]["analysis"] = {"decision": "candidate", "summary": '<script>alert("bad")</script>',
                               "reason": "Önizleme", "score": 80}
        report = pilot.render_report({"created_at": NOW.isoformat(), "stories": rows})
        self.assertNotIn("<script>", report)
        self.assertNotIn("<form", report)
        self.assertIn("&lt;script&gt;", report)
        self.assertIn("Yayın veya onay göndermez", report)


if __name__ == "__main__":
    unittest.main()
