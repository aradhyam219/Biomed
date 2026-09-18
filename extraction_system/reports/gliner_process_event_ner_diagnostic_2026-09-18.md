# GLiNER-BioMed Process/Event Entity Recognition Diagnostic

Date: 2026-09-18
Branch: `extraction_system_v2`
Scope: NER-only diagnostic. No Luna, OpenAI, relation extraction, prompt, threshold, model, or production-schema changes were made.

Test text:

> We observed that inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy in SSC-4 cells. Moreover, we observed that this has decreased migration and has blocked the expression of VEGF.

The standalone `biomedical-ner` command was used with the current GLiNER-BioMed checkpoint `Ihor/gliner-biomed-base-v1.0`, automatic device selection, and the configured threshold `0.5` for every pass.

## BASELINE

Command:

```powershell
uv --cache-dir C:/Projects/Biomed/.uv-cache run biomedical-ner --text "We observed that inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy in SSC-4 cells. Moreover, we observed that this has decreased migration and has blocked the expression of VEGF."
```

Labels: current default schema, without `--entity-label` overrides:

`gene`, `disease`, `chemical`, `species`, `cell line`, `DNA`, `RNA`

Threshold: `0.5`
Exit code: `0`
Wall-clock time: `18.028 s`

Entities returned:

```json
[
  {
    "id": "E1",
    "text": "p53",
    "type": "gene",
    "start": 46,
    "end": 49,
    "score": 0.9987726807594299
  },
  {
    "id": "E2",
    "text": "SSC-4 cells",
    "type": "cell line",
    "start": 121,
    "end": 132,
    "score": 0.9938382506370544
  },
  {
    "id": "E3",
    "text": "VEGF",
    "type": "chemical",
    "start": 224,
    "end": 228,
    "score": 0.8644157648086548
  }
]
```

## EXPANDED LABEL TEST

The baseline labels were retained and these labels were added: `protein`, `biological process`, and `perturbation`.

Command:

```powershell
uv --cache-dir C:/Projects/Biomed/.uv-cache run biomedical-ner --text "We observed that inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy in SSC-4 cells. Moreover, we observed that this has decreased migration and has blocked the expression of VEGF." --entity-label gene --entity-label disease --entity-label chemical --entity-label species --entity-label "cell line" --entity-label DNA --entity-label RNA --entity-label protein --entity-label "biological process" --entity-label perturbation
```

Threshold: `0.5`
Exit code: `0`
Wall-clock time: `7.348 s`

Entities returned:

```json
[
  {
    "id": "E1",
    "text": "p53",
    "type": "gene",
    "start": 46,
    "end": 49,
    "score": 0.9970773458480835
  },
  {
    "id": "E2",
    "text": "apoptosis",
    "type": "biological process",
    "start": 98,
    "end": 107,
    "score": 0.9764110445976257
  },
  {
    "id": "E3",
    "text": "autophagy",
    "type": "biological process",
    "start": 108,
    "end": 117,
    "score": 0.9555224180221558
  },
  {
    "id": "E4",
    "text": "SSC-4 cells",
    "type": "cell line",
    "start": 121,
    "end": 132,
    "score": 0.9954051971435547
  },
  {
    "id": "E5",
    "text": "migration",
    "type": "biological process",
    "start": 180,
    "end": 189,
    "score": 0.8779618740081787
  },
  {
    "id": "E6",
    "text": "VEGF",
    "type": "protein",
    "start": 224,
    "end": 228,
    "score": 0.9730226398086548
  }
]
```

## TARGET CHECK

Only exact returned spans are counted as detections. Near-matches and inferred event arguments are not counted.

### proliferation / proliferation ability

- Baseline: no.
- Expanded: no.
- Diagnostic: yes — `proliferation ability`, `biological process`, `[64, 85)`, score `0.6815402507781982`.

### apoptosis

- Baseline: no.
- Expanded: yes — `apoptosis`, `biological process`, `[98, 107)`, score `0.9764110445976257`.
- Diagnostic: yes — `apoptosis`, `biological process`, `[98, 107)`, score `0.9535817503929138`.

