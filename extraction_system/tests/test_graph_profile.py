"""Narrow CPU distribution/module verification; no inference or provider calls."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from biomedical_extractor.graph_contract import ExportContext, GraphValidationError, contract_resource, profile_identity
from biomedical_extractor.graph_profile import prepare_graph_export, verify_graph_profile, verify_ner_metadata
from biomedical_extractor.llm_pipeline import LLMExtractionPipeline
from biomedical_extractor.llm_relation_extraction import OpenAIConfig
from biomedical_extractor.ner_runners import RunnerOutput
from importlib.metadata import version

IDENTITY = 'ees-cfeec6ccd400b9f44abbef35551944aa074ee3d79d3e5ec18dd7d7551c76e0de'

class CPUProfileVerificationTests(unittest.TestCase):
    def setUp(self):
        self.profile = contract_resource('baseline-profile.json')
        self.observed = {key:self.profile['ner'][key] for key in ('model_identifier','model_revision','model_artifact_sha256')}
        self.observed['runtime'] = {**copy.deepcopy(self.profile['ner']['runtime']),
                                    'pytorch':'2.14.0+cpu', 'cuda_available':False, 'cuda_version':None}

    def test_proven_cpu_build_pair_is_accepted(self):
        verify_ner_metadata(self.observed,self.profile,pytorch_distribution='2.14.0')
        self.assertEqual(self.observed['runtime']['pytorch'],'2.14.0+cpu')
        self.assertEqual(self.profile['ner']['runtime']['pytorch'],'2.14.0')

    def test_cuda_and_arbitrary_local_builds_are_rejected(self):
        for build in ('2.14.0+cu128','2.14.0+cuda','2.14.0+custom','2.14.0+cpu.custom','2.14.1+cpu'):
            with self.subTest(build=build):
                self.observed['runtime']['pytorch']=build
                with self.assertRaises(GraphValidationError):
                    verify_ner_metadata(self.observed,self.profile,pytorch_distribution='2.14.0')

    def test_missing_or_different_distribution_is_rejected(self):
        for release in (None,'2.14.1','2.14.0+cpu','2.14.0+custom',''):
            with self.subTest(release=release), self.assertRaises(GraphValidationError):
                verify_ner_metadata(self.observed,self.profile,pytorch_distribution=release)

    def test_missing_or_contradictory_cpu_evidence_is_rejected(self):
        changes=[('device',None),('device','cuda'),('cuda_version','12.8'),
                 ('cuda_version',''),('cuda_available',True),('cuda_available',None),('cuda_available',0)]
        for key in ('device','cuda_version','cuda_available'):
            observed=copy.deepcopy(self.observed); del observed['runtime'][key]
            with self.subTest(missing=key), self.assertRaises(GraphValidationError):
                verify_ner_metadata(observed,self.profile,pytorch_distribution='2.14.0')
        for key,value in changes:
            observed=copy.deepcopy(self.observed); observed['runtime'][key]=value
            with self.subTest(field=key,value=value), self.assertRaises(GraphValidationError):
                verify_ner_metadata(observed,self.profile,pytorch_distribution='2.14.0')

    def test_exact_version_behavior_rejects_explicit_cuda_evidence(self):
        observed=copy.deepcopy(self.observed); observed['runtime']['pytorch']='2.14.0'
        verify_ner_metadata(observed,self.profile)
        for key,value in [('cuda_version','12.8'),('cuda_available',True),('device','cuda')]:
            changed=copy.deepcopy(observed); changed['runtime'][key]=value
            with self.subTest(field=key), self.assertRaises(GraphValidationError):
                verify_ner_metadata(changed,self.profile)

    def test_other_model_and_runtime_mismatches_still_fail(self):
        for key in ('model_identifier','model_revision','model_artifact_sha256'):
            observed=copy.deepcopy(self.observed); observed[key]='wrong'
            with self.subTest(field=key), self.assertRaises(GraphValidationError):
                verify_ner_metadata(observed,self.profile,pytorch_distribution='2.14.0')
        for key,value in [('stride',257),('flair','other'),('python','3.11.15'),('truncate',False)]:
            observed=copy.deepcopy(self.observed); observed['runtime'][key]=value
            with self.subTest(field=key), self.assertRaises(GraphValidationError):
                verify_ner_metadata(observed,self.profile,pytorch_distribution='2.14.0')
        changed=copy.deepcopy(self.profile); changed['relation']['prompt_sha256']='a'*64
        with self.assertRaises(GraphValidationError):
            verify_ner_metadata(self.observed,changed,pytorch_distribution='2.14.0')

    def test_original_descriptor_and_canonical_identity_remain_unchanged(self):
        before=copy.deepcopy(self.profile)
        verify_ner_metadata(self.observed,self.profile,pytorch_distribution='2.14.0')
        self.assertEqual(self.profile,before)
        self.assertEqual(profile_identity(self.profile),IDENTITY)
        self.assertEqual(self.profile,contract_resource('baseline-profile.json'))

    def test_live_bridge_reads_the_inference_interpreter_before_relations(self):
        pipeline=LLMExtractionPipeline.from_pretrained(llm_config=OpenAIConfig(api_key='offline-test'),
                                                      hunflair2_runtime_python='selected-isolated-python')
        ctx=ExportContext(version('biomedical-extractor'),'a'*40,self.profile)
        versions={key:self.profile['ner']['runtime'][key] for key in ('python','flair','pytorch','transformers','scispacy','spacy','en_core_sci_sm')}
        with patch('biomedical_extractor.graph_profile._hunflair2_artifact', return_value=(Path('artifact'),self.profile['ner']['model_revision'])), \
             patch('biomedical_extractor.graph_profile._sha256_file', return_value=self.profile['ner']['model_artifact_sha256']), \
             patch('biomedical_extractor.graph_profile.subprocess.check_output',return_value=json.dumps(versions)):
            prepare_graph_export(pipeline,text='BRCA1',document_id='d',context=ctx)
        runtime=pipeline.entity_extractor._runtime
        self.assertEqual(profile_identity(dict(runtime._v1_expected_profile)),IDENTITY)
        run=RunnerOutput('HunFlair2',Path('unused'),self.observed,{runtime._DOCUMENT_ID:[]})
        with patch('biomedical_extractor.ner_runners.run_hunflair2',return_value=run) as ner, \
             patch('biomedical_extractor.graph_profile.subprocess.check_output',return_value=json.dumps(versions)) as metadata, \
             patch.object(pipeline.relation_extractor,'extract_relations') as paid:
            runtime.predict_entities('BRCA1')
            self.assertEqual(str(ner.call_args.kwargs['python_path']),'selected-isolated-python')
            self.assertEqual(metadata.call_args.args[0][0],'selected-isolated-python')
            verify_graph_profile(pipeline,ctx,text='BRCA1')
            wrong={**versions,'pytorch':'2.14.1'}
            metadata.return_value=json.dumps(wrong)
            with self.assertRaises(GraphValidationError):
                runtime.predict_entities('BRCA1')
            paid.assert_not_called()
            metadata.return_value=json.dumps(versions)
            ctx.configuration['ner']=copy.deepcopy(ctx.configuration['ner'])
            ctx.configuration['ner']['runtime']['stride']=257
            with self.assertRaises(GraphValidationError):
                verify_graph_profile(pipeline,ctx,text='BRCA1')

if __name__ == '__main__':
    unittest.main()
