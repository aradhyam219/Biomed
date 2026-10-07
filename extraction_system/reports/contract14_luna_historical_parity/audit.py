"""Offline Contract 14 evidence audit. Never construct or invoke a provider client."""
from __future__ import annotations
import ast
import hashlib
import importlib.metadata
import json
from pathlib import Path
import socket
import subprocess
import sys
import tomllib
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
REF = '1f12923ce54ab6718a00b8d8e8126536285dc6a8'
ACCEPTED = '16b00b4e7ebe99ec257adf93917d3487629be257'
RECENT = 'reports/luna_56_max_fast_smoke_20261007_r2'
CACHE = '.cache/luna_56_max_fast_smoke_20261007_r2'
OLD_CACHE = '.cache/relation_contract_10/papers/pmcid_pmc11824863.json'
UNKNOWN = 'UNKNOWN / NOT PRESERVED'
network_attempts = []
def deny_network(*args, **kwargs):
    network_attempts.append('blocked socket connection')
    raise RuntimeError('Contract 14 forbids network access')
socket.socket.connect = deny_network
socket.create_connection = deny_network

def git(*args):
    return subprocess.check_output(['git', '-c', 'safe.directory=C:/Projects/Biomed', '-C', str(ROOT.parent), *args])
def blob(rev, name):
    return git('show', rev + ':extraction_system/' + name)
def sha(data):
    return hashlib.sha256(data).hexdigest()
def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
def load(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))
def write(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)+'\n', encoding='utf-8', newline='\n')
def text(name, value):
    (OUT/name).write_text(value, encoding='utf-8', newline='\n')

start_head = git('rev-parse', 'HEAD').decode().strip()
start_branch = git('branch', '--show-current').decode().strip()
status = git('status', '--porcelain').decode()
tracked = git('ls-files', 'extraction_system').decode().splitlines()
original_hashes = {n: sha((ROOT.parent/n).read_bytes()) for n in tracked if (ROOT.parent/n).is_file()}
evidence = []
def record(name, kind='archived_original', rev=None, note=''):
    data = blob(rev, name) if rev else (ROOT/name).read_bytes()
    item = {'path': name, 'kind': kind, 'commit': rev, 'sha256': sha(data), 'note': note}
    if rev:
        item['git_blob'] = git('rev-parse', rev+':extraction_system/'+name).decode().strip()
    evidence.append(item)
    return data

old = load(OLD_CACHE)
recent = load(RECENT+'/inputs.json')
old_graph_path = 'reports/relation_contract_10/graphs/pmcid_pmc11824863.json'
old_graph = json.loads(record(old_graph_path, rev=REF))
assert old['graph'] == old_graph == load(old_graph_path)
assert old_graph == json.loads(blob(ACCEPTED, old_graph_path))
assert old['mention_level_relations'] == recent['baseline_relations']
assert old['source']['text'] == recent['source']['source_text']
assert old['mention_level_entities'] == recent['entities']
assert old['relation_provider_attempts'] == 1 and old['relation_provider_failures'] == 0
assert len(old_graph['nodes']) == 20 and len(old_graph['edges']) == 19
record(OLD_CACHE, note='Earliest preserved Contract-10 relation representation is post-parser/post-validator. Raw provider output is not retained.')
for name in ['.cache/relation_contract_10/run_contract_10.py', '.cache/relation_contract_10/repair_artifacts.py',
             'reports/relation_contract_10/summary.json', 'reports/relation_migration_12a/frozen_set_manifest.json',
             'reports/relation_migration_12a/papers/pmcid_pmc11824863.json']:
    record(name)
for name in ['inputs.json','preflight.json','requests.json','relations.json','graph.json','graph_before_roles.json',
             'relation_diagnostics.json','role_diagnostics.json','scientific_review.json','smoke_driver.py',
             'relation_semantic_schema.json','relation_transport_schema.json','candidate.patch']:
    record(RECENT+'/'+name)
for name in ['relation_request_01.txt','relation_raw_01.txt']:
    record(CACHE+'/'+name, note='Original ignored cache, not rewritten or replaced by reconstruction.')

