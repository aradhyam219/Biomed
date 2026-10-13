"""Offline behavioral gates for Graph Contract v1 and known legacy payloads."""
import copy
from dataclasses import replace
from importlib.metadata import version
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from biomedical_extractor import (ExportContext, GraphValidationError, GraphResult,
    GraphDocument, GraphNode, GraphEdge, GraphEvidence, Entity, PaperRole,
    input_fingerprints, export_graph, graph_json, validate_graph, cache_eligibility,
    contract_resource, profile_identity, release_context, LLMExtractionPipeline,
    OpenAIConfig, prepare_graph_export, verify_graph_profile)
from biomedical_extractor.graph_profile import check_graph_options, verify_ner_metadata

STAMP = '2026-10-13T00:00:00Z'
ROOT = Path(__file__).resolve().parent.parent


def context():
    return ExportContext(version('biomedical-extractor'), 'a'*40, contract_resource('baseline-profile.json'))


def graph():
    text = '\U0001f9ec\r\ne\u0301 BRCA1'
    nodes = (GraphNode('n1', 'BRCA1', 'Gene', (Entity('E1','BRCA1','Gene',6,11,None),)),
             GraphNode('n2', 'e\u0301', 'Species', (Entity('E2','e\u0301','Species',3,5,0.8),),
                       paper_role=PaperRole('contextual',('Paraphrased role.',),('e\u0301',))))
    edge = GraphEdge('r1','n1','n1','regulates',False,(GraphEvidence('BRCA1','A paraphrased assertion.',effects=('Effect paraphrase',)),))
    return text, GraphResult(GraphDocument(' PMC123 '), nodes, (edge,))


def payload():
    text, g = graph()
    return export_graph(g,text=text,context=context(),generated_at=STAMP)


