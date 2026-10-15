# Entity Extraction System

Ordinary biomedical text becomes evidence-backed Graph JSON through pretrained
HunFlair2, document-local assembly, grounded LLM relations and paper roles.
The current implementation is an accepted functional baseline with documented
scientific limitations.

See [provisioning](docs/PROVISIONING.md), [product specification](docs/product/CURRENT_SPEC.md)
and [architecture](docs/ARCHITECTURE.md). Runtime/model identities and frozen prompt
hashes are recorded in the packaged CPU/CUDA profiles and
`reports/phase2/luna-freeze.json`. The current delivery provider path is frozen
GPT-5.6 Luna / max / Fast / background Responses; `provisioning/baseline.json`
preserves the original historical baseline.

```python
from biomedical_extractor import (
    LLMExtractionPipeline, prepare_graph_export, verify_graph_profile,
    export_graph, graph_json, validate_graph, input_fingerprints,
)
pipeline = LLMExtractionPipeline.from_hunflair2(offline=True)
context = prepare_graph_export(pipeline, text=text, document_id="paper-1", paper_title=title)
graph = pipeline.extract_graph(text, document_id="paper-1", paper_title=title)
verify_graph_profile(pipeline, context, text=text)
artifact = export_graph(graph, text=text, paper_title=title, context=context)
print(graph_json(artifact))
validate_graph(artifact, text=text, paper_title=title)
```

Install a release wheel for packaged build identity. The isolated baseline NER
runtime must be provisioned separately. Graph delivery preserves CPU support and
has a separately gated Linux/CUDA profile (`--device cuda`); raw `graph.to_json()`
remains unversioned for existing internal callers.
Contract validation/fingerprints work offline without the model runtime. See
[Graph Contract v1](docs/GRAPH_CONTRACT.md) for explicit recorded replay contexts,
legacy display compatibility, pure cache eligibility and validation limitations.

```powershell
biomedical-extract-llm --text "BRCA1 is associated with breast cancer." --document-id paper-1 --paper-title "Exact title" --output-format graph --hunflair2-offline
```

Supply provider credentials externally. The main locked environment and isolated
HunFlair2 environment are both required. Research history remains on
`extraction_system_v2` and the immutable baseline tag.

Run current deterministic tests with `uv run --locked python -m unittest discover
-s tests -v` and graph consumer checks with `node --test viewer/tests/adapter.test.mjs`.
The existing viewer can be served with `uv run --locked python -m http.server 8765
--directory viewer` and opened at http://127.0.0.1:8765/.
