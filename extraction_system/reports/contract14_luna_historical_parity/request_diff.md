# Model-facing request parity

Historical request values below are reconstructed where labelled. An actual historical wire request is not archived. Evidence paths and per-variable qualifications are in `parity_matrix.json` and `evidence_manifest.json`.

## Established input drift

Contract 10 passed source-ordered NER entities directly to RE. HunFlair2 enumerates E IDs in prediction order; its runtime sorts source offsets. The historical recorder subsequently walked graph nodes to save `mention_level_entities`. That saved array groups mentions by canonical node and is not the historical RE input order. The 12A manifest reused that array unchanged; the fresh smoke replayed it unchanged.

- Historical input order: E1 through E41 (deterministically reconstructed from IDs and historical code).
- Recent input starts: E1, E8, E10, E16, E2, E4, E5, E11, E12, E17.
- Source and per-ID mention records are identical; complete prompt bytes differ because the entity list order differs.
- Prompt delimiters, JSON indentation, Unicode serialization and protected instructions otherwise reconstruct identically. The instructions are part of the user/input string, despite the constant being named system prompt.

## Schema boundary

The verified semantic hash is `023435da3fa18abb77987313626636eff7bedda28739603db54a2f2c8137c945`; the verified strict transport hash is `b0506680756b7ad8332d976a419cdee57a81e1051dd115f291f65d77bd656510`. These describe two forms of the same domain schema, not necessarily two historical generation constraints. In the locked LangChain/OpenAI versions, nonstreaming Pydantic Responses parsing applies SDK strict conversion too, producing the same strict schema as the recent direct-SDK path. Both strict reconstructions require every relation property. Nullable fields such as intervention/surface_form become required-plus-nullable; effects/context arrays become required arrays; None defaults are stripped, object closure and descriptions preserved, no score field is present. See `schema_comparison.json` for every property. Actual historical wire schema remains UNKNOWN / NOT PRESERVED.

## Execution variables

Historical factory: LangChain ChatOpenAI, Responses, max reasoning, 128000 ceiling, SDK retries zero, Pydantic structured binding, synchronous invocation, no explicit tier/background. Recent path: direct Responses SDK create/retrieve, background true, fast requested and priority observed. No evidence here establishes that tier or background changes scientific quality. Historical service tier, installed runtime, complete request envelope and raw response were not retained. The uv.lock versions match the current installed versions, but that is not proof of the old runtime.