class GraphContractTests(unittest.TestCase):
    def test_schema_metaschemas_and_normative_vectors(self):
        for name in ('graph-v1.schema.json','graph-legacy.schema.json'):
            Draft202012Validator.check_schema(contract_resource(name))
        for row in contract_resource('fingerprint-examples.json'):
            self.assertEqual(input_fingerprints(row['text'],row['paper_title']),{k:row[k] for k in ('source_sha256','extraction_input_sha256')})
            self.assertEqual(len(row['text'].encode()),row['text_utf8_length'])
            self.assertEqual(len(row['paper_title'].encode()),row['title_utf8_length'])

    def test_exact_input_identity(self):
        self.assertEqual(input_fingerprints('x'),input_fingerprints('x',''))
        self.assertEqual(input_fingerprints('x','a')['source_sha256'],input_fingerprints('x','b')['source_sha256'])
        variants = [('x','a'),('x','b'),(' x','a'),('x\r\n','a'),('x\n','a'),('e\u0301','a'),('\u00e9','a'),('ab','c'),('a','bc')]
        self.assertEqual(len({input_fingerprints(*v)['extraction_input_sha256'] for v in variants}),len(variants))
        for value in (None,1,'\ud800'):
            with self.subTest(value=repr(value)),self.assertRaises(GraphValidationError):input_fingerprints('x',value)
            with self.assertRaises(GraphValidationError):input_fingerprints(value)

    def test_export_determinism_payload_preservation_and_empty(self):
        text,g=graph();before=g.to_dict()
        first=export_graph(g,text=text,context=context(),generated_at=STAMP)
        self.assertEqual(first,export_graph(g,text=text,context=context(),generated_at=STAMP))
        self.assertEqual({k:first[k] for k in before},before)
        self.assertEqual(g.to_dict(),before)
        self.assertEqual(json.loads(graph_json(first))['provenance']['generated_at'],STAMP)
        self.assertTrue(validate_graph(first,text=text).source_checked)
        self.assertIn('unchecked',validate_graph(first).limitation)
        empty=GraphResult(GraphDocument('empty'),(),())
        self.assertEqual(export_graph(empty,text='',context=context())['nodes'],[])

    def test_metadata_fails_clearly(self):
        for release,revision in [('0.0.0','a'*40),(version('biomedical-extractor'),''),(version('biomedical-extractor'),'a'*39),(version('biomedical-extractor'),'A'*40)]:
            with self.assertRaises(GraphValidationError):ExportContext(release,revision,context().configuration)
        with patch('biomedical_extractor.graph_contract.metadata.version',side_effect=__import__('importlib.metadata',fromlist=['PackageNotFoundError']).PackageNotFoundError):
            with self.assertRaises(GraphValidationError):context()
        with patch('biomedical_extractor.graph_contract.subprocess.check_output',return_value=' M source.py'):
            with self.assertRaises(GraphValidationError):release_context()

    def test_structure_negative_cases(self):
        mutations=[lambda d:d.pop('document'),lambda d:d.pop('provenance'),
            lambda d:d.update(schema_version=None),lambda d:d.update(schema_version='2.0'),
            lambda d:d.update(schema_version=1),lambda d:d.update(extra=True),
            lambda d:d['document'].update(id=' \t'),lambda d:d['nodes'][0].update(extra='x'),
            lambda d:d['nodes'][0].update(paper_role=None),lambda d:d['nodes'][0].update(mentions=[]),
            lambda d:d['nodes'][0]['mentions'][0].pop('score'),
            lambda d:d['nodes'][0]['mentions'][0].update(start=True),
            lambda d:d['nodes'][0]['mentions'][0].update(start=6.0),
            lambda d:d['nodes'][0]['mentions'][0].update(end=6),
            lambda d:d['nodes'][0]['mentions'][0].update(start=-1),
            lambda d:d['nodes'][0]['mentions'][0].update(score=True),
            lambda d:d['nodes'][0]['mentions'][0].update(score=float('nan')),
            lambda d:d['edges'][0]['evidence'][0].update(score=float('inf')),
            lambda d:d['edges'][0]['evidence'][0].update(score=1.1),
            lambda d:d['edges'][0].update(negated=0),lambda d:d['edges'][0].update(evidence=[]),
            lambda d:d['edges'][0]['evidence'][0].pop('assertion'),
            lambda d:d['edges'][0]['evidence'][0].update(effects=None),
            lambda d:d['edges'][0]['evidence'][0].update(intervention=2),
            lambda d:d['edges'][0]['evidence'][0].update(surface_form='  '),
            lambda d:d['provenance'].update(source_sha256='a'*64+'\n'),
            lambda d:d['provenance'].update(extraction_input_sha256='A'*64),
            lambda d:d['provenance'].update(build_revision='a'*39),
            lambda d:d['provenance'].update(generated_at='2026-02-30T00:00:00Z'),
            lambda d:d['provenance'].update(generated_at='2026-10-13T00:00:00+00:00'),
            lambda d:d['provenance'].update(extraction_profile=' ')]
        for i,mutate in enumerate(mutations):
            d=payload();mutate(d);before=copy.deepcopy(d)
            with self.subTest(case=i),self.assertRaises(GraphValidationError):validate_graph(d)
            # NaN equality is undefined, so compare its stable diagnostic serialization.
            self.assertEqual(repr(d),repr(before))

    def test_integrity_and_role_negative_cases(self):
        mutations=[lambda d:d['nodes'].append(copy.deepcopy(d['nodes'][0])),
            lambda d:d['edges'].append(copy.deepcopy(d['edges'][0])),
            lambda d:d['edges'][0].update(id='n1'),lambda d:d['edges'][0].update(target='missing'),
            lambda d:d['nodes'][1]['mentions'][0].update(id='E1'),
            lambda d:d['nodes'][0].update(paper_role=copy.deepcopy(d['nodes'][1]['paper_role'])),
            lambda d:d['nodes'][1]['paper_role'].update(category='substantive'),
            lambda d:d['nodes'][1]['paper_role'].update(paragraphs=[]),
            lambda d:d['nodes'][1]['paper_role'].update(paragraphs=['a','b','c']),
            lambda d:d['nodes'][1]['paper_role'].update(evidence=[])]
        for i,mutate in enumerate(mutations):
            d=payload();mutate(d)
            with self.subTest(case=i),self.assertRaises(GraphValidationError):validate_graph(d)

    def test_source_context_offsets_and_quotes(self):
        text,g=graph();d=payload()
        validate_graph(d,text=text)
        for mutate in [lambda d:d['nodes'][0]['mentions'][0].update(start=7,end=12),
                       lambda d:d['nodes'][1]['mentions'][0].update(text='\u00e9'),
                       lambda d:d['edges'][0]['evidence'][0].update(text='not quoted'),
                       lambda d:d['nodes'][1]['paper_role'].update(evidence=['not quoted'])]:
            altered=copy.deepcopy(d);mutate(altered)
            validate_graph(altered)  # graph-only checks explicitly do not prove grounding
            with self.assertRaises(GraphValidationError):validate_graph(altered,text=text)
        with self.assertRaises(GraphValidationError):validate_graph(d,text=text+' ')
        with self.assertRaises(GraphValidationError):validate_graph(d,text=text,paper_title='changed')

    def test_legacy_shapes_no_mutation_or_fallback(self):
        cases=[json.loads(p.read_text(encoding='utf-8'))['expected_graph'] for p in (ROOT/'tests/fixtures/baseline').glob('*.json')]
        cases.append(json.loads((ROOT/'viewer/graph-fixture.json').read_text(encoding='utf-8')))
        for d in cases:
            before=copy.deepcopy(d)
            self.assertEqual(validate_graph(d).format,'legacy')
            self.assertEqual(d,before)
            self.assertFalse(cache_eligibility(d,document_id=d['document']['id'],text='').eligible)
            for v in (None,'','9.0',1):
                altered={**d,'schema_version':v}
                with self.assertRaises(GraphValidationError):validate_graph(altered)

    def test_cache_literal_identity_and_old_provenance(self):
        d=payload();text,_=graph()
        d['provenance'].update(extractor_version='old-release',build_revision='b'*40,extraction_profile='old-profile')
        self.assertTrue(cache_eligibility(d,document_id=' PMC123 ',text=text).eligible)
        for doc,t,h in [('PMC123',text,''),(' pmc123 ',text,''),('PMCID:PMC123',text,''),(' PMC123 ',text+' ',''),(' PMC123 ',text,'title'),(' PMC123 ',None,'')]:
            self.assertFalse(cache_eligibility(d,document_id=doc,text=t,paper_title=h).eligible)
        d['edges'][0]['target']='absent'
        self.assertIn('invalid',cache_eligibility(d,document_id=' PMC123 ',text=text).reason)

    def test_profile_immutable_binding_and_overrides(self):
        p=context().configuration
        self.assertEqual(profile_identity(p),profile_identity(copy.deepcopy(p)))
        for section,key,value in [('relation','model','other'),('relation','reasoning_effort','high'),('relation','service_tier','fast'),('relation','background',False),('relation','max_retries',0)]:
            altered=copy.deepcopy(p);altered[section]['configuration'][key]=value
            with self.assertRaises(GraphValidationError):profile_identity(altered)
        for mutate in [lambda d:d['roles'].update(model='other'),lambda d:d['roles'].update(prompt_sha256='a'*64),lambda d:d['ner'].update(model_revision='a'*40),lambda d:d['ner']['runtime'].update(stride=1),lambda d:d['relation'].update(semantic_schema={})]:
            altered=copy.deepcopy(p);mutate(altered)
            with self.assertRaises(GraphValidationError):profile_identity(altered)
        for kwargs in [dict(model='other'),dict(reasoning_effort='high'),dict(service_tier='fast'),dict(background=False),dict(max_retries=0),dict(max_completion_tokens=42)]:
            with self.assertRaises(GraphValidationError):check_graph_options(OpenAIConfig(**kwargs),model='hunflair/hunflair2-ner',device=None)
        check_graph_options(OpenAIConfig(api_key='rotation',api_key_env='ANOTHER'),model='hunflair/hunflair2-ner',device=None)
        with self.assertRaises(GraphValidationError):check_graph_options(OpenAIConfig(),model='hunflair/hunflair2-ner',device='cuda')
        with self.assertRaises(GraphValidationError):prepare_graph_export(LLMExtractionPipeline(object(),object()),text='x',document_id='d',context=context())

    def test_actual_runtime_and_provider_configuration(self):
        p=context().configuration
        observed={**{k:p['ner'][k] for k in ('model_identifier','model_revision','model_artifact_sha256')},'runtime':copy.deepcopy(p['ner']['runtime'])}
        verify_ner_metadata(observed,p)
        observed['runtime']['stride']=1
        with self.assertRaises(GraphValidationError):verify_ner_metadata(observed,p)
        pipeline=LLMExtractionPipeline.from_pretrained(llm_config=OpenAIConfig(api_key='offline-test'))
        from biomedical_extractor.graph_profile import _provider
        _provider(pipeline.relation_extractor,'relation',p)
        from biomedical_extractor.llm_paper_roles import LLMPaperRoleExtractor
        roles=LLMPaperRoleExtractor.from_openai(OpenAIConfig(api_key='offline-test',model='relation-override',reasoning_effort='high'))
        _provider(roles,'roles',p)  # role model/reasoning are independently fixed
        pipeline.relation_extractor._prompt+='changed'
        with self.assertRaises(GraphValidationError):_provider(pipeline.relation_extractor,'relation',p)

    def test_preflight_paths_credentials_and_actual_drift_before_paid_calls(self):
        from biomedical_extractor import HunFlair2IsolatedRuntime
        from biomedical_extractor.ner_runners import RunnerOutput
        p = context().configuration
        observed = {**{k: p['ner'][k] for k in ('model_identifier', 'model_revision', 'model_artifact_sha256')}, 'runtime': copy.deepcopy(p['ner']['runtime'])}
        versions = {k: p['ner']['runtime'][k] for k in ('python', 'flair', 'pytorch', 'transformers', 'scispacy', 'spacy', 'en_core_sci_sm')}
        for cache, key in [('cache-one', 'credential-one'), ('moved-cache', 'credential-two')]:
            pipeline = LLMExtractionPipeline.from_pretrained(llm_config=OpenAIConfig(api_key=key), hunflair2_runtime_python='isolated-python', hunflair2_runtime_cache=cache)
            with patch('biomedical_extractor.graph_profile._hunflair2_artifact', return_value=(Path('artifact'), p['ner']['model_revision'])), \
                 patch('biomedical_extractor.graph_profile._sha256_file', return_value=p['ner']['model_artifact_sha256']), \
                 patch('biomedical_extractor.graph_profile.subprocess.check_output', return_value=json.dumps(versions)):
                bound = prepare_graph_export(pipeline, text='BRCA1', document_id='d', context=context())
            self.assertEqual(profile_identity(bound.configuration), profile_identity(p))
            runtime = pipeline.entity_extractor._runtime
            altered = copy.deepcopy(observed)
            altered['runtime']['stride'] = 1
            run = RunnerOutput('HunFlair2', Path('unused'), altered, {runtime._DOCUMENT_ID: []})
            with patch('biomedical_extractor.ner_runners.run_hunflair2', return_value=run), \
                 patch.object(pipeline.relation_extractor, 'extract_relations') as paid:
                with self.assertRaises(GraphValidationError): pipeline.extract_graph('BRCA1', document_id='d')
                paid.assert_not_called()
            runtime._last_metadata = observed
            verify_graph_profile(pipeline, bound, text='BRCA1')

    def test_bound_providers_cannot_keep_profile_after_mutation(self):
        from biomedical_extractor.graph_profile import _provider
        from biomedical_extractor.llm_paper_roles import LLMPaperRoleExtractor
        p = context().configuration
        for section in ('relation', 'roles'):
            for field, value in [('_model', 'changed'), ('_reasoning_effort', 'high'), ('_service_tier', 'fast'), ('_max_output_tokens', 1), ('_schema', {})]:
                producer = (LLMExtractionPipeline.from_pretrained(llm_config=OpenAIConfig(api_key='offline-test')).relation_extractor if section == 'relation' else LLMPaperRoleExtractor.from_openai(OpenAIConfig(api_key='offline-test')))
                setattr(producer._background_executor, field, value)
                with self.subTest(section=section, field=field), self.assertRaises(GraphValidationError): _provider(producer, section, p)


if __name__=='__main__':unittest.main()
