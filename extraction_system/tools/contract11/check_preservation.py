"""Offline audit of preserved source bytes, review freezes and semantic boundaries."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("runner",Path(__file__).with_name("run.py"))
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class PreservationChecks(unittest.TestCase):
    def test_preserved_bytes(self):
        manifest=json.loads((ROOT/"reports/contract11_preservation_11p/preserved_files.json").read_text())
        for name,expected in manifest["sha256"].items():
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),expected)

    def test_original_blind_freeze(self):
        review=ROOT/"reports/model_selection_11u/review"
        freeze=json.loads((review/"review_freeze.json").read_text())
        for name,key in (("blind_packet.json","blind_packet_sha256"),("model_key.json","model_key_sha256")):
            self.assertEqual(hashlib.sha256((review/name).read_bytes()).hexdigest(),freeze[key])

    def test_supplement_preserves_abc_and_d(self):
        read=lambda name:json.loads((ROOT/name).read_text())
        abc=read("reports/model_selection_11u/review/blind_packet.json")
        abcd=read("reports/model_selection_11u_with_candidate_d/review/blind_packet.json")
        d=read("reports/gpt61_sol_xhigh_supplemental/candidate_runs/gpt_61_sol_xhigh_standard/real.json")
        self.assertEqual(abcd["candidates"][:3],abc["candidates"])
        self.assertEqual(abcd["candidates"][3]["relations"],d["validated_relations"])

    def test_semantic_and_transport_boundary(self):
        p=runner.trial.p
        manifest,text,entities=p.frozen()
        self.assertEqual(len(entities),68)
        self.assertEqual(len(text),1981)
        wire=p.strict_transport_schema()
        self.assertEqual(p.sha(p.canonical(p.SCHEMA)),p.EXPECTED_SCHEMA)
        self.assertEqual(p.sha(p.canonical(wire)),runner.trial.TRANSPORT_SHA)
        self.assertTrue(all(p.verify_transport(wire).values()))
        self.assertEqual(p.DEFAULT_LLM_RELATION_MODEL,"gpt-5.6-luna")


if __name__=="__main__":
    unittest.main()
