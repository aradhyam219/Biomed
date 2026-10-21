"""Installed-wheel gate; run outside checkout with copied saved-stage inputs."""
import json
from pathlib import Path
import sys
from unittest.mock import patch

from jsonschema import Draft202012Validator
from biomedical_extractor import (contract_resource, input_fingerprints, validate_graph,
    release_context, export_graph, graph_json, cache_eligibility, GraphValidationError,
    LLMExtractionPipeline, Entity, PaperRole, PaperRoleRecord, PaperRoleExtractionResult)
from biomedical_extractor.relation_extraction import validate_relations
from biomedical_extractor.graph_contract import delivery_profile, profile_identity
import biomedical_extractor.graph_contract as contract


def main(directory):
    fixtures = Path(directory)
    with patch('subprocess.check_output', side_effect=AssertionError('Git/process access forbidden in installed gate')):
        ctx = release_context()
        cuda = release_context(device='cuda')
        assert profile_identity(ctx.configuration) == 'ees-35a70f202f4e6659fd1578a8df14243243bbabe011b3379ee154704dacf3d76f'
        assert profile_identity(cuda.configuration) == 'ees-9c3d817bf294bab6b6335a362e5aed289f9d004401bdb67f915746a6dafc5ed8'
        assert cuda.configuration == delivery_profile('cuda:0')
        assert profile_identity(contract_resource('baseline-profile.json')) == 'ees-cfeec6ccd400b9f44abbef35551944aa074ee3d79d3e5ec18dd7d7551c76e0de'
        for name in ('graph-v1.schema.json', 'graph-legacy.schema.json'):
            Draft202012Validator.check_schema(contract_resource(name))
        for row in contract_resource('fingerprint-examples.json'):
            assert input_fingerprints(row['text'], row['paper_title']) == {k:row[k] for k in ('source_sha256','extraction_input_sha256')}
        legacy = json.loads((fixtures/'viewer.json').read_text(encoding='utf-8'))
        assert validate_graph(legacy).format == 'legacy'
        for path in sorted(fixtures.glob('baseline-*.json')):
            case = json.loads(path.read_text(encoding='utf-8'))
            class NER:
                def extract_entities(self, text):
                    assert text == case['text']
                    return tuple(Entity(**value) for value in case['entities'])
            class RE:
                def extract_relations(self, text, entities):
                    return validate_relations(text, entities, case['relations'])
            class Roles:
                def extract_roles(self, title, text, targets):
                    assert title == case['paper_title']
                    return PaperRoleExtractionResult(tuple(PaperRoleRecord(r['node_id'], PaperRole(**r['paper_role'])) for r in case['roles']))
            pipeline = LLMExtractionPipeline(NER(), RE(), Roles() if case['roles'] else None)
            result = pipeline.extract_graph(case['text'], document_id=case['document_id'], paper_title=case['paper_title'])
            assert result.to_dict() == case['expected_graph']
            assert validate_graph(case['expected_graph']).format == 'legacy'
            artifact = export_graph(result, text=case['text'], paper_title=case['paper_title'], context=ctx, generated_at='2026-10-13T00:00:00Z')
            assert {k:artifact[k] for k in ('document','nodes','edges')} == case['expected_graph']
            assert json.loads(graph_json(artifact)) == artifact
            assert cache_eligibility(artifact, document_id=case['document_id'], text=case['text'], paper_title=case['paper_title']).eligible
        package = Path(contract.__file__).parent
        identity = package/'contract_resources/release.json'
        saved = identity.read_bytes()
        try:
            identity.unlink()
            try: release_context()
            except GraphValidationError: pass
            else: raise AssertionError('missing installed identity accepted')
        finally: identity.write_bytes(saved)
        source = package/'graph.py'
        saved = source.read_bytes()
        try:
            source.write_bytes(saved+b'\n# modified build\n')
            try: release_context()
            except GraphValidationError: pass
            else: raise AssertionError('modified installed source accepted')
        finally: source.write_bytes(saved)
        print(json.dumps({'installed_release':ctx.extractor_version,'build_revision':ctx.build_revision,'offline_installed_gates':'passed'},sort_keys=True))


if __name__=='__main__': main(sys.argv[1])
