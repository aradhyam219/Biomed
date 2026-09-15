# BioRED Relation Evaluation

This document is the authoritative methodology for the V0-B relation-extraction
baseline. The experiment asks how the current zero-shot GLiREL checkpoint performs
when entity recognition is removed as a source of error.

## Source and split

Use the official NCBI BioRED archive and its original `Dev.BioC.JSON` file. The
evaluator requires an explicit file or containing-directory path, records the file's
SHA-256 digest, and rejects train/test split names. It does not use the later
BioRED-BC8 400-document test extension.

Primary sources:

- [NCBI BioRED repository](https://github.com/ncbi/BioRED) — official archive,
  formats, and original train/development/test split.
- [Original BioRED paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC9487702/) —
  corpus design and document-level relation task.
- [BioCreative VIII corpus description](https://academic.oup.com/database/article/doi/10.1093/database/baae071/7731176)
  — entity normalization, relation pair families, and semantic labels.
- [GLiREL repository](https://github.com/jackboyla/GLiREL) and
  [paper](https://aclanthology.org/2025.naacl-long.418/) — supplied token-span
  entities, zero-shot relation prompts, scores, and `top_k` behavior.

The corpus stays in a local gitignored location; it is not committed.

## Gold-entity isolation and BioC parsing

`Dev.BioC.JSON` stores a title and abstract as document-relative passages. The loader
sorts passages by `offset`, fills the corpus-defined gap between them with a space,
and validates that every annotation's half-open character bounds
`[offset, offset + length)` select its exact mention text. It preserves the original
mention ID, text, BioRED type, and every normalized concept identifier.

BioC entity types are deterministically mapped for GLiREL and candidate filtering:

| BioC type | Evaluation type |
|---|---|
| `DiseaseOrPhenotypicFeature` | `Disease` |
| `GeneOrGeneProduct` | `Gene` |
| `ChemicalEntity` | `Chemical` |
| `SequenceVariant` | `Variant` |
| `OrganismTaxon` | `Species` |
| `CellLine` | `CellLine` |

Only Disease, Gene, Chemical, and Variant mentions are supplied to the primary
relation experiment. Species and cell-line mentions remain in parsed data but cannot
create V0-B candidates. GLiNER is neither loaded nor called.

Some exact BioRED mentions end inside GLiREL's usual compound token—for example,
`H3` within `H3K36me3`. The supplied-entity production path splits tokens at exact
entity character boundaries before producing GLiREL's inclusive token bounds. It
does not widen, remap, or discard a gold annotation. GLiREL output endpoint bounds
are half-open and resolve back to the same supplied mention IDs.

## Relation schema and candidate space

The canonical schema is exactly:

```text
Association
Positive_Correlation
Negative_Correlation
Bind
Conversion
Drug_Interaction
Comparison
Cotreatment
```

GLiREL receives deterministic human-readable prompts (`positive correlation`,
`drug interaction`, and so on), and every prediction is mapped back through the
explicit table in `biomedical_extractor.biored`. No synonym rewriting occurs.

The evaluator accepts only these unordered type families:

```text
Disease-Gene        Chemical-Gene
Disease-Variant     Gene-Gene
Chemical-Disease    Chemical-Chemical
Chemical-Variant    Variant-Variant
```

GLiREL's allowed-head/allowed-tail primitive cannot express this complete symmetric
union in one document pass, so the evaluator removes predictions outside these
families deterministically after inference. `top_k=1` is applied by GLiREL to each
directed mention pair.

No stricter relation-label/type matrix is applied. Although published examples place
`Bind` with gene-gene/chemical-gene and several specialized labels with
chemical-chemical pairs, the official development corpus itself includes one
chemical-chemical `Bind` and two chemical-gene `Cotreatment` gold relations. Corpus
truth therefore prevents those examples from being treated as universal filters.

## Mention-to-concept aggregation

BioRED truth is a non-directional normalized concept relation at document level,
whereas GLiREL predicts directed mention pairs. Evaluation converts units as follows:

1. Resolve both predicted endpoints to supplied gold mention IDs.
2. Read each mention's normalized concept IDs without consulting gold relations.
3. Split the official comma-delimited multi-ID field, preserve every unique ID, and
   expand the endpoint sets by Cartesian product.
4. Sort each concept pair so opposite GLiREL directions represent the same candidate.
5. For each `(document, concept pair, relation label)`, retain the maximum score over
   all mentions, expansions, duplicate predictions, and directions.
6. For each `(document, concept pair)`, retain only its highest-scoring label; the
   canonical BioRED label order breaks exact score ties.

This maximum-evidence rule prevents repeated mentions of one concept from creating
duplicate document-level relations. It also handles a same-concept pair
deterministically as `(concept, concept)`.

## Complete-fit development set and coverage

V0-B is a **BioRED development complete-fit baseline**, not a full or official
BioRED development score. The current `jackboyla/glirel-large-v0` checkpoint accepts
at most 512 supplied-entity tokens. Exact preflight identifies one official
development document above that limit: PMID `19880293` has 554 tokens.

The authorized evaluation set therefore contains the other 99 documents. PMID
`19880293` remains unevaluated: it is not truncated, windowed, chunked, inferred, or
counted as a false negative. The exclusion is decided solely by pre-inference
sequence length and independently of prediction outcome. The report always includes
document coverage, total official-development gold relations, evaluated-document
gold relations, gold-relation coverage, and the excluded document's gold count.

This exception is specific to V0-B and this checkpoint. Any other over-limit PMID
fails closed rather than being silently excluded.

## Threshold calibration and metrics

Inference runs once per development document at relation threshold `0.0` and saves
the resulting concept-label scores incrementally. A smoke run, subset run, and full
run can share one cache: already present document IDs are not inferred again.

The scorer evaluates all distinct concept-level score boundaries over the authorized
99-document complete-fit set and chooses the threshold with maximum typed micro F1.
An exact F1 tie prefers higher precision, then the higher threshold. Predictions use
the inclusive decision `score >= threshold`. This is a development-calibrated
operating point, not an unbiased test estimate.

Pair-only TP/FP/FN compare exact sets of `(document, unordered concept pair)` and
ignore label. Typed TP/FP/FN compare `(document, unordered concept pair, canonical
relation label)`. Precision is `TP / (TP + FP)`, recall is `TP / (TP + FN)`, and F1
is their harmonic mean. Undefined metrics are serialized as JSON `null` and printed
as `N/A`. Novelty is intentionally absent. Per-label metrics use the same typed unit.

The summary also records pre/post-threshold counts, selected operating points, and a
small set of high-confidence true positives, false positives, and false negatives.

## Current V0-B result

The completed zero-shot run used the dataset and protocol above. The ignored raw
cache contains predictions for exactly the 99 evaluated documents; PMID `19880293`
is absent. Seventy-four valid cached predictions were reused and only the remaining
25 complete-fit documents were inferred.

```text
BioRED development complete-fit baseline
Evaluated: 99 / 100 documents
Excluded: PMID 19880293
Exclusion reason: exceeds current GLiREL checkpoint input limit
Document coverage: 99.00%
Total official-dev gold relations: 1162
Gold relations in evaluated documents: 1156
Gold-relation coverage: 99.48%
Gold relations in excluded document: 6
```

The threshold calibrated once over those 99 documents is `0.14250895`. At that
threshold, pair-only micro precision/recall/F1 are `0.2212 / 0.4775 / 0.3023`
(`TP=552`, `FP=1944`, `FN=604`), and typed micro precision/recall/F1 are
`0.1322 / 0.2855 / 0.1807` (`TP=330`, `FP=2166`, `FN=826`). This is a
development-calibrated complete-fit baseline and must not be cited as a full or
official BioRED development score.

## Sequence integrity and limitations

The checkpoint and GLiREL preprocessing enforce `max_len=512`. Length is measured
after the exact gold-boundary token splits used for supplied entities. GLiREL 1.2.1
would silently truncate PMID `19880293`; the evaluator instead removes it before
model loading under the complete-fit policy above. Chunking and cross-chunk
aggregation remain outside V0-B's authorized scope.

Other limitations:

- threshold selection and quality reporting use the same development split;
- zero-shot prompt behavior is checkpoint-specific;
- the 99/100 complete-fit result may contain selection bias and must never be
  described as a full or official BioRED development score;
- concept IDs are supplied by BioRED only for scoring isolation and are not a new
  production entity-linking feature;
- no GLiNER evaluation, end-to-end BioRED run, novelty prediction, training,
  fine-tuning, or hyperparameter sweep is performed.

## Commands and generated outputs

From the `extraction_system` root:

```powershell
# One-document real-model smoke test
uv run biored-evaluate --dataset C:\path\to\BioRED --limit 1

# Full original development split, reusing the same incremental cache
uv run biored-evaluate --dataset C:\path\to\BioRED
```

Use `--cache` and `--output` to choose alternate generated JSON paths. By default,
both are under `.cache/`. The command has no model-selection option: V0-B is fixed to
`jackboyla/glirel-large-v0` / `DEFAULT_RELATION_MODEL`. The summary contains dataset
identity, checkpoint, schema, top-k policy, coverage and exclusion counts, threshold,
pair-only and typed metrics, per-label metrics, sequence diagnostics, and
representative errors.
