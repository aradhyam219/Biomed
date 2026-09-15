# V0-B Self-Concept Relation Diagnostic

Date: 2026-09-15  
Status: read-only diagnostic complete  
Baseline: [BioRED V0-B complete-fit machine-readable report](biored_v0b_complete_fit.json)

## Executive finding

The exact local official BioRED development corpus contains **one** normalized
self-concept gold relation. The hypothesis that BioRED development truth contains
no self-concept relations is therefore false for the authoritative project data.

Talia's finding about the cited V0-B false positive remains correct: PMID `24288432`
contains no gold relation from concept `2264` to itself, while the cached V0-B
candidate predicts `2264 -> Association -> 2264` with score
`0.6384876370429993`.

Because the requested metric-impact analysis was conditional on the gold
self-relation count being zero, filtered metrics are not an authorized conclusion
of this diagnostic. No candidate filter or evaluation behavior was changed.

## Scope and integrity

This diagnostic used only the official local development JSON and the existing
cached concept-level V0-B scores. It did not load or run GLiREL, modify the cache,
change production/evaluation code, recalibrate an adopted operating point, start
V1, or alter any candidate constraint.

Authoritative inputs:

| Input | Local path | SHA-256 |
|---|---|---|
| Official BioRED development corpus | `.cache/BIORED/BioRED/Dev.BioC.JSON` | `d5ab4d05673ac46fb5e3b2904d2820462dec2c4c50dfcdd8678635ff1b8ce1f5` |
| Existing V0-B raw score cache | `.cache/v0b_raw.json` | `795b96cce23197db8ed9237ebdd7678b34761a14633202eaf2b7653dc4e4a4f6` |

The corpus contains 100 documents and 1,162 canonical typed gold relations. The
cache contains exactly the authorized 99 complete-fit document IDs, 7,992 cached
concept-label scores, and no entry for excluded PMID `19880293`.

## Method

1. Load the exact `Dev.BioC.JSON` through the project BioRED parser.
2. Scan all canonical gold relations for `concept_a == concept_b`.
3. Repeat the gold count after removing only the authorized sequence-length
   exclusion, PMID `19880293`.
4. Deserialize cached concept-label scores for the exact 99-document set and reject
   any cache/document-ID mismatch.
5. Count cached self-concept concept-label candidates.
6. Apply the existing one-label-per-concept-pair selection, then the unchanged V0-B
   threshold `0.14250895380973816`.
7. Count surviving self-concept predictions by canonical relation label.

Sequence length, gold truth, and cached predictions remained separate inputs. No
prediction outcome was consulted when defining the authorized 99-document set.

## 1. Gold self-concept relations

| Evaluation scope | Gold self-concept relations |
|---|---:|
| All 100 official development documents | **1** |
| Authorized 99-document complete-fit set | **1** |

The single relation is:

| PMID | BioC relation ID | Concept A | Relation | Concept B |
|---|---|---|---|---|
| `24036311` | `R18` | `22083` | `Bind` | `22083` |

This record was confirmed directly in the raw BioC relation fields: both
`infons.entity1` and `infons.entity2` are `22083`, and `infons.type` is `Bind`.
It belongs to the evaluated 99-document set.

## 2. Predicted self-concept candidates

There are two useful pre-threshold counts because the cache stores a score per
concept pair and label, while final V0-B prediction selection retains one label per
concept pair:

| Stage | Self-concept count |
|---|---:|
| Cached concept-label scores | **436** |
| Unique self-concept pairs after one-label-per-pair selection | **393** |
| Predictions surviving threshold `0.14250895380973816` | **140** |

Surviving predictions by relation label:

| Relation label | Count |
|---|---:|
| Association | **119** |
| Positive_Correlation | **2** |
| Negative_Correlation | **5** |
| Bind | **2** |
| Conversion | **0** |
| Drug_Interaction | **4** |
| Comparison | **6** |
| Cotreatment | **2** |
| **Total** | **140** |

### Confirmed cited false positive

| Field | Value |
|---|---|
| PMID | `24288432` |
| Concept pair | `2264 -> 2264` |
| Predicted label | `Association` |
| Cached score | `0.6384876370429993` |
| Survives current threshold | Yes |
| Matching BioRED gold relation | None |

The full 100-document gold scan found no self-concept relation for concept `2264`
in PMID `24288432`; the only gold self-concept relation is the distinct `Bind`
record in PMID `24036311` above.

## 3. Metric-impact condition

The requested metric comparison was explicitly conditional:

> Recompute filtered metrics if and only if gold self-relations equal zero.

The observed gold count is one, so that condition is false. Consequently, this
report does not present an old-versus-filtered score or recommend adopting a blanket
`concept_a != concept_b` filter. Such a filter would change the candidate space in a
way that can remove a legitimate official-development gold relation.

The current V0-B threshold and published complete-fit baseline therefore remain
unchanged by this diagnostic.

## Conclusion

- Keep PMID `24288432`, concept `2264 -> 2264`, labeled as a genuine V0-B false
  positive.
- Do not generalize that example into a claim that BioRED has no normalized
  self-concept gold relations.
- Do not add a blanket self-pair exclusion without a separate methodological
  decision that explicitly addresses the gold `22083 -> Bind -> 22083` relation.
- No V1 work, fine-tuning, model inference, cache mutation, or evaluator change is
  justified by this diagnostic alone.