| Variable | Contract 10 | Recent smoke | Parity | Can affect output? |
|---|---|---|---|---|
| Model | gpt-5.6-luna | gpt-5.6-luna | IDENTICAL | YES |
| Reasoning | max | max | IDENTICAL | YES |
| Paper / source mode | PMCID:PMC11824863 / title plus complete abstract | PMCID:PMC11824863 / title plus complete abstract | IDENTICAL | YES |
| Source SHA-256 | 604ce7f15b0ca00853cfc4cc07039d51059792e907d3da07c08be40730fb1b5b | 604ce7f15b0ca00853cfc4cc07039d51059792e907d3da07c08be40730fb1b5b | IDENTICAL | YES |
| Source characters / UTF-8 bytes | {"characters": 1496, "bytes": 1501} | {"characters": 1496, "bytes": 1501} | IDENTICAL | YES |
| Newline / Unicode | {"CR": 0, "LF": 2, "NFC": true} | {"CR": 0, "LF": 2, "NFC": true} | IDENTICAL | YES |
| Mention records by ID | ebb0ba78d17b25c2a1ca0bc8e99a7bd4d84428349d446f3d03251bdf21ae355f | ebb0ba78d17b25c2a1ca0bc8e99a7bd4d84428349d446f3d03251bdf21ae355f | IDENTICAL | YES |
| Model-facing ordered entity packet SHA-256 | 63032955590e93eef90c0dfd87c99e653454f22dde4f3e1b069a7952ddb4433a | 7af02036660ba6d5581468deb3b777039c7a6912d4ea4c5ee1027387d10f5e0b | DIFFERENT | YES |
| Entity ordering | ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "E9", "E10", "E11", "E12", "E13", "E14", "E15", "E16", "E17", "E18", "E19", "E20", "E21", "E22", "E23", "E24", "E25", "E26", "E27", "E28", "E29", "E30", "E31", "E32", "E33", "E34", "E35", "E36", "E37", "E38", "E39", "E40", "E41"] | ["E1", "E8", "E10", "E16", "E2", "E4", "E5", "E11", "E12", "E17", "E20", "E22", "E41", "E3", "E18", "E21", "E6", "E7", "E9", "E13", "E14", "E15", "E19", "E40", "E23", "E24", "E25", "E26", "E27", "E28", "E29", "E30", "E31", "E32", "E33", "E34", "E38", "E35", "E36", "E37", "E39"] | DIFFERENT | YES |
| RE entity granularity | mention-level | mention-level | IDENTICAL | YES |
| Mention-to-node mapping | 79646a2ab181dbb0e11dcbc338bff4dba6e3d925c512701d4bd8c03b8e714239 | 79646a2ab181dbb0e11dcbc338bff4dba6e3d925c512701d4bd8c03b8e714239 | IDENTICAL | NO |
| System prompt SHA-256 | 13f38a6e94db74b534eb0df0b139287ace2e714fc908276ce4c3572f9b25836f | 13f38a6e94db74b534eb0df0b139287ace2e714fc908276ce4c3572f9b25836f | IDENTICAL | YES |
| Complete model-input prompt SHA-256 | 99db58b9b122f5cf7c4a7a5f7c3a0bcb8b53dd09676631af5dfe1e35bda7c3a6 | b47a63b66b7a3e42d4d1a899de27965defa101f071cd859ec5225ebf5fc96228 | DIFFERENT | YES |
| Message envelope | LangChain string input converted to a human/user message (historical code; exact wire envelope UNKNOWN / NOT PRESERVED) | Direct Responses input string | DIFFERENT | POSSIBLY |
| Semantic schema SHA-256 | 023435da3fa18abb77987313626636eff7bedda28739603db54a2f2c8137c945 | 023435da3fa18abb77987313626636eff7bedda28739603db54a2f2c8137c945 | IDENTICAL | YES |
| Transport schema SHA-256 | {"actual_wire": "UNKNOWN / NOT PRESERVED", "lock_version_reconstruction": "b0506680756b7ad8332d976a419cdee57a81e1051dd115f291f65d77bd656510"} | b0506680756b7ad8332d976a419cdee57a81e1051dd115f291f65d77bd656510 | UNKNOWN | YES |
| Response-format mechanism | LangChain with_structured_output(Pydantic), nonstreaming Responses parse path inferred from locked wrapper | Direct SDK Responses create with text.format json_schema strict=True | DIFFERENT | POSSIBLY |
| Background | Not specified by historical factory; synchronous wrapper invocation | True, background create/retrieve polling | DIFFERENT | POSSIBLY |
| Service tier | {"requested": "Not specified by historical factory", "observed": "UNKNOWN / NOT PRESERVED"} | {"requested": "fast", "observed": "priority"} | DIFFERENT | UNKNOWN |
| Max output tokens | 128000 | 128000 | IDENTICAL | YES |
| Repair budget / actual repairs | {"maximum": 2, "actual": 0} | {"maximum": 2, "actual": 0} | IDENTICAL | NO |
| SDK retries | 0 configured by factory | 0 configured by factory | IDENTICAL | NO |
| Dependencies | {"lock": {"langchain-core": "1.6.3", "langchain-openai": "1.6.2", "openai": "3.14.1", "pydantic": "2.13.5"}, "installed_at_historical_execution": "UNKNOWN / NOT PRESERVED"} | {"lock": {"langchain-core": "1.6.3", "langchain-openai": "1.6.2", "openai": "3.14.1", "pydantic": "2.13.5"}, "installed": {"openai": "3.14.1", "langchain-openai": "1.6.2", "langchain-core": "1.6.3", "pydantic": "2.13.5"}} | UNKNOWN | POSSIBLY |
| store | {"historical_factory": "not explicitly configured", "actual_wire": "UNKNOWN / NOT PRESERVED"} | false | UNKNOWN | UNKNOWN |
| temperature | {"historical_factory": "not explicitly configured", "actual_wire": "UNKNOWN / NOT PRESERVED"} | {"factory": "not explicitly configured", "actual_wire": "UNKNOWN / NOT PRESERVED"} | UNKNOWN | POSSIBLY |
| top_p | {"historical_factory": "not explicitly configured", "actual_wire": "UNKNOWN / NOT PRESERVED"} | {"factory": "not explicitly configured", "actual_wire": "UNKNOWN / NOT PRESERVED"} | UNKNOWN | POSSIBLY |
| seed | {"historical_factory": "not explicitly configured", "actual_wire": "UNKNOWN / NOT PRESERVED"} | {"factory": "not explicitly configured", "actual_wire": "UNKNOWN / NOT PRESERVED"} | UNKNOWN | POSSIBLY |
| parallel/tool settings | {"historical_factory": "not explicitly configured", "actual_wire": "UNKNOWN / NOT PRESERVED"} | {"factory": "not explicitly configured", "actual_wire": "UNKNOWN / NOT PRESERVED"} | UNKNOWN | POSSIBLY |
| Raw relation count | UNKNOWN / NOT PRESERVED | 19 | UNKNOWN | NO |
| Validated relation count | 19 | 19 | IDENTICAL | NO |
| Graph relation / edge count | 19 | 19 | IDENTICAL | NO |
| Unconnected nodes | 3 | 4 | DIFFERENT | NO |