old_code = record('src/biomedical_extractor/llm_relation_extraction.py', 'historical_git_source', REF)
for name in ['entity_assembly.py','graph.py','llm_pipeline.py','hunflair2.py','hunflair2_runtime.py']:
    record('src/biomedical_extractor/'+name, 'historical_git_source', REF)
    assert blob(REF, 'src/biomedical_extractor/'+name) == blob(ACCEPTED, 'src/biomedical_extractor/'+name)
assert old_code == blob(ACCEPTED, 'src/biomedical_extractor/llm_relation_extraction.py')

# Select only pure historical prompt/schema definitions; never execute factories.
tree = ast.parse(old_code.decode('utf-8'))
definitions = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in {'_build_prompt','_structured_payload_schema'}) or
               (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id=='RELATION_EXTRACTION_SYSTEM_PROMPT' for t in n.targets))]
namespace = {'json': json}
module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *definitions], type_ignores=[])
exec(compile(ast.fix_missing_locations(module), '<historical-pure-definitions>', 'exec'), namespace)
from biomedical_extractor.entity_extraction import Entity
from biomedical_extractor.llm_relation_extraction import _parse_structured_response, validate_relations, RELATION_EXTRACTION_SYSTEM_PROMPT
from biomedical_extractor.entity_assembly import assemble_document_entities
from biomedical_extractor.graph import build_graph_result
from openai.lib._parsing._responses import type_to_text_format_param
from openai import pydantic_function_tool

# E IDs encode the historical NER enumeration order. The archived recorder
# serialized mentions by graph node instead, so its array is not the RE input order.
old_mentions = sorted(old['mention_level_entities'], key=lambda e: int(e['id'][1:]))
assert [e['id'] for e in old_mentions] == ['E'+str(i) for i in range(1,42)]
assert old_mentions == sorted(old_mentions, key=lambda e:(e['start'],e['end'],e['type']))
old_entities = tuple(Entity(**e) for e in old_mentions)
new_entities = tuple(Entity(**e) for e in recent['entities'])
source = old['source']['text']
assert all(source[e.start:e.end] == e.text for e in old_entities)
old_prompt = namespace['_build_prompt'](source, old_entities, namespace['RELATION_EXTRACTION_SYSTEM_PROMPT'])
cache_order_prompt = namespace['_build_prompt'](source, new_entities, namespace['RELATION_EXTRACTION_SYSTEM_PROMPT'])
actual_prompt = (ROOT/CACHE/'relation_request_01.txt').read_text(encoding='utf-8')
assert cache_order_prompt == actual_prompt and old_prompt != actual_prompt
assert namespace['RELATION_EXTRACTION_SYSTEM_PROMPT'] == RELATION_EXTRACTION_SYSTEM_PROMPT
assert sha(RELATION_EXTRACTION_SYSTEM_PROMPT.encode('utf-8')) == '13f38a6e94db74b534eb0df0b139287ace2e714fc908276ce4c3572f9b25836f'
schema_type = namespace['_structured_payload_schema']()
semantic = schema_type.model_json_schema()
strict = pydantic_function_tool(schema_type)['function']['parameters']
wrapper_format = type_to_text_format_param(schema_type)
assert semantic == load(RECENT+'/relation_semantic_schema.json')
assert strict == wrapper_format['schema'] == load(RECENT+'/relation_transport_schema.json')
assert sha(canonical(semantic)) == '023435da3fa18abb77987313626636eff7bedda28739603db54a2f2c8137c945'
assert sha(canonical(strict)) == 'b0506680756b7ad8332d976a419cdee57a81e1051dd115f291f65d77bd656510'

text('historical_prompt_reconstructed.txt', old_prompt)
write('historical_mentions_reconstructed.json', old_mentions)
write('historical_semantic_schema_reconstructed.json', semantic)
write('historical_transport_schema_lock_version_reconstructed.json', strict)

