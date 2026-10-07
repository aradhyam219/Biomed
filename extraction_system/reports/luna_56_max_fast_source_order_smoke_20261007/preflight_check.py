"""Deterministic Contract 14R gating; this file never invokes a provider."""
import importlib.util
import json
from pathlib import Path
from dataclasses import asdict

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / '.cache/contract14r'
spec = importlib.util.spec_from_file_location('smoke', CACHE/'smoke.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
PRIOR = ROOT/'reports/luna_56_max_fast_smoke_20261007_r2'
AUDIT = ROOT/'reports/contract14_luna_historical_parity'
def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def verify():
    packet=read(m.PACKET)
    prior=read(PRIOR/'inputs.json')
    historical=read(AUDIT/'historical_mentions_reconstructed.json')
    frozen=m.FrozenEntities(packet)
    assembly=m.assemble_document_entities(frozen.entities,frozen.source)
    old_assembly=m.assemble_document_entities(tuple(m.Entity(**e) for e in prior['entities']),frozen.source)
    assert len(frozen.entities)==41 and len(assembly.document_entities)==20
    assert packet['entities']==historical
    assert sorted(prior['entities'],key=lambda e:(e['start'],e['end'],e['type']))==historical
    assert assembly.to_dict()==old_assembly.to_dict()
    assert frozen.source==prior['source']['source_text']
    assert all(frozen.source[e.start:e.end]==e.text for e in frozen.entities)
    assert {e['id']:e for e in packet['entities']}=={e['id']:e for e in prior['entities']}
    old_preflight=read(PRIOR/'preflight.json')
    config={k:v for k,v in asdict(m.relation.OpenAIConfig()).items() if k not in {'api_key','api_key_env','base_url'}}
    assert config==old_preflight['candidate']
    new_prompt=m.relation._build_prompt(frozen.source,frozen.entities,m.relation.RELATION_EXTRACTION_SYSTEM_PROMPT)
    grouped_prompt=m.relation._build_prompt(frozen.source,tuple(m.Entity(**e) for e in prior['entities']),m.relation.RELATION_EXTRACTION_SYSTEM_PROMPT)
    assert grouped_prompt==(ROOT/'.cache/luna_56_max_fast_smoke_20261007_r2/relation_request_01.txt').read_text(encoding='utf-8')
    assert new_prompt==(AUDIT/'historical_prompt_reconstructed.txt').read_text(encoding='utf-8')
    assert new_prompt!=grouped_prompt
    loaded_hashes={}
    for name,h in old_preflight['protected_modules'].items():
        assert m.digest((ROOT/'src/biomedical_extractor'/name).read_bytes())==h
        assert m.digest((CACHE/'runtime/biomedical_extractor'/name).read_bytes())==h
        loaded_hashes[name]=h
    candidate_hashes=read(PRIOR/'candidate_hashes.json')
    for module in [m.relation,m.role]:
        name=Path(module.__file__).name
        assert m.digest(Path(module.__file__).read_bytes())==candidate_hashes['src/biomedical_extractor/'+name]
        loaded_hashes[name]=m.digest(Path(module.__file__).read_bytes())
    for name,module,prompt in [('relation',m.relation,m.relation.RELATION_EXTRACTION_SYSTEM_PROMPT),('role',m.role,m.role.PAPER_ROLE_EXTRACTION_SYSTEM_PROMPT)]:
        assert module._structured_payload_schema().model_json_schema()==read(PRIOR/(name+'_semantic_schema.json'))
        assert m.strict_transport_schema(module._structured_payload_schema())==read(PRIOR/(name+'_transport_schema.json'))
        assert m.digest(prompt.encode('utf-8'))==old_preflight['schemas'][name]['prompt_sha256']
    order=[]
    for i,(expected,actual,grouped) in enumerate(zip(historical,packet['entities'],prior['entities']),1):
        fields=['id','text','start','end','type']
        order.append({'position':i,'contract10':{k:expected[k] for k in fields},'candidate':{k:actual[k] for k in fields},'previous_smoke':{k:grouped[k] for k in fields},'exact_ordered_parity':expected==actual})
    m.write(m.REPORT/'mention_order_diff.json',{'order_parity_pass':True,'historical_order_provenance':'Contract 14 deterministic reconstruction from Contract-10 NER enumeration/source ordering, not graph-node grouping','positions':order})
    comparisons={k:'IDENTICAL' for k in ['source','mention_contents','mention_ids','mention_spans','mention_types','mention_scores','assembly_mapping','system_prompt','semantic_schema','transport_schema','transport_mechanism','model','reasoning','background','service_tier_request','token_ceiling','timeouts','polling','repair_budget','graph_construction','role_behavior','store_setting']}
    comparisons['mention_ordering']='CHANGED: restored exact Contract-10 source order'
    m.write(m.REPORT/'request_parity.json',{'passed':True,'single_intentional_variable':'mention serialization order','comparisons':comparisons,'loaded_module_hashes':loaded_hashes,'candidate_config':config,'source_sha256':m.digest(frozen.source.encode()),'new_complete_prompt_sha256':m.digest(new_prompt.encode()),'prior_complete_prompt_sha256':m.digest(grouped_prompt.encode()),'ordered_mention_packet_sha256':m.digest(m.canonical(packet['entities'])),'credential_lookup':'Same environment-first credential/endpoint lookup as prior smoke; no overrides or credentials recorded','limitations':'Historical source order and prompt are reconstructed, not an archived historical wire request. Role input varies only as a downstream consequence of generated isolated nodes.'})
    pre=read(m.REPORT/'preflight.json')
    pre.update(mentions=41,assembled_nodes=20,ordered_sequence_parity=True,single_variable_isolation_pass=True,production_defaults_modified=False,contract='14R',report_only_experiment=True)
    m.write(m.REPORT/'preflight.json',pre)
    return {'order_parity':'PASS','mentions':41,'assembled_nodes':20,'single_variable_isolation':'PASS','provider_requests':0,'prompt_sha256':m.digest(new_prompt.encode())}

if __name__=='__main__':
    print(json.dumps(verify()))
