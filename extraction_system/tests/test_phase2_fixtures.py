"""Frozen Phase 2 input/configuration invariants; no model/provider execution."""
import hashlib
import json
from pathlib import Path
import unittest
import copy
import contextlib
import io
import tempfile
from unittest.mock import patch

from tools import phase2_reference

from biomedical_extractor.graph_contract import contract_resource, input_fingerprints, profile_identity

ROOT = Path(__file__).resolve().parents[1]

class Phase2FixtureTests(unittest.TestCase):
    def test_frozen_sources_and_profile(self):
        manifest = json.loads((ROOT/'reports/phase2/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(len(manifest['cases']), 7)
        self.assertEqual(len({case['case_id'] for case in manifest['cases']}), 7)
        documents = {}
        for case in manifest['cases']:
            with self.subTest(case=case['case_id']):
                packet = json.loads((ROOT/case['fixture']).read_text(encoding='utf-8'))
                self.assertEqual(packet['case_id'], case['case_id'])
                self.assertEqual(packet['document_id'], case['document_id'])
                self.assertEqual(packet['paper_title'], case['paper_title'])
                self.assertEqual(hashlib.sha256(packet['paper_title'].encode('utf-8')).hexdigest(), case['title_sha256'])
                hashes = input_fingerprints(packet['text'], packet['paper_title'])
                self.assertEqual(hashes, {key:case[key] for key in hashes})
                documents[case['case_id']] = packet['document_id']
        self.assertEqual(documents['sfpq-passage'], documents['sfpq-full'])
        self.assertEqual(documents['cbl-passage'], documents['cbl-full'])
        self.assertEqual(manifest['paid_subset'], ['sfpq-full', 'cbl-full'])
        self.assertEqual(manifest['end_to_end_case'], 'sfpq-full')
        self.assertEqual(manifest['cpu_profile'], contract_resource('baseline-profile.json'))
        self.assertEqual(manifest['cpu_profile_identity'], profile_identity(manifest['cpu_profile']))

    def test_scientific_checklist_quotes_resolve_to_source(self):
        checklist = json.loads((ROOT/'reports/phase2/scientific-checklist.json').read_text(encoding='utf-8'))
        self.assertEqual([case['case_id'] for case in checklist['cases']], ['sfpq-full','cbl-full'])
        for case in checklist['cases']:
            packet=json.loads((ROOT/f"tests/fixtures/compatibility/{case['case_id']}.json").read_text(encoding='utf-8'))
            self.assertEqual(packet['document_id'],case['document_id'])
            for quote in case['passages']:
                self.assertGreater(quote['end'],quote['start'])
                self.assertEqual(packet['text'][quote['start']:quote['end']],quote['evidence'])
                self.assertTrue(quote['inspect'])

    def test_actual_build_mismatch_is_retained_but_not_accepted(self):
        manifest=json.loads((ROOT/'reports/phase2/manifest.json').read_text(encoding='utf-8'))
        profile=manifest['cpu_profile']
        metadata={key:profile['ner'][key] for key in ('model_identifier','model_revision','model_artifact_sha256')}
        metadata['runtime']=copy.deepcopy(profile['ner']['runtime'])
        metadata['runtime']['pytorch']='2.14.0+cpu'
        documents=[]
        for case in manifest['cases']:
            packet=json.loads((ROOT/case['fixture']).read_text(encoding='utf-8'))
            documents.append({'id':case['case_id'],'text_sha256':case['source_sha256'],
                              'predictions':[{'text':packet['text'][:1],'start':0,'end':1,'label':'Gene','score':0.875}]})
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache/phase2') as temporary:
            output=Path(temporary)
            evidence=output/'summary'
            phase2_reference.write(evidence/'manifest.json',manifest)
            phase2_reference.write(output/'run.json',{'run_id':'diagnostic-test','platform':'test','machine':'test','tool_sha256':'a'*64})
            phase2_reference.write(output/'raw.json',{'metadata':metadata,'documents':documents})
            with patch.object(phase2_reference,'EVIDENCE',evidence), contextlib.redirect_stdout(io.StringIO()):
                phase2_reference.inspect_cpu(output)
                summary=phase2_reference.read(evidence/'cpu-reference.json')
                self.assertEqual(summary['disposition'],'BLOCKED')
                self.assertFalse(summary['accepted_cpu_comparator'])
                self.assertEqual(summary['runtime_descriptor_differences']['pytorch'],{'expected':'2.14.0','observed':'2.14.0+cpu'})
                entities=phase2_reference.read(output/'sfpq-full-entities.json')['entities']
                self.assertEqual(entities[0]['score'],0.875)
                # Invalid source spans must fail even for diagnostic observations.
                documents[0]['predictions'][0]['text']='not the source slice'
                phase2_reference.write(output/'raw.json',{'metadata':metadata,'documents':documents})
                (evidence/'cpu-reference.json').unlink()
                with self.assertRaises(ValueError):
                    phase2_reference.inspect_cpu(output)

    def test_python_source_attestation_handles_bom_and_line_endings_only(self):
        source='print("Greek: \u03b2")\n# second line\n'
        expected=hashlib.sha256(source.encode('utf-8')).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'capture.py'
            for data in (source.encode('utf-8'), b'\xef\xbb\xbf'+source.replace('\n','\r\n').encode('utf-8'), source.replace('\n','\r').encode('utf-8')):
                path.write_bytes(data)
                self.assertEqual(phase2_reference.python_source_sha256(path),expected)
                byte_digest=hashlib.sha256(data).hexdigest()
                phase2_reference.verify_capture_tool(path,source_sha256=expected,byte_sha256=byte_digest)
                with self.assertRaises(ValueError):
                    phase2_reference.verify_capture_tool(path,source_sha256='0'*64,byte_sha256=byte_digest)
                with self.assertRaises(ValueError):
                    phase2_reference.verify_capture_tool(path,source_sha256=expected,byte_sha256='0'*64)
            path.write_bytes(source.replace('second','changed').encode('utf-8'))
            self.assertNotEqual(phase2_reference.python_source_sha256(path),expected)
        self.assertNotEqual(input_fingerprints('text\r\n','title'),input_fingerprints('text\n','title'))

if __name__ == '__main__':
    unittest.main()