raw = (ROOT/CACHE/'relation_raw_01.txt').read_text(encoding='utf-8')
parsed = _parse_structured_response(raw)
validated = validate_relations(source,new_entities,parsed)
recent_relations = load(RECENT+'/relations.json')['relations']
assert [{**r, 'score': r.get('score')} for r in parsed] == recent_relations
assert canonical(validated.to_dict()['relations']) == canonical(recent_relations)
assembly_old = assemble_document_entities(old_entities,source)
assembly_new = assemble_document_entities(new_entities,source)
assert assembly_old.to_dict() == assembly_new.to_dict()
replay = build_graph_result(old['paper_id'],assembly_new,validated).to_dict()
assert canonical(replay) == canonical(load(RECENT+'/graph_before_roles.json'))
new_graph = load(RECENT+'/graph.json')
assert canonical(replay['edges']) == canonical(new_graph['edges'])
assert canonical([{k:v for k,v in n.items() if k!='paper_role'} for n in new_graph['nodes']]) == canonical(replay['nodes'])
mapping = {e.id:n.id for n in assembly_new.document_entities for e in n.mentions}
write('entity_mapping_comparison.json', {'historical_order_status':'RECONSTRUCTED_FROM_EXACT_HISTORICAL_NER_ENUMERATION_AND_PRESERVED_IDS',
      'historical_re_order':[e.id for e in old_entities],'archived_postgraph_order':[e['id'] for e in old['mention_level_entities']],
      'recent_re_order':[e.id for e in new_entities],'records_identical_by_id':True,'mapping_identical':True,
      'mention_to_node':mapping,'historical_node_count':20,'recent_node_count':20,'sensitive_mentions':[e.to_dict() for e in old_entities if any(s in e.text.casefold() for s in ['sfpq','proline','amyloid','aβ','pi3k','phosphoinositide','akt','protein kinase b','mouse','mice'])]})

locks = {r:tomllib.loads(blob(r,'uv.lock').decode('utf-8')) for r in [REF,'HEAD']}
packages = ['openai','langchain-openai','langchain-core','pydantic']
versions = {r:{p['name']:p['version'] for p in d['package'] if p['name'] in packages} for r,d in locks.items()}
installed = {p:importlib.metadata.version(p) for p in packages}
assert versions[REF] == versions['HEAD'] == installed
for path in ['.venv/Lib/site-packages/langchain_openai/chat_models/base.py',
             '.venv/Lib/site-packages/openai/lib/_parsing/_responses.py',
             '.venv/Lib/site-packages/openai/lib/_pydantic.py']:
    record(path,'installed_lock_version_source',note='Supports conditional reconstruction, not proof of the historical installed runtime.')
record('uv.lock','historical_git_source',REF)
record('uv.lock','historical_git_source','HEAD')
record('src/biomedical_extractor/responses_execution.py')

rows = []
def row(variable, old_value, new_value, parity, affect, supporting, note=''):
    rows.append({'variable':variable,'contract10':old_value,'recent_luna_smoke':new_value,'parity':parity,'can_affect_model_output':affect,'evidence':supporting,'note':note})
