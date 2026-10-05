"""Experimental auditor boundary checks without paid provider calls."""
import copy
import importlib.util
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("auditor13a", ROOT / "reports/relation_auditor_13a/scripts/auditor.py")
a = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = a
spec.loader.exec_module(a)


class AuditorTests(unittest.TestCase):
    def setUp(self):
        self.case = dict(source_text="A increases B in cells.", entities=[
            dict(id="E1", text="A", type="Gene", start=0, end=1),
            dict(id="E2", text="B", type="Gene", start=12, end=13)],
            pass1_relations=[dict(relation_ref="P1R001", source="E1", target="E2")])
        self.patch = dict(relation_ref="P1R001", intervention=[], effects=[],
                          context=[dict(value="cells", supporting_evidence="A increases B in cells.")])
        self.payload = dict(missing_relations=[], enrichment_patches=[self.patch])

    def test_valid_patch_preserves_pass1(self):
        before = copy.deepcopy(self.case)
        self.assertEqual(a.validate_audit(self.case, self.payload), self.payload)
        self.assertEqual(self.case, before)

    def test_bad_reference_and_duplicate_record(self):
        self.patch["relation_ref"] = "P1R002"
        with self.assertRaises(ValueError):
            a.validate_audit(self.case, self.payload)
        self.patch["relation_ref"] = "P1R001"
        self.payload["enrichment_patches"].append(copy.deepcopy(self.patch))
        with self.assertRaises(ValueError):
            a.validate_audit(self.case, self.payload)

    def test_nonverbatim_support_and_bad_type(self):
        self.patch["context"][0]["supporting_evidence"] = "other cells"
        with self.assertRaises(ValueError):
            a.validate_audit(self.case, self.payload)
        self.patch["context"][0] = dict(value=7, supporting_evidence="cells")
        with self.assertRaises(ValueError):
            a.validate_audit(self.case, self.payload)

    def test_topology_fields_forbidden(self):
        for field in ("source", "target", "predicate", "negated", "assertion", "evidence"):
            candidate = copy.deepcopy(self.payload)
            candidate["enrichment_patches"][0][field] = "changed"
            with self.assertRaises(ValueError):
                a.validate_audit(self.case, candidate)

    def test_duplicate_value_and_empty_patch(self):
        self.patch["context"].append(copy.deepcopy(self.patch["context"][0]))
        with self.assertRaises(ValueError):
            a.validate_audit(self.case, self.payload)
        self.patch["context"] = []
        with self.assertRaises(ValueError):
            a.validate_audit(self.case, self.payload)

    def test_missing_relation_validation(self):
        relation = dict(source="E1", target="E2", predicate="increases",
                        assertion="A increases B.", evidence="A increases B in cells.",
                        negated=False, intervention=None, effects=[], context=[], surface_form=None)
        self.payload["missing_relations"] = [relation]
        a.validate_audit(self.case, self.payload)
        relation["target"] = "E3"
        with self.assertRaises(ValueError):
            a.validate_audit(self.case, self.payload)

    def test_empty_result_and_strict_wire_schema(self):
        from biomedical_extractor.responses_execution import strict_transport_schema
        a.validate_audit(self.case, dict(missing_relations=[], enrichment_patches=[]))
        wire = strict_transport_schema(a.AuditPayload)
        self.assertFalse(wire["additionalProperties"])
        self.assertEqual(set(wire["required"]), {"missing_relations", "enrichment_patches"})

    def test_durable_attempt_prevents_paid_resubmission(self):
        with TemporaryDirectory() as directory:
            report = Path(directory)
            a.write(report / "audit_outputs/case/attempt.json", {"status": "started"})
            with patch.object(a, "REPORT", report), patch.object(a, "verify", return_value={"cases": [{"slug": "case"}]}), \
                 patch.object(a.OpenAIConfig, "from_environment", return_value=a.OpenAIConfig(api_key="test-placeholder")), \
                 patch("openai.OpenAI") as client, patch.object(a, "ResponsesBackgroundExecutor") as executor:
                with self.assertRaisesRegex(RuntimeError, "Refusing resubmission"):
                    a.run()
                client.return_value.responses.create.assert_not_called()
                executor.assert_not_called()

    def test_provider_failure_never_consumes_structural_repairs(self):
        with TemporaryDirectory() as directory:
            report = Path(directory)
            a.write(report / "inputs/case.json", self.case)
            request = report / "inputs/case.request.txt"
            request.write_text("frozen request", encoding="utf-8")
            row = {"slug": "case", "request_sha256": a.digest(request.read_bytes())}
            with patch.object(a, "REPORT", report), patch.object(a, "verify", return_value={"cases": [row]}), \
                 patch.object(a.OpenAIConfig, "from_environment", return_value=a.OpenAIConfig(api_key="test-placeholder")), \
                 patch("openai.OpenAI"), patch.object(a, "ResponsesBackgroundExecutor") as executor:
                executor.return_value.execute.side_effect = RuntimeError("provider failed")
                with self.assertRaisesRegex(RuntimeError, "provider failed"):
                    a.run()
                self.assertEqual(executor.return_value.execute.call_count, 1)
                record = a.read(report / "audit_outputs/case/attempt.json")
                self.assertEqual(record, {"case": "case", "status": "provider_failed", "repairs": 0})


if __name__ == "__main__":
    unittest.main()
