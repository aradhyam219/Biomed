"""Offline checks for 11U accounting and metadata, without provider calls."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

spec=importlib.util.spec_from_file_location("trial",Path(__file__).with_name("run_trial.py"))
trial=importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)


class TrialChecks(unittest.TestCase):
    def test_reference_11t_cost_decomposition(self):
        phase={"generations":[{"response_id":"offline", "usage":dict(input_tokens=5223,output_tokens=56702,
            input_tokens_details=dict(cached_tokens=0,cache_write_tokens=5220))}]}
        row=trial.costs(phase,trial.CANDIDATES[0])[0]
        self.assertEqual(row["regular_input_tokens"],3)
        self.assertAlmostEqual(row["estimated_request_cost_usd"],0.138696)

    def test_missing_usage_not_zero_cost(self):
        row=trial.costs({"generations":[{"usage":None}]},trial.CANDIDATES[0])[0]
        self.assertIsNone(row["estimated_request_cost_usd"])

    def test_invalid_decomposition_not_invented(self):
        phase={"generations":[{"usage":dict(input_tokens=4,output_tokens=10,
            input_tokens_details=dict(cached_tokens=3,cache_write_tokens=3))}]}
        self.assertIsNone(trial.costs(phase,trial.CANDIDATES[0])[0]["estimated_request_cost_usd"])

    def test_priority_is_valid_fast_and_timing_is_estimate(self):
        trial.OBSERVATIONS["offline"]=[dict(timestamp="2026-10-04T00:00:00+00:00",status="queued",returned_service_tier="priority"),
            dict(timestamp="2026-10-04T00:00:03+00:00",status="in_progress",returned_service_tier="priority"),
            dict(timestamp="2026-10-04T00:00:06+00:00",status="completed",returned_service_tier="priority")]
        outcome=trial.enrich({"generations":[dict(response_id="offline",status="success",usage=None)]},trial.CANDIDATES[0])
        self.assertTrue(outcome["service_tier_verified"])
        self.assertFalse(outcome["service_tier_mismatch"])
        self.assertEqual(outcome["generations"][0]["approximate_queue_duration_seconds"],3)

    def test_default_is_fast_tier_mismatch(self):
        trial.OBSERVATIONS["default_offline"]=[dict(timestamp="2026-10-04T00:00:00+00:00",status="completed",returned_service_tier="default")]
        outcome=trial.enrich({"generations":[dict(response_id="default_offline",status="success",usage=None)]},trial.CANDIDATES[0])
        self.assertTrue(outcome["service_tier_mismatch"])
        self.assertFalse(outcome["service_tier_verified"])


if __name__=="__main__":
    unittest.main()