OLD = OLD_CACHE
NEW = RECENT+'/preflight.json'
row('Model','gpt-5.6-luna','gpt-5.6-luna','IDENTICAL','YES',[OLD,RECENT+'/relation_diagnostics.json'])
row('Reasoning','max','max','IDENTICAL','YES',[OLD,RECENT+'/relation_diagnostics.json'])
row('Paper / source mode','PMCID:PMC11824863 / title plus complete abstract','PMCID:PMC11824863 / title plus complete abstract','IDENTICAL','YES',[OLD,RECENT+'/inputs.json'])
row('Source SHA-256',sha(source.encode()),sha(source.encode()),'IDENTICAL','YES',[OLD,RECENT+'/inputs.json'])
row('Source characters / UTF-8 bytes',{'characters':len(source),'bytes':len(source.encode())},{'characters':len(source),'bytes':len(source.encode())},'IDENTICAL','YES',[OLD,RECENT+'/inputs.json'])
row('Newline / Unicode',{'CR':source.count('\r'),'LF':source.count('\n'),'NFC':unicodedata.is_normalized('NFC',source)},{'CR':source.count('\r'),'LF':source.count('\n'),'NFC':unicodedata.is_normalized('NFC',source)},'IDENTICAL','YES',[OLD,RECENT+'/inputs.json'],'Extracted source strings compared as UTF-8 bytes; enclosing JSON file bytes need not match.')
row('Mention records by ID',sha(canonical({e['id']:e for e in old_mentions})),sha(canonical({e['id']:e for e in recent['entities']})),'IDENTICAL','YES',[OLD,RECENT+'/inputs.json'],'41 IDs, texts, types, offsets and scores match exactly; repeated mentions are retained.')
row('Model-facing ordered entity packet SHA-256',sha(canonical(old_mentions)),sha(canonical(recent['entities'])),'DIFFERENT','YES',['entity_mapping_comparison.json','src/biomedical_extractor/hunflair2.py@'+REF,'.cache/relation_contract_10/run_contract_10.py'],'Historical input order reconstructed from E IDs assigned by enumerate; saved historical cache was already reordered after graph construction.')
row('Entity ordering',[e['id'] for e in old_mentions],[e.id for e in new_entities],'DIFFERENT','YES',['entity_mapping_comparison.json',CACHE+'/relation_request_01.txt'])
row('RE entity granularity','mention-level','mention-level','IDENTICAL','YES',['src/biomedical_extractor/llm_pipeline.py@'+REF,RECENT+'/smoke_driver.py'])
row('Mention-to-node mapping',sha(canonical(mapping)),sha(canonical(mapping)),'IDENTICAL','NO',['entity_mapping_comparison.json'],'Both orders deterministically yield the same 20-node identity view; mappings are not added to the RE prompt.')
row('System prompt SHA-256',sha(RELATION_EXTRACTION_SYSTEM_PROMPT.encode()),sha(RELATION_EXTRACTION_SYSTEM_PROMPT.encode()),'IDENTICAL','YES',['src/biomedical_extractor/llm_relation_extraction.py@'+REF,NEW])
row('Complete model-input prompt SHA-256',sha(old_prompt.encode()),sha(actual_prompt.encode()),'DIFFERENT','YES',['historical_prompt_reconstructed.txt',CACHE+'/relation_request_01.txt'],'Historical value is explicitly reconstructed; recent value hashes the preserved exact input string.')
row('Message envelope','LangChain string input converted to a human/user message (historical code; exact wire envelope '+UNKNOWN+')','Direct Responses input string','DIFFERENT','POSSIBLY',['src/biomedical_extractor/llm_relation_extraction.py@'+REF,RECENT+'/smoke_driver.py'],'The so-called system prompt is prepended to the user/input string in both paths; no distinct developer/system message established.')
row('Semantic schema SHA-256',sha(canonical(semantic)),sha(canonical(semantic)),'IDENTICAL','YES',['historical_semantic_schema_reconstructed.json',RECENT+'/relation_semantic_schema.json'])
row('Transport schema SHA-256',{'actual_wire':UNKNOWN,'lock_version_reconstruction':sha(canonical(strict))},sha(canonical(strict)),'UNKNOWN','YES',['historical_transport_schema_lock_version_reconstructed.json',RECENT+'/relation_transport_schema.json','.venv/Lib/site-packages/openai/lib/_parsing/_responses.py'],'Lock-version wrapper uses responses.parse(text_format=Pydantic) and SDK strict conversion; its reconstructed transport matches the recent schema. Do not equate semantic versus transport hashes with historical schema drift.')
row('Response-format mechanism','LangChain with_structured_output(Pydantic), nonstreaming Responses parse path inferred from locked wrapper','Direct SDK Responses create with text.format json_schema strict=True','DIFFERENT','POSSIBLY',['src/biomedical_extractor/llm_relation_extraction.py@'+REF,'src/biomedical_extractor/responses_execution.py'],'Actual historical wire request not preserved.')
row('Background','Not specified by historical factory; synchronous wrapper invocation','True, background create/retrieve polling','DIFFERENT','POSSIBLY',['src/biomedical_extractor/llm_relation_extraction.py@'+REF,RECENT+'/requests.json'])
row('Service tier',{'requested':'Not specified by historical factory','observed':UNKNOWN},{'requested':'fast','observed':'priority'},'DIFFERENT','UNKNOWN',['src/biomedical_extractor/llm_relation_extraction.py@'+REF,RECENT+'/relation_diagnostics.json'],'Historical Standard processing is not asserted. No evidence establishes tier as the cause of scientific output differences.')
row('Max output tokens',128000,128000,'IDENTICAL','YES',[OLD,NEW])
row('Repair budget / actual repairs',{'maximum':2,'actual':0},{'maximum':2,'actual':0},'IDENTICAL','NO',['.cache/relation_contract_10/run_contract_10.py','reports/relation_contract_10/summary.json',RECENT+'/relation_diagnostics.json'])
row('SDK retries','0 configured by factory','0 configured by factory','IDENTICAL','NO',['src/biomedical_extractor/llm_relation_extraction.py@'+REF,'src/biomedical_extractor/llm_relation_extraction.py'])
row('Dependencies',{'lock':versions[REF],'installed_at_historical_execution':UNKNOWN},{'lock':versions['HEAD'],'installed':installed},'UNKNOWN','POSSIBLY',['uv.lock@'+REF,'uv.lock@HEAD'],'Dependency lock is identical; historical runtime installation was not recorded.')
row('store',{'historical_factory':'not explicitly configured','actual_wire':UNKNOWN},False,'UNKNOWN','UNKNOWN',['src/biomedical_extractor/llm_relation_extraction.py@'+REF,'src/biomedical_extractor/responses_execution.py'],'Recent executor explicitly sends store=False. Historical effective value was not retained.')
for name in ['temperature','top_p','seed','parallel/tool settings']:
    row(name,{'historical_factory':'not explicitly configured','actual_wire':UNKNOWN},{'factory':'not explicitly configured','actual_wire':UNKNOWN},'UNKNOWN','POSSIBLY',['src/biomedical_extractor/llm_relation_extraction.py@'+REF,RECENT+'/smoke_driver.py'],'Smoke capture saves selected parameters, not a complete serialized wire request. No historical effective value inferred.')
