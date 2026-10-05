"""Independently replay audit graphs through the production pipeline, offline.

Verify exact frozen inputs, raw fresh output, relation grounding, full ledger
coverage, orphan identities and summary arithmetic. No provider calls occur.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location('audit13c',Path(__file__).with_name('audit.py'))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
from biomedical_extractor.llm_pipeline import LLMExtractionPipeline
from biomedical_extractor.llm_relation_extraction import _parse_structured_response
from biomedical_extractor.relation_extraction import RelationExtractionResult


class FrozenEntities:
    def __init__(self,p): self.p = p
    def extract_entities(self,text):
        assert text == self.p['source_text']
        return tuple(a.Entity(**e) for e in self.p['entities'])


class FrozenRelations:
    def __init__(self,p,values): self.p,self.values = p,values
    def extract_relations(self,text,entities):
        assert text == self.p['source_text']
        assert [e.to_dict() for e in entities] == self.p['entities']
        return a.validate_relations(text,entities,tuple(a.Relation(**r) for r in self.values))


def orphan(g):
    connected = {e[k] for e in g['edges'] for k in ('source','target')}
    return {n['id'] for n in g['nodes']} - connected


def main():
    manifest = a.verify()
    summary = a.read(a.OUT/'summary.json')
    fresh,reused,graphs = 0,0,0
    response_ids = set()
    for row in manifest['papers']:
        slug = row['slug']
        p = a.read(a.OUT/'inputs'/f'{slug}.json')
        result = a.read(a.OUT/'candidate'/slug/'result.json')
        assert result['status'] == 'success'
        assert result['configuration'] == manifest['configuration']
        diagnostics = result['generation_diagnostics']
        assert len(diagnostics) == 1 and not diagnostics[0]['repair']
        for key,value in [('observed_model','gpt-6.1-sol'),('observed_reasoning_effort','medium'),('observed_service_tier','default'),('observed_background',True)]:
            assert diagnostics[0][key] == value
        assert diagnostics[0]['status'] == 'success'
        assert diagnostics[0]['response_id'] not in response_ids
        response_ids.add(diagnostics[0]['response_id'])
        if row['reuse']:
            reused += 1
            assert a.sha((a.OUT/'candidate'/slug/'result.json').read_bytes()) == row['reused_output_sha256']
        else:
            fresh += 1
            raw = list((a.OUT/'candidate'/slug).glob('raw_*.txt'))
            assert len(raw) == 1
            parsed = _parse_structured_response(json.loads(raw[0].read_text(encoding='utf-8')))
            valid = a.validate_relations(p['source_text'],tuple(a.Entity(**e) for e in p['entities']),parsed)
            assert json.loads(json.dumps([r.to_dict() for r in valid.relations])) == result['relations']
        values = {'baseline_09b':p['baseline_09b'],'candidate':result['relations']}
        if 'baseline_contract10' in p: values['baseline_contract10'] = p['baseline_contract10']
        projections = {}
        for name,rs in values.items():
            pipeline = LLMExtractionPipeline(FrozenEntities(p),FrozenRelations(p,rs))
            replay = pipeline.extract_graph(p['source_text'],document_id=p['paper_id'])
            expected = a.read(a.OUT/'projections'/slug/f'{name}.json')
            assert json.loads(replay.to_json()) == expected
            assert all('paper_role' not in n for n in expected['nodes'])
            projections[name] = expected
            graphs += 1
        comp = a.read(a.OUT/'comparisons'/f'{slug}.json')
        for baseline,view in comp['views'].items():
            bg,cg = projections[baseline],projections['candidate']
            assert bg['nodes'] == cg['nodes']
            bo,co = orphan(bg),orphan(cg)
            expected = {'INHERITED ORPHAN':bo&co,'NEW ORPHAN':co-bo,'RESOLVED ORPHAN':bo-co,'NEW NODE / IDENTITY DIFFERENCE':set()}
            labels = {n['id']:n['label'] for n in bg['nodes']}
            for category,ids in expected.items():
                assert {v['id'] for v in view['orphans'][category]} == ids
                assert all(labels[v['id']]==v['label'] for v in view['orphans'][category])
            assert len(co) - len(bo) == len(co-bo) - len(bo-co)
            covered = set()
            for f in view['findings']:
                covered.update(f['baseline_relation_indices'])
                assert all(0 <= i < len(result['relations']) for i in f['candidate_relation_indices'])
                assert all(q in p['source_text'] for q in f['source_evidence'])
                if f['classification']=='HARMFUL OMISSION':
                    assert f['lost_meaning_source_excerpt'] in p['source_text']
            assert covered == set(range(len(p[baseline])))
            for n in view['orphans']['NEW ORPHAN']:
                assert n['previous_relations'] and n['cause'] in {'relation omitted','relation represented through another alias/node','identity split','endpoint changed','beneficial cleanup','uncertain'}
        sr = next(v for v in summary['rows'] if v['slug']==slug)
        assert all(sr[k]==v for k,v in comp['views']['baseline_09b']['controlled_counts'].items())
        assert sr['severity'] == comp['severity']
    assert fresh == reused == 4
    for key in summary['rows'][0]:
        if isinstance(summary['rows'][0][key],int):
            assert summary['aggregate'][key] == sum(r[key] for r in summary['rows'])
    assert sum(summary['severity_counts'].values()) == 8
    evidence_counts = {'fresh_inference_cases':fresh,'reused_cases':reused,'successful_generation_count':8,'repair_generations':0,'offline_pipeline_graph_replays':graphs,'complete_baseline_relation_coverage':True,'identical_nodes_per_controlled_pair':True,'orphan_turnover_verified':True,'source_and_raw_output_grounding_verified':True,'summary_arithmetic_verified':True,'protected_tracked_files_unchanged':True,'paper_role_provider_calls':0,'production_code_changes':0}
    a.write(a.OUT/'verification.json',evidence_counts)
    files = {p.relative_to(a.OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(a.OUT.rglob('*')) if p.is_file() and p.name!='artifact_hashes.json' and '__pycache__' not in p.parts}
    a.write(a.OUT/'artifact_hashes.json',files)
    print(evidence_counts)


if __name__=='__main__': main()
