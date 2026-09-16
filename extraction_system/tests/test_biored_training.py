from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from biomedical_extractor.biored import (
    CANONICAL_TO_PROMPT,
    BioREDDocument,
    BioREDMention,
    BioREDDataset,
    TypedRelation,
    load_biored,
)
from biomedical_extractor.biored_training import (
    GLIREL_RELATION_LABELS,
    V1TrainingConfig,
    build_training_plan,
    calculate_scheduler_steps,
    convert_document_to_glirel,
    _expected_relation_pair_count,
    _native_loader,
    _select_smoke_example,
    prepare_training_corpus,
    verify_biored_dev_hash,
    verify_generated_positive_origins,
)


def _dataset(documents: tuple[BioREDDocument, ...], split: str = "train") -> BioREDDataset:
    return BioREDDataset(
        path=Path(f"{split}.BioC.JSON"),
        split=split,
        sha256="test-sha",
        source="BioC",
        date="2021-11-30",
        key="BioC.key",
        documents=documents,
    )


class BioREDTrainingTests(unittest.TestCase):
    def test_converter_expands_concept_mentions_in_both_directions(self):
        document = BioREDDocument(
            id="PM1",
            text="G D G D",
            mentions=(
                BioREDMention("G1", "G", "Gene", 0, 1, ("G",)),
                BioREDMention("D1", "D", "Disease", 2, 3, ("D",)),
                BioREDMention("G2", "G", "Gene", 4, 5, ("G",)),
                BioREDMention("D2", "D", "Disease", 6, 7, ("D",)),
            ),
            relations=(TypedRelation("PM1", "D", "G", "Association"),),
        )

        converted = convert_document_to_glirel(document)
        relations = converted.example["relations"]

        self.assertEqual(converted.token_count, 4)
        self.assertEqual(len(relations), 8)
        self.assertEqual(
            {relation["relation_text"] for relation in relations}, {"association"}
        )
        self.assertEqual(
            {relation["canonical_relation_type"] for relation in relations},
            {"Association"},
        )
        self.assertEqual(converted.example["label"], list(GLIREL_RELATION_LABELS))
        self.assertEqual(
            {
                (
                    tuple(relation["head"]["position"]),
                    tuple(relation["tail"]["position"]),
                )
                for relation in relations
            },
            {
                ((0, 0), (1, 1)),
                ((0, 0), (3, 3)),
                ((2, 2), (1, 1)),
                ((2, 2), (3, 3)),
                ((1, 1), (0, 0)),
                ((3, 3), (0, 0)),
                ((1, 1), (2, 2)),
                ((3, 3), (2, 2)),
            },
        )
        self.assertFalse(converted.diagnostics["unresolved_gold_relations"])
        self.assertFalse(converted.diagnostics["unrepresentable_mention_pairs"])
        self.assertEqual(
            verify_generated_positive_origins(relations and (converted.example,), _dataset((document,)))["invalid"],
            0,
        )

    def test_train_and_inference_use_the_same_prompt_labels(self):
        from biomedical_extractor.biored_cli import _extractor

        class CapturingModel:
            def create_dataloader(self, examples, **kwargs):
                self.train_relation_types = kwargs["train_relation_types"]
                return object()

        model = CapturingModel()
        _native_loader(model, (), V1TrainingConfig())

        self.assertEqual(GLIREL_RELATION_LABELS, tuple(CANONICAL_TO_PROMPT.values()))
        self.assertEqual(model.train_relation_types, list(GLIREL_RELATION_LABELS))
        self.assertEqual(
            _extractor(object(), None).config.relation_labels,
            GLIREL_RELATION_LABELS,
        )

    def test_smoke_example_selection_is_pair_and_token_deterministic(self):
        def example(document_id, token_count, entity_count):
            return {
                "metadata": {"document_id": document_id},
                "tokenized_text": ["x"] * token_count,
                "ner": [[index, index, "Gene", "x"] for index in range(entity_count)],
                "relations": [],
            }

        high_pair_count = example("high-pairs", 10, 5)
        longer_tie = example("longer-tie", 110, 4)
        shorter_tie = example("shorter-tie", 100, 4)

        self.assertEqual(_expected_relation_pair_count(high_pair_count), 20)
        self.assertIs(
            _select_smoke_example((shorter_tie, high_pair_count, longer_tie)),
            high_pair_count,
        )
        self.assertIs(_select_smoke_example((shorter_tie, longer_tie)), longer_tie)

    def test_scheduler_steps_use_optimizer_update_count(self):
        self.assertEqual(calculate_scheduler_steps(4_000, 8, 0.1), (500, 50))
        self.assertEqual(calculate_scheduler_steps(4_001, 8, 0.1), (501, 50))

    def test_prepare_excludes_over_limit_documents_without_truncation(self):
        short = BioREDDocument(
            id="short",
            text="G D",
            mentions=(
                BioREDMention("G", "G", "Gene", 0, 1, ("G",)),
                BioREDMention("D", "D", "Disease", 2, 3, ("D",)),
            ),
            relations=(TypedRelation("short", "G", "D", "Association"),),
        )
        long_text = "G " + ("x " * 511) + "D"
        long = BioREDDocument(
            id="long",
            text=long_text,
            mentions=(
                BioREDMention("G", "G", "Gene", 0, 1, ("G",)),
                BioREDMention("D", "D", "Disease", len(long_text) - 1, len(long_text), ("D",)),
            ),
            relations=(
                TypedRelation("long", "G", "D", "Association"),
                TypedRelation("long", "G", "D2", "Bind"),
            ),
        )
        prepared = prepare_training_corpus(_dataset((short, long)))

        self.assertEqual(prepared.stats["documents"]["included"], 1)
        self.assertEqual(prepared.stats["documents"]["excluded"], 1)
        self.assertEqual(prepared.stats["gold_relations"]["included"], 1)
        self.assertEqual(prepared.stats["gold_relations"]["excluded"], 2)
        self.assertEqual(prepared.stats["token_lengths"]["documents_over_max_len"][0]["tokens"], 513)
        self.assertEqual(prepared.stats["generated_positive_relations"]["total"], 2)
        self.assertEqual(len(prepared.examples), 1)

    def test_native_collator_assigns_zero_to_unlabeled_pairs(self):
        from glirel.modules.base import InstructBase

        config = SimpleNamespace(
            max_width=12,
            max_entity_pair_distance=None,
            span_marker_mode="markerv1",
            fixed_relation_types=True,
            max_len=512,
            num_train_rel_types=8,
            random_drop=False,
            shuffle_types=False,
            coreference_label=None,
        )
        native = InstructBase(config)
        example = {
            "tokenized_text": ["G", "D"],
            "ner": [[0, 0, "Gene", "G"], [1, 1, "Disease", "D"]],
            "relations": [],
            "label": list(GLIREL_RELATION_LABELS),
        }

        batch = native.collate_fn(
            [example],
            train_relation_types=list(GLIREL_RELATION_LABELS),
            device="cpu",
        )

        self.assertEqual(batch["rel_label"].tolist(), [[0, 0]])

    def test_train_dev_test_loader_keeps_split_identity(self):
        root = {
            "source": "BioC",
            "date": "2021-11-30",
            "key": "BioC.key",
            "documents": [
                {
                    "id": "PM1",
                    "passages": [
                        {
                            "offset": 0,
                            "text": "G",
                            "annotations": [],
                        }
                    ],
                    "relations": [],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "BioRED"
            base.mkdir()
            for filename in ("Train.BioC.JSON", "Dev.BioC.JSON", "Test.BioC.JSON"):
                (base / filename).write_text(json.dumps(root), encoding="utf-8")
            self.assertEqual(load_biored(base.parent, "train").split, "train")
            self.assertEqual(load_biored(base.parent, "dev").split, "dev")
            self.assertEqual(load_biored(base.parent, "test").split, "test")

    def test_dev_hash_guard_fails_closed_on_mismatch(self):
        root = {
            "source": "BioC",
            "date": "2021-11-30",
            "key": "BioC.key",
            "documents": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "BioRED"
            base.mkdir()
            (base / "Dev.BioC.JSON").write_text(json.dumps(root), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                verify_biored_dev_hash(base.parent, expected_sha256="not-the-hash")

    def test_training_plan_is_constructed_without_checkpoint_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            jsonl = Path(directory) / "train.jsonl"
            jsonl.write_text("{}\n", encoding="utf-8")
            plan = build_training_plan(jsonl, Path(directory) / "checkpoints")

        self.assertEqual(plan.config.checkpoint, "jackboyla/glirel-large-v0")
        self.assertEqual(plan.config.lr_encoder, 1e-5)
        self.assertEqual(plan.config.lr_others, 1e-4)
        self.assertEqual(plan.config.train_batch_size, 1)
        self.assertEqual(plan.config.gradient_accumulation, 8)
        self.assertEqual(plan.config.mixed_precision, "fp16")
        self.assertEqual(plan.config.num_steps, 4_000)
        self.assertEqual(plan.config.save_every, 1_000)
        self.assertEqual(plan.config.num_unseen_rel_types, 0)


if __name__ == "__main__":
    unittest.main()