row('Raw relation count',UNKNOWN,19,'UNKNOWN','NO',['.cache/relation_contract_10/run_contract_10.py',CACHE+'/relation_raw_01.txt'])
row('Validated relation count',19,19,'IDENTICAL','NO',[OLD,RECENT+'/relations.json'])
row('Graph relation / edge count',19,19,'IDENTICAL','NO',[old_graph_path,RECENT+'/graph.json'])
row('Unconnected nodes',3,4,'DIFFERENT','NO',[old_graph_path,RECENT+'/graph.json'],'Two new isolated kinase long-form nodes, one formerly isolated Mice node now connected; counts alone do not score quality.')
write('parity_matrix.json',{'primary_verdict':'B','historical_raw_stop_condition':True,'rows':rows})

# Every baseline relation is included in the comparison, with full rich fields.
matches = [[0],[1],[2],[],[3],[4],[5],[6],[7],[8],[9],[10],[11],[12],[13],[14],[15],[16,17],[18]]
classes = ['MODEL_REPRESENTATION_CHANGE','MODEL_REPRESENTATION_CHANGE','MODEL_OMISSION','UNKNOWN','MODEL_REPRESENTATION_CHANGE','MODEL_REPRESENTATION_CHANGE','MODEL_REPRESENTATION_CHANGE','MODEL_REPRESENTATION_CHANGE','MODEL_REPRESENTATION_CHANGE','MODEL_REPRESENTATION_CHANGE','MODEL_REPRESENTATION_CHANGE','MODEL_REPRESENTATION_CHANGE','MODEL_REPRESENTATION_CHANGE','MODEL_REPRESENTATION_CHANGE','MODEL_OMISSION','MODEL_REPRESENTATION_CHANGE','MODEL_REPRESENTATION_CHANGE','MODEL_REPRESENTATION_CHANGE','MODEL_REPRESENTATION_CHANGE']
judgments = ['representation change','preserved','material scientific loss','nonmaterial knowledge-gap omission','representation change','preserved','preserved','preserved','preserved','preserved','preserved','preserved','preserved','preserved','material scientific loss','material scientific loss and endpoint change','material scientific loss and endpoint change','representation change','preserved']
notes = [
 'Title benefit relation targets the Mice species mention instead of AD disease; scientific improvement retained. This connects the formerly isolated Mice node.',
 'Disease characterization retained.',
 'Antioxidant functions and gene-expression regulation within brain neurons absent from the current raw assertion and its evidence. Earliest current loss is already at raw model output.',
 'Historical explicit knowledge-gap relation absent. Ledger marks nonmaterial; raw historical presence unknown.',
 'AD mouse-model assertion retained, but injection context was moved to the amyloid-beta induction record.',
 'Injection intervention and model-induction direction retained.',
 'Viral intervention and hippocampal AD mice context retained; endpoints select Mice rather than AD.',
 'Recognition/memory improvement retained, target Mice rather than AD.',
 'APP reduction and intervention/context retained.',
 'Tau reduction and intervention/context retained.',
 'APP marker association with AD retained.',
 'Tau marker association with AD retained.',
 'GST upregulation retained in assertion/predicate; effects array is empty, but no loss of the upregulation science.',
 'HO-1 upregulation retained in assertion/predicate; effects array is empty, but no loss of the upregulation science.',
 'Bcl-2/Bax ratio and anti/proapoptotic descriptions retained; SFPQ intervention and AD mice context absent in current raw fields and evidence.',
 'Ratio direction retained; current raw source E33 rather than baseline E32 isolates the full-name PI3K node. Current raw intervention/context absent. Mapping is deterministic and unchanged; this is generation-side endpoint selection, not remapping loss.',
 'Ratio direction retained; current raw source E36 rather than baseline E35 isolates the full-name AKT node. Current raw intervention/context absent. Mapping is deterministic and unchanged; this is generation-side endpoint selection, not remapping loss.',
 'Explicit activation retained in raw assertions/effects through two SFPQ-to-component associations rather than the baseline PI3K-to-AKT co-participation edge. Endpoint/topology representation differs; this does not demonstrate downstream deletion.',
 'Tentative prevention/treatment target retained.'
]
by_id = {e.id:e.to_dict() for e in new_entities}
causal=[]
for i,(relation,indices,classification,judgment,note) in enumerate(zip(old['mention_level_relations'],matches,classes,judgments,notes)):
    causal.append({'contract10_relation_index':i,'contract10_relation':relation,'contract10_source_entity':by_id[relation['source']],
        'contract10_target_entity':by_id[relation['target']],'recent_relation_indices':indices,'recent_relations':[recent_relations[j] for j in indices],
        'classification':classification,'semantic_judgment':judgment,'rationale':note,
        'historical_provider_raw_boundary':UNKNOWN,'recent_raw_equals_validated':True,
        'causal_scope':'Classifies current raw output relative to historical validated baseline, not intrinsic model regression or historical parser behavior.'})
