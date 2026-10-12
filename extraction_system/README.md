# Entity Extraction System

Ordinary biomedical text becomes evidence-backed Graph JSON through pretrained
HunFlair2, document-local assembly, grounded LLM relations and paper roles.
The current implementation is an accepted functional baseline with documented
scientific limitations.

See [provisioning](docs/PROVISIONING.md), [product specification](docs/product/CURRENT_SPEC.md)
and [architecture](docs/ARCHITECTURE.md). Runtime/model identities and frozen prompt
hashes are recorded in `provisioning/baseline.json`.

```python
from biomedical_extractor import LLMExtractionPipeline
pipeline = LLMExtractionPipeline.from_hunflair2(offline=True)
graph = pipeline.extract_graph(text, document_id="paper-1", paper_title=title)
print(graph.to_json())
```

Supply provider credentials externally. The main locked environment and isolated
HunFlair2 environment are both required. Research history remains on
`extraction_system_v2` and the immutable baseline tag.

Run current deterministic tests with `uv run --locked python -m unittest discover
-s tests -v` and graph consumer checks with `node --test viewer/tests/adapter.test.mjs`.
The existing viewer can be served with `uv run --locked python -m http.server 8765
--directory viewer` and opened at http://127.0.0.1:8765/.