### autophagy

- Baseline: no.
- Expanded: yes — `autophagy`, `biological process`, `[108, 117)`, score `0.9555224180221558`.
- Diagnostic: yes — `autophagy`, `biological process`, `[108, 117)`, score `0.9004080295562744`.

### migration

- Baseline: no.
- Expanded: yes — `migration`, `biological process`, `[180, 189)`, score `0.8779618740081787`.
- Diagnostic: yes — `migration`, `biological process`, `[180, 189)`, score `0.9015381932258606`.

### inhibiting the expression of p53

- Baseline: no.
- Expanded: no.
- Diagnostic: no. The `perturbation`-only pass returned no entity for this phrase.

### p53

- Baseline: yes — `p53`, `gene`, `[46, 49)`, score `0.9987726807594299`.
- Expanded: yes — `p53`, `gene`, `[46, 49)`, score `0.9970773458480835`.
- Diagnostic: no; `gene` was not among the restricted labels.

### VEGF

- Baseline: yes — `VEGF`, `chemical`, `[224, 228)`, score `0.8644157648086548`.
- Expanded: yes — `VEGF`, `protein`, `[224, 228)`, score `0.9730226398086548`.
- Diagnostic: no; `protein` and `chemical` were not among the restricted labels.

### SSC-4 cells

- Baseline: yes — `SSC-4 cells`, `cell line`, `[121, 132)`, score `0.9938382506370544`.
- Expanded: yes — `SSC-4 cells`, `cell line`, `[121, 132)`, score `0.9954051971435547`.
- Diagnostic: no; `cell line` was not among the restricted labels.

## DIAGNOSTIC PASS

This pass was required because the expanded combined schema missed `proliferation ability` and returned no `perturbation` entity.

Command labels: only `biological process`, `perturbation`
Threshold: `0.5`
Exit code: `0`
Wall-clock time: `7.310 s`

Entities returned:

```json
[
  {
    "id": "E1",
    "text": "proliferation ability",
    "type": "biological process",
    "start": 64,
    "end": 85,
    "score": 0.6815402507781982
  },
  {
    "id": "E2",
    "text": "apoptosis",
    "type": "biological process",
    "start": 98,
    "end": 107,
    "score": 0.9535817503929138
  },
  {
    "id": "E3",
    "text": "autophagy",
    "type": "biological process",
    "start": 108,
    "end": 117,
    "score": 0.9004080295562744
  },
  {
    "id": "E4",
    "text": "migration",
    "type": "biological process",
    "start": 180,
    "end": 189,
    "score": 0.9015381932258606
  }
]
```

The restricted labels recovered `proliferation ability`, indicating that label competition in the expanded schema may suppress that process span. The restricted pass still returned no `perturbation` span, so it does not show label competition as the explanation for the perturbation miss.

## CONCLUSION

- Biological-process nodes: conditionally usable on this example. The combined schema detected `apoptosis`, `autophagy`, and `migration`, but missed `proliferation ability`; the process-only pass recovered it at `0.6815402507781982`. This is not reliable combined-schema coverage.
- Perturbation/event nodes: not usable on this example. The `perturbation` label returned no entity, including in the restricted pass, and no entity was returned for `inhibiting the expression of p53`.
- Label conflict: yes. `VEGF` was returned as `chemical` under the baseline schema and `protein` under the expanded schema; it was not returned as `gene`. This is an obvious label-competition/type-instability issue.

The machine-readable technical record is [gliner_process_event_ner_diagnostic_2026-09-18.json](<C:/Projects/Biomed/extraction_system/reports/gliner_process_event_ner_diagnostic_2026-09-18.json>). No architectural or production changes were made.

## MACHINE-READABLE TECHNICAL DETAILS