write('relation_causal_diff.json',{'historical_earliest_available':'validated mention-level relations','historical_raw_output':UNKNOWN,
    'current_earliest_available':'preserved provider output_text JSON before parsing','current_raw_count':19,
    'current_raw_parsed_validated_equal':True,'comparison_normalization':'JSON array/list equivalence and addition of score=null, absent from generation schema; no scientific fields changed.',
    'current_graph_replay_equal':True,'current_roles_leave_edges_unchanged':True,
    'first_established_request_divergence':'Mention-list serialization order before prompt construction',
    'first_current_output_divergence':'Provider output_text already contains omissions and endpoint changes',
    'rows':causal})

schema_detail=[]
for name,prop in semantic['$defs']['StructuredRelation']['properties'].items():
    strict_prop=strict['$defs']['StructuredRelation']['properties'][name]
    schema_detail.append({'field':name,'semantic_required':name in semantic['$defs']['StructuredRelation'].get('required',[]),
       'strict_required':name in strict['$defs']['StructuredRelation']['required'],'semantic':prop,'strict':strict_prop})
write('schema_comparison.json',{'domain_semantic_equivalence':True,'historical_actual_model_facing_equivalence':UNKNOWN,
 'locked_wrapper_reconstruction_matches_recent_transport':True,'schema_hashes':{'semantic':sha(canonical(semantic)),'transport':sha(canonical(strict))},
 'fields':schema_detail,'object_closure':{'semantic':semantic['$defs']['StructuredRelation'].get('additionalProperties'),'strict':strict['$defs']['StructuredRelation'].get('additionalProperties')},
 'relation_array':{'semantic':semantic['properties']['relations'],'strict':strict['properties']['relations']},
 'warning':'Both SDK paths perform strict conversion in the locked dependency versions. Semantic versus strict transport differences alone do not establish a change between invocations.'})

after = {n:sha((ROOT.parent/n).read_bytes()) for n in original_hashes}
assert original_hashes == after
assert git('rev-parse','HEAD').decode().strip() == start_head
assert git('branch','--show-current').decode().strip() == start_branch
assert not network_attempts
for item in evidence:
    assert sha(blob(item['commit'],item['path']) if item['commit'] else (ROOT/item['path']).read_bytes()) == item['sha256']
