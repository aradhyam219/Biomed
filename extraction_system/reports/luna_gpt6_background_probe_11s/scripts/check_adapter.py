"""Offline lifecycle checks using fake SDK responses; makes no provider calls."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

spec = importlib.util.spec_from_file_location("probe", Path(__file__).with_name("run_background_probe.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def response(status, output=""):
    return SimpleNamespace(id="resp_fake", created_at=1, status=status, output_text=output,
                           usage=None, error=None, incomplete_details=None)


class Client:
    def __init__(self, statuses):
        self.responses = self
        self.statuses = iter(statuses)
        self.creates = self.polls = self.cancels = 0

    def create(self, **kwargs):
        self.creates += 1
        assert kwargs["background"] is True and kwargs["store"] is False
        assert kwargs["text"]["format"]["schema"] == probe.SCHEMA
        value = next(self.statuses)
        if isinstance(value, Exception):
            raise value
        return value

    def retrieve(self, response_id, **kwargs):
        assert response_id == "resp_fake"
        self.polls += 1
        value = next(self.statuses)
        if isinstance(value, Exception):
            raise value
        return value

    def cancel(self, response_id, **kwargs):
        assert response_id == "resp_fake"
        self.cancels += 1
        return response("cancelled")


class LifecycleChecks(unittest.TestCase):
    def setUp(self):
        self.clock = 0
        self.saved = []
        for target, value in [("baseline", lambda: {}), ("write", lambda *args: None),
                              ("time.monotonic", lambda: self.clock), ("time.sleep", self.sleep)]:
            patcher = patch.object(probe, target, value) if "." not in target else patch("probe."+target, value)
            # Importlib modules need registration only for mock's dotted lookup.
            import sys
            sys.modules["probe"] = probe
            patcher.start()
            self.addCleanup(patcher.stop)
        probe.HISTORY.clear()

    def sleep(self, seconds):
        self.clock += seconds

    def generation(self, client, deadline=30):
        record = {}
        output = probe.generation(client, "prompt", deadline, record,
                                  lambda: self.saved.append(dict(record)))
        return record, output

    def test_id_persisted_before_poll_and_success(self):
        client = Client([response("queued"), response("completed", '{"relations":[]}')])
        record, output = self.generation(client)
        self.assertEqual(self.saved[1]["response_id"], "resp_fake")
        self.assertEqual(self.saved[1]["poll_count"], 0)
        self.assertTrue(record["transport_success"])
        self.assertEqual(output, '{"relations":[]}')
        self.assertEqual(client.creates, 1)

    def test_create_failure_has_no_retry(self):
        client = Client([RuntimeError("lost acknowledgement")])
        record, output = self.generation(client)
        self.assertEqual(record["status"], "background_create_failure")
        self.assertIsNone(output)
        self.assertEqual((client.creates, client.polls), (1, 0))

    def test_five_transport_failures_stop_same_id(self):
        import httpx2
        errors = [probe.APIConnectionError(request=httpx2.Request("GET", "https://api.openai.com")) for _ in range(5)]
        client = Client([response("queued"), *errors])
        record, _ = self.generation(client)
        self.assertEqual(record["status"], "background_polling_failure")
        self.assertEqual((client.creates, client.polls), (1, 5))

    def test_deadline_cancels_same_id(self):
        client = Client([response("queued")])
        record, _ = self.generation(client, deadline=3)
        self.assertEqual(record["status"], "background_timeout_cancelled")
        self.assertEqual(client.cancels, 1)

    def test_provider_failure_never_repairs(self):
        client = Client([response("failed")])
        outcome = probe.phase(client, "offline.json", probe.SYNTHETIC, probe.SYNTHETIC_ENTITIES, 30)
        self.assertEqual(outcome["status"], "provider_failed")
        self.assertEqual(client.creates, 1)

    def test_generated_invalid_output_uses_bounded_repairs(self):
        client = Client([response("completed", '{"bad":[]}') for _ in range(3)])
        outcome = probe.phase(client, "offline.json", probe.SYNTHETIC, probe.SYNTHETIC_ENTITIES, 30)
        self.assertEqual(outcome["status"], "structured_parse_failure")
        self.assertEqual(outcome["repair_count"], 2)
        self.assertEqual(client.creates, 3)


if __name__ == "__main__":
    unittest.main()