```json
{
  "report_type": "gliner_process_event_ner_diagnostic",
  "report_date": "2026-09-18",
  "branch": "extraction_system_v2",
  "test_text": "We observed that inhibiting the expression of p53 decreased the proliferation ability and induced apoptosis/autophagy in SSC-4 cells. Moreover, we observed that this has decreased migration and has blocked the expression of VEGF.",
  "scope": {
    "ner_only": true,
    "luna_called": false,
    "openai_called": false,
    "relation_extraction_called": false,
    "manual_entities_supplied": false,
    "default_schema_changed": false,
    "threshold_changed": false,
    "production_code_changed": false
  },
  "extractor": {
    "command": "biomedical-ner",
    "model": "Ihor/gliner-biomed-base-v1.0",
    "device": "auto",
    "threshold": 0.5,
    "default_labels": [
      "gene",
      "disease",
      "chemical",
      "species",
      "cell line",
      "DNA",
      "RNA"
    ]
  },
  "runs": {
    "baseline": {
      "labels": [
        "gene",
        "disease",
        "chemical",
        "species",
        "cell line",
        "DNA",
        "RNA"
      ],
      "exit_code": 0,
      "wall_clock_seconds": 18.028,
      "entities": [
        {"id": "E1", "text": "p53", "type": "gene", "start": 46, "end": 49, "score": 0.9987726807594299},
        {"id": "E2", "text": "SSC-4 cells", "type": "cell line", "start": 121, "end": 132, "score": 0.9938382506370544},
        {"id": "E3", "text": "VEGF", "type": "chemical", "start": 224, "end": 228, "score": 0.8644157648086548}
      ]
    },
    "expanded": {
      "labels": [
        "gene",
        "disease",
        "chemical",
        "species",
        "cell line",
        "DNA",
        "RNA",
        "protein",
        "biological process",
        "perturbation"
      ],
      "exit_code": 0,
      "wall_clock_seconds": 7.348,
      "entities": [
        {"id": "E1", "text": "p53", "type": "gene", "start": 46, "end": 49, "score": 0.9970773458480835},
        {"id": "E2", "text": "apoptosis", "type": "biological process", "start": 98, "end": 107, "score": 0.9764110445976257},
        {"id": "E3", "text": "autophagy", "type": "biological process", "start": 108, "end": 117, "score": 0.9555224180221558},
        {"id": "E4", "text": "SSC-4 cells", "type": "cell line", "start": 121, "end": 132, "score": 0.9954051971435547},
        {"id": "E5", "text": "migration", "type": "biological process", "start": 180, "end": 189, "score": 0.8779618740081787},
        {"id": "E6", "text": "VEGF", "type": "protein", "start": 224, "end": 228, "score": 0.9730226398086548}
      ]
    },
    "diagnostic_process_perturbation_only": {
      "labels": ["biological process", "perturbation"],
      "exit_code": 0,
      "wall_clock_seconds": 7.31,
      "entities": [
        {"id": "E1", "text": "proliferation ability", "type": "biological process", "start": 64, "end": 85, "score": 0.6815402507781982},
        {"id": "E2", "text": "apoptosis", "type": "biological process", "start": 98, "end": 107, "score": 0.9535817503929138},
        {"id": "E3", "text": "autophagy", "type": "biological process", "start": 108, "end": 117, "score": 0.9004080295562744},
        {"id": "E4", "text": "migration", "type": "biological process", "start": 180, "end": 189, "score": 0.9015381932258606}
      ]
    }
  },
  "target_checks": {
    "proliferation / proliferation ability": {
      "baseline": {"detected": false, "span_text": null, "type": null, "start": null, "end": null, "score": null},
      "expanded": {"detected": false, "span_text": null, "type": null, "start": null, "end": null, "score": null},
      "diagnostic_process_perturbation_only": {"detected": true, "span_text": "proliferation ability", "type": "biological process", "start": 64, "end": 85, "score": 0.6815402507781982}
    },
    "apoptosis": {
      "baseline": {"detected": false, "span_text": null, "type": null, "start": null, "end": null, "score": null},
      "expanded": {"detected": true, "span_text": "apoptosis", "type": "biological process", "start": 98, "end": 107, "score": 0.9764110445976257},
      "diagnostic_process_perturbation_only": {"detected": true, "span_text": "apoptosis", "type": "biological process", "start": 98, "end": 107, "score": 0.9535817503929138}
    },
    "autophagy": {
      "baseline": {"detected": false, "span_text": null, "type": null, "start": null, "end": null, "score": null},
      "expanded": {"detected": true, "span_text": "autophagy", "type": "biological process", "start": 108, "end": 117, "score": 0.9555224180221558},
      "diagnostic_process_perturbation_only": {"detected": true, "span_text": "autophagy", "type": "biological process", "start": 108, "end": 117, "score": 0.9004080295562744}
    },
    "migration": {
      "baseline": {"detected": false, "span_text": null, "type": null, "start": null, "end": null, "score": null},
      "expanded": {"detected": true, "span_text": "migration", "type": "biological process", "start": 180, "end": 189, "score": 0.8779618740081787},
      "diagnostic_process_perturbation_only": {"detected": true, "span_text": "migration", "type": "biological process", "start": 180, "end": 189, "score": 0.9015381932258606}
    },
    "inhibiting the expression of p53": {
      "baseline": {"detected": false, "span_text": null, "type": null, "start": null, "end": null, "score": null},
      "expanded": {"detected": false, "span_text": null, "type": null, "start": null, "end": null, "score": null},
      "diagnostic_process_perturbation_only": {"detected": false, "span_text": null, "type": null, "start": null, "end": null, "score": null}
    },
    "p53": {
      "baseline": {"detected": true, "span_text": "p53", "type": "gene", "start": 46, "end": 49, "score": 0.9987726807594299},
      "expanded": {"detected": true, "span_text": "p53", "type": "gene", "start": 46, "end": 49, "score": 0.9970773458480835},
      "diagnostic_process_perturbation_only": {"detected": false, "span_text": null, "type": null, "start": null, "end": null, "score": null}
    },
    "VEGF": {
      "baseline": {"detected": true, "span_text": "VEGF", "type": "chemical", "start": 224, "end": 228, "score": 0.8644157648086548},
      "expanded": {"detected": true, "span_text": "VEGF", "type": "protein", "start": 224, "end": 228, "score": 0.9730226398086548},
      "diagnostic_process_perturbation_only": {"detected": false, "span_text": null, "type": null, "start": null, "end": null, "score": null}
    },
    "SSC-4 cells": {
      "baseline": {"detected": true, "span_text": "SSC-4 cells", "type": "cell line", "start": 121, "end": 132, "score": 0.9938382506370544},
      "expanded": {"detected": true, "span_text": "SSC-4 cells", "type": "cell line", "start": 121, "end": 132, "score": 0.9954051971435547},
      "diagnostic_process_perturbation_only": {"detected": false, "span_text": null, "type": null, "start": null, "end": null, "score": null}
    }
  },
  "diagnostic_interpretation": {
    "required": true,
    "process_label_competition_supported": true,
    "perturbation_label_competition_supported": false,
    "reason": "The combined schema missed proliferation ability but the process-only pass recovered it; the perturbation-only label returned no entity."
  },
  "validation": {
    "all_returned_spans_within_input": true,
    "all_outputs_normalized_by_existing_adapter": true,
    "manual_entities_created": false,
    "threshold_modified": false,
    "paid_api_calls": 0,
    "runtime_warnings": [
      "torch.jit.script is deprecated",
      "GLiNER tokenizer reported no predefined maximum length and defaulted to no truncation"
    ]
  },
  "conclusion": {
    "biological_process_nodes": "Conditionally usable on this example, but not reliably covered by the combined schema: apoptosis, autophagy, and migration were detected while proliferation ability required the restricted process-label pass.",
    "perturbation_event_nodes": "Not usable on this example: the perturbation label returned no entity in either the combined or restricted pass.",
    "label_conflict": "VEGF was chemical under the baseline schema and protein under the expanded schema; it was not returned as gene."
  }
}
```