reconstructed=[{'path':f.name,'sha256':sha(f.read_bytes()),'kind':'reconstructed_not_archived','note':'Historical code plus archived mention fields; see audit.py. Not a recovered request or provider output.'}
               for f in OUT.iterdir() if 'reconstructed' in f.name]
write('evidence_manifest.json',{'branch':start_branch,'start_head':start_head,'initial_status':status,
 'reference_commit':REF,'accepted_report_commit':ACCEPTED,'reference_confirmation':'Relevant NER, RE, assembly, graph and pipeline Git blobs match the accepted Contract-10 report commit; graph is byte-derived JSON-equivalent at both commits.',
 'original_artifacts':evidence,'reconstructed_artifacts':reconstructed,'missing':['Historical raw provider response/output_text','Historical serialized request envelope and actual transport schema','Historical runtime-installed dependency versions and observed service tier'],
 'stop_condition':'Historical raw provider output unavailable and cannot be deterministically reconstructed; audit stops with bounded findings and explicit unknowns. No inference or guess substitutes for it.',
 'validation':{'provider_clients_created':0,'provider_api_calls':0,'socket_connection_attempts':0,'production_and_prior_tracked_files_unchanged':True,'all_prior_tracked_file_hashes_verified':len(original_hashes),
 'referenced_cache_and_historical_artifacts_unchanged':True,'branch_and_head_unchanged_during_audit':True,'no_reset':True,'reconstruction_labelled':True},
 'future_experiment_not_run':'Only under a new contract: capture full requests and raw responses while holding source, mention ordering, prompt, strict schema and provider settings fixed. It cannot recover the missing historical raw output or by itself prove the cause of this historical run.'})

table='| Variable | Contract 10 | Recent smoke | Parity | Can affect output? |\n|---|---|---|---|---|\n'
for r in rows:
    def short(v):
        s=json.dumps(v,ensure_ascii=True) if not isinstance(v,str) else v
        return s.replace('|','\\|')
    table+=f"| {r['variable']} | {short(r['contract10'])} | {short(r['recent_luna_smoke'])} | {r['parity']} | {r['can_affect_model_output']} |\n"
