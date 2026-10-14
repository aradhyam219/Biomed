"""Narrow baseline configuration verification for the v1 export boundary.

Preflight reads local artifacts and isolated distribution metadata, without
loading a model. Postflight checks the NER metadata actually returned and the
bound provider executors. Raw extraction remains independent of this policy.
"""
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from .graph_contract import (GraphValidationError, contract_resource, input_fingerprints,
                             release_context, profile_identity, _document_id)
from .hunflair2 import HunFlair2BioMedExtractor, HunFlair2IsolatedRuntime
from .llm_relation_extraction import LLMRelationExtractor, OpenAIConfig
from .llm_paper_roles import LLMPaperRoleExtractor
from .responses_execution import ResponsesBackgroundExecutor, strict_transport_schema
from . import llm_relation_extraction as relation_module, llm_paper_roles as role_module
from .ner_runners import _hunflair2_artifact, _sha256_file


def _fail(field):
    raise GraphValidationError(f'unsupported/unverified v1 baseline configuration: {field}')


def _implementation(profile):
    for name, expected in profile['implementation_sha256'].items():
        actual = sha256(Path(__file__).with_name(name).read_text(encoding='utf-8-sig').encode()).hexdigest()
        if actual != expected:
            _fail(name)


def check_graph_options(config: OpenAIConfig, *, model: str, device: str | None,
                        runtime_script=None):
    """Reject unsupported scientific CLI/env overrides before producer construction."""
    p = contract_resource('baseline-profile.json')
    for name, expected in p['relation']['configuration'].items():
        if getattr(config, name) != expected:
            _fail(f'relation.{name}')
    if config.base_url not in (None, 'https://api.openai.com/v1'):
        _fail('provider endpoint')
    if model != p['ner']['model_identifier'] or device not in (None, 'cpu'):
        _fail('NER model/device')
    if runtime_script is not None and Path(runtime_script).resolve() != Path(__file__).with_name('hunflair2_runtime.py').resolve():
        _fail('runtime script override')
    _implementation(p)


def _provider(extractor, section, p):
    expected_type = LLMRelationExtractor if section == 'relation' else LLMPaperRoleExtractor
    if type(extractor) is not expected_type:
        _fail(f'injected {section} producer')
    descriptor = p[section]
    executor = extractor._background_executor
    if type(executor) is not ResponsesBackgroundExecutor:
        _fail(f'{section} execution mode')
    from openai import OpenAI
    if type(executor._client) is not OpenAI or str(executor._client.base_url).rstrip('/') != 'https://api.openai.com/v1':
        _fail(f'{section} provider')
    configuration = descriptor['configuration'] if section == 'relation' else descriptor
    for field, attr in [('model','_model'),('reasoning_effort','_reasoning_effort'),('service_tier','_service_tier'),
                        ('max_completion_tokens','_max_output_tokens'),('poll_interval_seconds','_poll_interval_seconds'),
                        ('generation_timeout_seconds','_generation_timeout_seconds')]:
        if getattr(executor, attr) != configuration[field]:
            _fail(f'{section}.{field}')
    if extractor._max_retries != configuration['max_retries']:
        _fail(f'{section}.repair budget')
    if sha256(extractor._prompt.encode()).hexdigest() != descriptor['prompt_sha256']:
        _fail(f'{section}.prompt')
    module = relation_module if section == 'relation' else role_module
    semantic = module._structured_payload_schema()
    if semantic.model_json_schema() != descriptor['semantic_schema'] or executor._schema != strict_transport_schema(semantic):
        _fail(f'{section}.schema')


def _runtime(pipeline, p):
    if type(pipeline.entity_extractor) is not HunFlair2BioMedExtractor:
        _fail('injected entity producer')
    runtime = pipeline.entity_extractor._runtime
    if type(runtime) is not HunFlair2IsolatedRuntime:
        _fail('injected NER runtime')
    if runtime._model_identifier != p['ner']['model_identifier'] or runtime._device != 'cpu':
        _fail('NER model/device')
    if runtime._runtime_script.resolve() != Path(__file__).with_name('hunflair2_runtime.py').resolve():
        _fail('runtime script')
    return runtime


def prepare_graph_export(pipeline, *, text: str, document_id: str, paper_title: str = '', context=None):
    """Preflight a real baseline pipeline before any paid extraction submission.

    Runtime paths and credentials are excluded from identity. Only a provisioned
    CPU baseline is initially supported. Reads metadata without model imports.
    """
    input_fingerprints(text, paper_title)
    _document_id(document_id)
    context = context or release_context()
    context.__post_init__()
    p = context.configuration
    _implementation(p)
    _provider(pipeline.relation_extractor, 'relation', p)
    runtime = _runtime(pipeline, p)
    if not pipeline._automatic_paper_roles:
        _fail('automatic roles disabled')
    if pipeline.paper_role_extractor is not None:
        _provider(pipeline.paper_role_extractor, 'roles', p)
    config = pipeline._paper_role_config or OpenAIConfig.from_environment()
    check_graph_options(config, model=runtime._model_identifier, device=runtime._device)
    # Freeze the effective lazy-role configuration now, not after NER/relations.
    pipeline._paper_role_config = config
    artifact, revision = _hunflair2_artifact(runtime._runtime_cache, runtime._model_identifier)
    if artifact is None or revision != p['ner']['model_revision'] or _sha256_file(artifact) != p['ner']['model_artifact_sha256']:
        _fail('NER artifact/revision')
    observed = _isolated_versions(runtime)
    for key in ('python', 'flair', 'pytorch', 'transformers', 'scispacy', 'spacy', 'en_core_sci_sm'):
        if observed.get(key) != p['ner']['runtime'][key]:
            _fail(f'NER runtime {key}')
    runtime._last_metadata = None
    runtime._v1_expected_profile = _LiveNERProfile(p, runtime)
    pipeline._v1_expected_profile = p
    pipeline._last_graph_role_extractor = None
    return context