text('request_diff.md', '# Model-facing request parity\n\nHistorical request values below are reconstructed where labelled. An actual historical wire request is not archived. Evidence paths and per-variable qualifications are in `parity_matrix.json` and `evidence_manifest.json`.\n\n## Established input drift\n\nContract 10 passed source-ordered NER entities directly to RE. HunFlair2 enumerates E IDs in prediction order; its runtime sorts source offsets. The historical recorder subsequently walked graph nodes to save `mention_level_entities`. That saved array groups mentions by canonical node and is not the historical RE input order. The 12A manifest reused that array unchanged; the fresh smoke replayed it unchanged.\n\n- Historical input order: E1 through E41 (deterministically reconstructed from IDs and historical code).\n- Recent input starts: E1, E8, E10, E16, E2, E4, E5, E11, E12, E17.\n- Source and per-ID mention records are identical; complete prompt bytes differ because the entity list order differs.\n- Prompt delimiters, JSON indentation, Unicode serialization and protected instructions otherwise reconstruct identically. The instructions are part of the user/input string, despite the constant being named system prompt.\n\n## Schema boundary\n\nThe verified semantic hash is `'+sha(canonical(semantic))+'`; the verified strict transport hash is `'+sha(canonical(strict))+'`. These describe two forms of the same domain schema, not necessarily two historical generation constraints. In the locked LangChain/OpenAI versions, nonstreaming Pydantic Responses parsing applies SDK strict conversion too, producing the same strict schema as the recent direct-SDK path. Both strict reconstructions require every relation property. Nullable fields such as intervention/surface_form become required-plus-nullable; effects/context arrays become required arrays; None defaults are stripped, object closure and descriptions preserved, no score field is present. See `schema_comparison.json` for every property. Actual historical wire schema remains UNKNOWN / NOT PRESERVED.\n\n## Execution variables\n\nHistorical factory: LangChain ChatOpenAI, Responses, max reasoning, 128000 ceiling, SDK retries zero, Pydantic structured binding, synchronous invocation, no explicit tier/background. Recent path: direct Responses SDK create/retrieve, background true, fast requested and priority observed. No evidence here establishes that tier or background changes scientific quality. Historical service tier, installed runtime, complete request envelope and raw response were not retained. The uv.lock versions match the current installed versions, but that is not proof of the old runtime.\n\n'+table)
text('summary.md', '# Contract 14 historical Luna parity audit\n\n**VERDICT B — Material request/input drift found.** The accepted Contract-10 Luna and recent Luna smoke did not receive the same ordered extraction prompt. This audit cannot attribute the regression to Luna itself.\n\nThe first established divergence is **mention-list ordering before prompt serialization**. Historical HunFlair2 assigned E1–E41 in source order, and the pipeline passed that sequence unchanged to RE. The Contract-10 recorder saved mentions later by iterating graph nodes; that grouped array became the 12A frozen packet and then the fresh smoke input. Source text, entity IDs/text/types/spans/scores, system instructions and deterministic assembly mapping match, but the model-facing entity order and complete prompt differ. See `entity_mapping_comparison.json`, `historical_prompt_reconstructed.txt`, and `request_diff.md`. Historical prompt is a deterministic reconstruction, not an archived wire request.\n\nThe reference commit `'+REF+'` contains the accepted Contract-10 implementation: the relevant source blobs match the accepted report commit `'+ACCEPTED+'`, and its SFPQ graph matches the cache and tracked historical graph. The cached 19 validated relation records exactly match the frozen baseline. The fresh smoke also has **19 relations, 20 nodes and 19 edges**; the contract introduction saying it had fewer relations is inaccurate for this fresh run. Four current nodes are isolated versus three historically.\n\n**The schema-change hypothesis is not established.** Semantic and strict transport hashes verify as specified. Reconstructing the historical Pydantic binding through the locked LangChain/OpenAI versions gives the same strict transport schema as the recent direct SDK path. Required/nullable transformations therefore cannot alone be blamed on a later conversion. The actual historical wire schema remains UNKNOWN / NOT PRESERVED. See `schema_comparison.json`.\n\nThe recent raw output already omits SFPQ antioxidant/gene-regulation detail, drops SFPQ intervention/AD mice context from three ratio records, and selects shorthand E33/E36 instead of the full-name kinase endpoints E32/E35. These are retained unchanged by parsing and validation. Deterministic assembly correctly applies the unchanged mapping; full-name kinase nodes become isolated because of raw endpoint selection, not a new endpoint remapper. Role enrichment attaches grounded metadata without changing any edge. Explicit PI3K/AKT activation remains present. See `relation_causal_diff.json` for all 19 baseline records.\n\n**Mandatory stop condition reached:** the historical recorder saved only validated results, not the raw provider response. Raw historical output cannot be deterministically reconstructed. It is therefore impossible to prove its raw-to-parsed/validated boundary, exact historical wire request, actual runtime-installed SDK or observed tier. No guessing or rerun was used. The primary verdict remains B because ordered prompt drift is independently established; it is not a claim that this drift caused the omissions. This is a bounded audit rather than a complete historical wire reconstruction.\n\nRuled out for the current losses: changed source text, changed mention contents, changed protected prompt instructions, changed deterministic mention-to-node mapping, parser/validator deletion, graph dropping of valid edges, and role-enrichment edge changes. Remaining uncertainty: how much ordering, message-envelope/provider execution differences, or stochastic variability contributed; historical raw semantics and effective transport/runtime/tier are not preserved.\n\nNo production behavior changed and no provider clients or API requests were made. Historical artifacts were hash-checked before/after; all prior tracked files remain unchanged. Only this audit directory is intended for the dedicated report commit. `evidence_manifest.json` distinguishes original artifacts, Git sources and reconstructions.\n')
print(json.dumps({'verdict':'B','first_divergence':'model-facing mention-list ordering','historical_raw_stop_condition':True,
 'source_identical':True,'mentions_identical_by_id':True,'assembly_identical':True,'system_prompt_identical':True,
 'historical_complete_prompt_reconstructed_sha256':sha(old_prompt.encode()),'recent_preserved_prompt_sha256':sha(actual_prompt.encode()),
 'locked_wrapper_transport_matches_recent':True,'current_raw_equals_validated':True,'network_calls':0}))