def verify_graph_profile(pipeline, context, *, text: str):
    """Check the actual returned NER metadata and bound provider configuration."""
    p = context.configuration
    _implementation(p)
    _provider(pipeline.relation_extractor, 'relation', p)
    runtime = _runtime(pipeline, p)
    if text.strip():
        verify_ner_metadata(runtime._last_metadata, _LiveNERProfile(p, runtime))
    if pipeline._last_graph_role_extractor is not None:
        _provider(pipeline._last_graph_role_extractor, 'roles', p)


class _LiveNERProfile:
    """Carry interpreter binding outside the unchanged scientific descriptor.

    The protected NER bridge passes only its expected profile to post-NER
    verification. This private binding lets that check observe distribution
    metadata from the same selected interpreter, before any relation submission.
    Retain the authoritative descriptor by reference so replaced sections are
    revalidated at the post-NER checkpoint. The binding never enters public JSON.
    """

    def __init__(self, descriptor, runtime):
        self.descriptor = descriptor
        self.runtime = runtime


def _isolated_versions(runtime):
    """Read release metadata using the interpreter selected by the NER bridge."""
    executable = runtime._runtime_python
    if executable is None:
        candidates = [Path('.cache/hunflair2/runtime/bin/python'), Path('.cache/hunflair2/runtime/Scripts/python.exe')]
        executable = next((v for v in candidates if v.is_file()), candidates[0])
    packages = {'flair':'flair','pytorch':'torch','transformers':'transformers','scispacy':'scispacy','spacy':'spacy','en_core_sci_sm':'en-core-sci-sm'}
    code = 'import importlib.metadata as m,json,platform; print(json.dumps({"python":platform.python_version(),**{k:m.version(v) for k,v in '+repr(packages)+'.items()}}))'
    try:
        observed = json.loads(subprocess.check_output([str(executable),'-c',code], text=True, timeout=30))
        if not isinstance(observed, dict):
            raise ValueError('distribution metadata must be an object')
        return observed
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise GraphValidationError('isolated runtime identity unavailable') from error


def verify_ner_metadata(observed, profile, *, pytorch_distribution=None):
    """Check actual model/build metadata, with one corroborated CPU-only pair.

    The descriptor records the distribution release. Literal module build
    2.14.0+cpu additionally requires distribution 2.14.0, actual CPU, no CUDA
    runtime and CUDA unavailable. Live evidence comes from the bound inference
    interpreter; retained-run callers supply the captured distribution release.
    No suffix normalization or other local-build acceptance occurs.
    """
    live_runtime = None
    if isinstance(profile, _LiveNERProfile):
        live_runtime = profile.runtime
        profile = profile.descriptor
        profile_identity(profile)  # Revalidate all current sections before relations.
    if not isinstance(observed, dict) or not isinstance(observed.get('runtime'), dict):
        _fail('missing actual NER metadata')
    for key in ('model_identifier', 'model_revision', 'model_artifact_sha256'):
        if observed.get(key) != profile['ner'][key]:
            _fail(f'actual NER {key}')
    runtime = observed['runtime']
    # Even exact version observations must not contradict the CPU-only policy.
    if runtime.get('cuda_available', False) is not False or runtime.get('cuda_version') is not None:
        _fail('actual NER CUDA-backed runtime')
    expected_release = profile['ner']['runtime']['pytorch']
    if pytorch_distribution is not None and pytorch_distribution != expected_release:
        _fail('actual NER PyTorch distribution release')
    for key, expected in profile['ner']['runtime'].items():
        if key == 'offset_mechanics' or runtime.get(key) == expected:
            continue
        if key == 'pytorch' and expected == '2.14.0' and runtime.get(key) == '2.14.0+cpu':
            profile_identity(profile)  # Exception applies only to the original descriptor.
            if live_runtime is not None:
                pytorch_distribution = _isolated_versions(live_runtime).get('pytorch')
            if (pytorch_distribution != '2.14.0' or runtime.get('device') != 'cpu'
                    or 'cuda_version' not in runtime or runtime['cuda_version'] is not None
                    or runtime.get('cuda_available') is not False):
                _fail('uncorroborated CPU PyTorch module build')
            continue
        _fail(f'actual NER runtime {key}')
