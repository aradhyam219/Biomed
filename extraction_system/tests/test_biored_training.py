from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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
    SMOKE_MAX_AMP_ATTEMPTS,
    TrainingPlan,
    V1TrainingConfig,
    _build_v1_optimizer,
    build_training_plan,
    calculate_scheduler_steps,
    convert_document_to_glirel,
    _expected_relation_pair_count,
    _native_loader,
    _optimizer_step_status,
    _select_smoke_example,
    _validate_unscaled_gradients,
    prepare_training_corpus,
    run_gpu_smoke_test,
    run_training,
    verify_biored_dev_hash,
    verify_generated_positive_origins,
    _write_json,
    write_prepared_corpus,
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

    def test_smoke_accepts_globally_finite_non_zero_unscaled_gradients(self):
        import torch

        model = torch.nn.Sequential(torch.nn.Linear(2, 2), torch.nn.Linear(2, 1))
        model(torch.ones(1, 2)).sum().backward()

        metrics = _validate_unscaled_gradients(model, torch)

        self.assertTrue(metrics["gradients_finite"])
        self.assertGreater(metrics["global_unscaled_gradient_norm"], 0.0)
        self.assertEqual(metrics["gradient_tensors"], 4)

    def test_smoke_surfaces_non_finite_gradients_as_amp_overflow(self):
        import torch

        model = torch.nn.Linear(2, 1)
        model.weight.grad = torch.tensor([[float("inf"), 0.0]])

        with self.assertRaisesRegex(RuntimeError, "AMP-overflow blocker"):
            _validate_unscaled_gradients(model, torch)

    def test_optimizer_state_distinguishes_skipped_and_executed_step(self):
        import torch

        parameter = torch.nn.Parameter(torch.tensor([1.0, 2.0]))
        optimizer = torch.optim.AdamW(
            [{"params": [parameter], "weight_decay": 0.0}], lr=0.1
        )

        skipped = _optimizer_step_status(optimizer, torch)
        self.assertFalse(skipped["optimizer_step_completed"])
        self.assertEqual(skipped["optimizer_parameters_at_step_1"], 0)

        parameter.grad = torch.tensor([1.0, 0.0])
        optimizer.step()
        executed = _optimizer_step_status(optimizer, torch)
        self.assertTrue(executed["optimizer_step_completed"])
        self.assertEqual(executed["optimizer_parameters_at_step_1"], 1)

    def test_unchanged_arbitrary_scalar_does_not_fail_optimizer_step_check(self):
        import torch

        parameter = torch.nn.Parameter(torch.tensor([1.0, 2.0]))
        optimizer = torch.optim.AdamW(
            [{"params": [parameter], "weight_decay": 0.0}], lr=0.1
        )
        parameter.grad = torch.tensor([1.0, 0.0])
        unchanged_before = parameter.detach()[1].clone()
        optimizer.step()

        self.assertEqual(parameter.detach()[1], unchanged_before)
        self.assertTrue(_optimizer_step_status(optimizer, torch)["optimizer_step_completed"])

    def test_smoke_reports_stage_timings_and_update_diagnostics(self):
        import torch

        class TinySmokeModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.weight = torch.nn.Parameter(torch.tensor([1.0, 0.0]))

            def forward(self, batch):
                del batch
                return {"total_loss": self.weight[0].square()}

        class CountingScaler:
            instance = None

            def __init__(self, enabled):
                del enabled
                self.unscale_calls = 0
                self.step_calls = 0
                self.update_calls = 0
                CountingScaler.instance = self

            def scale(self, loss):
                return loss

            def unscale_(self, optimizer):
                del optimizer
                self.unscale_calls += 1

            def step(self, optimizer):
                self.step_calls += 1
                return optimizer.step()

            def update(self):
                self.update_calls += 1

            def get_scale(self):
                return 1.0

        model = TinySmokeModel()
        batch = {
            "tokens": [["G", "D"]],
            "rel_label": torch.zeros((1, 2), dtype=torch.long),
        }
        example = {
            "metadata": {"document_id": "PM1"},
            "tokenized_text": ["G", "D"],
            "ner": [[0, 0, "Gene", "G"], [1, 1, "Disease", "D"]],
            "relations": [],
        }
        config = V1TrainingConfig(device="cpu", mixed_precision="none")

        def optimizer_builder(current_model, current_config):
            del current_config
            return torch.optim.AdamW(
                [{"params": [current_model.weight], "weight_decay": 0.0}], lr=0.1
            )

        with tempfile.TemporaryDirectory() as directory:
            plan = TrainingPlan(
                Path(directory) / "train.jsonl",
                Path(directory) / "checkpoints",
                config,
            )
            with patch(
                "biomedical_extractor.biored_training._load_glirel_model",
                return_value=model,
            ), patch(
                "biomedical_extractor.biored_training.load_training_examples",
                return_value=[example],
            ), patch(
                "biomedical_extractor.biored_training._native_loader",
                return_value=[batch],
            ), patch(
                "biomedical_extractor.biored_training._build_v1_optimizer",
                side_effect=optimizer_builder,
            ), patch.object(torch.cuda.amp, "GradScaler", CountingScaler):
                result = run_gpu_smoke_test(plan)

        self.assertTrue(result["gradients_finite"])
        self.assertGreater(result["global_unscaled_gradient_norm"], 0.0)
        self.assertTrue(result["optimizer_step_completed"])
        self.assertEqual(result["optimizer_parameters_at_step_1"], 1)
        self.assertEqual(result["scaler_scale_before"], 1.0)
        self.assertEqual(result["scaler_scale_after"], 1.0)
        self.assertEqual(CountingScaler.instance.unscale_calls, 1)
        self.assertEqual(CountingScaler.instance.step_calls, 1)
        self.assertEqual(CountingScaler.instance.update_calls, 1)
        self.assertTrue(
            {
                "model_load",
                "batch_materialization",
                "forward",
                "backward",
                "gradient_validation",
                "optimizer_scaler_step",
            }.issubset(result["stage_timings_seconds"])
        )

    def test_smoke_retries_overflow_and_records_scale_trajectory(self):
        import torch

        class TinySmokeModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.weight = torch.nn.Parameter(torch.tensor([1.0, 0.0]))

            def forward(self, batch):
                del batch
                return {"total_loss": self.weight[0].square()}

        class RecoveringScaler:
            instance = None

            def __init__(self, enabled):
                del enabled
                self.scale_value = 8.0
                self.unscale_calls = 0
                self.step_calls = 0
                RecoveringScaler.instance = self

            def is_enabled(self):
                return True

            def scale(self, loss):
                return loss * self.scale_value

            def unscale_(self, optimizer):
                self.unscale_calls += 1
                if self.unscale_calls == 1:
                    for group in optimizer.param_groups:
                        for parameter in group["params"]:
                            if parameter.grad is not None:
                                parameter.grad.fill_(float("inf"))

            def step(self, optimizer):
                self.step_calls += 1
                if self.step_calls > 1:
                    return optimizer.step()
                return None

            def update(self):
                if self.step_calls == 1:
                    self.scale_value /= 2

            def get_scale(self):
                return self.scale_value

        model = TinySmokeModel()
        batch = {
            "tokens": [["G", "D"]],
            "rel_label": torch.zeros((1, 2), dtype=torch.long),
        }
        example = {
            "metadata": {"document_id": "PM1"},
            "tokenized_text": ["G", "D"],
            "ner": [[0, 0, "Gene", "G"], [1, 1, "Disease", "D"]],
            "relations": [],
        }
        config = V1TrainingConfig(device="cpu", mixed_precision="none")

        with tempfile.TemporaryDirectory() as directory:
            plan = TrainingPlan(
                Path(directory) / "train.jsonl",
                Path(directory) / "checkpoints",
                config,
            )
            with patch(
                "biomedical_extractor.biored_training._load_glirel_model",
                return_value=model,
            ), patch(
                "biomedical_extractor.biored_training.load_training_examples",
                return_value=[example],
            ), patch(
                "biomedical_extractor.biored_training._native_loader",
                return_value=[batch],
            ), patch(
                "biomedical_extractor.biored_training._build_v1_optimizer",
                return_value=torch.optim.AdamW(
                    [{"params": [model.weight], "weight_decay": 0.0}], lr=0.1
                ),
            ), patch.object(torch.cuda.amp, "GradScaler", RecoveringScaler):
                result = run_gpu_smoke_test(plan)

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["attempt_count"], 2)
        self.assertEqual(result["amp_overflow_attempts"], 1)
        self.assertEqual(result["successful_scale"], 4.0)
        self.assertEqual(result["successful_global_unscaled_gradient_norm"] > 0, True)
        self.assertTrue(result["optimizer_step_completed"])
        self.assertEqual(result["optimizer_parameters_at_step_1"], 1)
        self.assertEqual(
            result["scaler_scale_trajectory"],
            [
                {"attempt": 1, "before": 8.0, "after": 4.0},
                {"attempt": 2, "before": 4.0, "after": 4.0},
            ],
        )
        self.assertEqual(result["attempts"][0]["status"], "AMP_OVERFLOW")
        self.assertTrue(result["attempts"][0]["optimizer_update_skipped"])
        self.assertEqual(result["attempts"][1]["status"], "PASS")

    def test_smoke_returns_structured_blocker_after_overflow_retry_bound(self):
        import torch

        class TinySmokeModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.weight = torch.nn.Parameter(torch.tensor([1.0, 0.0]))

            def forward(self, batch):
                del batch
                return {"total_loss": self.weight[0].square()}

        class AlwaysOverflowScaler:
            def __init__(self, enabled):
                del enabled
                self.scale_value = 8.0

            def scale(self, loss):
                return loss * self.scale_value

            def unscale_(self, optimizer):
                for group in optimizer.param_groups:
                    for parameter in group["params"]:
                        if parameter.grad is not None:
                            parameter.grad.fill_(float("inf"))

            def step(self, optimizer):
                del optimizer
                return None

            def update(self):
                self.scale_value /= 2

            def get_scale(self):
                return self.scale_value

        model = TinySmokeModel()
        batch = {
            "tokens": [["G", "D"]],
            "rel_label": torch.zeros((1, 2), dtype=torch.long),
        }
        example = {
            "metadata": {"document_id": "PM1"},
            "tokenized_text": ["G", "D"],
            "ner": [[0, 0, "Gene", "G"], [1, 1, "Disease", "D"]],
            "relations": [],
        }
        config = V1TrainingConfig(device="cpu", mixed_precision="none")

        with tempfile.TemporaryDirectory() as directory:
            plan = TrainingPlan(
                Path(directory) / "train.jsonl",
                Path(directory) / "checkpoints",
                config,
            )
            with patch(
                "biomedical_extractor.biored_training._load_glirel_model",
                return_value=model,
            ), patch(
                "biomedical_extractor.biored_training.load_training_examples",
                return_value=[example],
            ), patch(
                "biomedical_extractor.biored_training._native_loader",
                return_value=[batch],
            ), patch(
                "biomedical_extractor.biored_training._build_v1_optimizer",
                return_value=torch.optim.AdamW(
                    [{"params": [model.weight], "weight_decay": 0.0}], lr=0.1
                ),
            ), patch.object(torch.cuda.amp, "GradScaler", AlwaysOverflowScaler):
                result = run_gpu_smoke_test(plan)

        self.assertEqual(result["status"], "BLOCKER")
        self.assertEqual(result["attempt_count"], SMOKE_MAX_AMP_ATTEMPTS)
        self.assertEqual(result["amp_overflow_attempts"], SMOKE_MAX_AMP_ATTEMPTS)
        self.assertIn("persisted", result["blocker_reason"])
        self.assertEqual(len(result["scaler_scale_trajectory"]), SMOKE_MAX_AMP_ATTEMPTS)
        self.assertTrue(
            all(attempt["optimizer_update_skipped"] for attempt in result["attempts"])
        )
        self.assertIsNone(result["peak_cuda_memory_allocated_bytes"])
        self.assertIn("forward", result["stage_timings_seconds"])

    def test_training_update_schedule_remains_gradient_accumulation_based(self):
        import torch

        class TinyTrainingModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.weight = torch.nn.Parameter(torch.tensor(1.0))

            def forward(self, batch):
                del batch
                return {"total_loss": self.weight.square()}

            def save_pretrained(self, path):
                Path(path).mkdir(parents=True, exist_ok=True)

        model = TinyTrainingModel()
        example = {
            "metadata": {"document_id": "PM1"},
            "tokenized_text": ["G"],
            "ner": [],
            "relations": [],
        }
        config = V1TrainingConfig(
            device="cpu",
            mixed_precision="none",
            num_steps=3,
            gradient_accumulation=2,
            save_every=2,
        )

        def optimizer_builder(current_model, current_config):
            del current_config
            return torch.optim.AdamW(current_model.parameters(), lr=0.1)

        with tempfile.TemporaryDirectory() as directory:
            plan = TrainingPlan(
                Path(directory) / "train.jsonl",
                Path(directory) / "checkpoints",
                config,
            )
            with patch(
                "biomedical_extractor.biored_training._load_glirel_model",
                return_value=model,
            ), patch(
                "biomedical_extractor.biored_training.load_training_examples",
                return_value=[example],
            ), patch(
                "biomedical_extractor.biored_training._native_loader",
                return_value=[{}],
            ), patch(
                "biomedical_extractor.biored_training._build_v1_optimizer",
                side_effect=optimizer_builder,
            ):
                summary = run_training(plan)

        self.assertEqual(summary["steps"], 3)
        self.assertEqual(summary["optimizer_updates"], 2)
        self.assertEqual(summary["scheduler_total_steps"], 2)
        self.assertEqual(
            [entry["microstep"] for entry in summary["training_progression"]],
            [2, 3],
        )

    def test_training_counts_amp_skips_and_advances_scheduler_only_on_success(self):
        import torch

        class TinyTrainingModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.weight = torch.nn.Parameter(torch.tensor(1.0))

            def forward(self, batch):
                del batch
                return {"total_loss": self.weight.square()}

            def save_pretrained(self, path):
                Path(path).mkdir(parents=True, exist_ok=True)

        class OneSkippedUpdateScaler:
            instance = None

            def __init__(self, enabled):
                del enabled
                self.step_calls = 0
                self.scale_value = 8.0
                OneSkippedUpdateScaler.instance = self

            def is_enabled(self):
                return True

            def scale(self, loss):
                return loss

            def step(self, optimizer):
                self.step_calls += 1
                if self.step_calls > 1:
                    return optimizer.step()
                return None

            def update(self):
                if self.step_calls == 1:
                    self.scale_value /= 2

            def get_scale(self):
                return self.scale_value

        class RecordingScheduler:
            def __init__(self):
                self.step_calls = 0

            def step(self):
                self.step_calls += 1

        model = TinyTrainingModel()
        example = {
            "metadata": {"document_id": "PM1"},
            "tokenized_text": ["G"],
            "ner": [],
            "relations": [],
        }
        config = V1TrainingConfig(
            device="cpu",
            mixed_precision="none",
            num_steps=3,
            gradient_accumulation=2,
            save_every=2,
        )
        scheduler = RecordingScheduler()

        with tempfile.TemporaryDirectory() as directory:
            plan = TrainingPlan(
                Path(directory) / "train.jsonl",
                Path(directory) / "checkpoints",
                config,
            )
            with patch(
                "biomedical_extractor.biored_training._load_glirel_model",
                return_value=model,
            ), patch(
                "biomedical_extractor.biored_training.load_training_examples",
                return_value=[example],
            ), patch(
                "biomedical_extractor.biored_training._native_loader",
                return_value=[{}],
            ), patch(
                "biomedical_extractor.biored_training._build_v1_optimizer",
                return_value=torch.optim.AdamW(model.parameters(), lr=0.1),
            ), patch(
                "transformers.get_cosine_schedule_with_warmup",
                return_value=scheduler,
            ), patch.object(
                torch.cuda.amp, "GradScaler", OneSkippedUpdateScaler
            ):
                summary = run_training(plan)
                serialized = json.loads(
                    (Path(directory) / "checkpoints" / "training_summary.json")
                    .read_text(encoding="utf-8")
                )

        self.assertEqual(summary["optimizer_updates"], 1)
        self.assertEqual(summary["amp_skipped_updates"], 1)
        self.assertEqual(summary["intended_optimizer_updates"], 2)
        self.assertEqual(summary["final_scaler_scale"], 4.0)
        self.assertEqual(scheduler.step_calls, 1)
        self.assertEqual(serialized["optimizer_updates"], 1)
        self.assertEqual(serialized["amp_skipped_updates"], 1)
        self.assertEqual(serialized["final_scaler_scale"], 4.0)

    def test_scheduler_steps_use_optimizer_update_count(self):
        self.assertEqual(calculate_scheduler_steps(4_000, 8, 0.1), (500, 50))
        self.assertEqual(calculate_scheduler_steps(4_001, 8, 0.1), (501, 50))

    def test_v1_optimizer_uses_upstream_parameter_grouping(self):
        import torch

        class TinyGLiREL(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.token_rep_layer = torch.nn.Sequential(
                    torch.nn.Linear(2, 2), torch.nn.LayerNorm(2)
                )
                self.other = torch.nn.Sequential(
                    torch.nn.Linear(2, 2), torch.nn.LayerNorm(2)
                )
                self.frozen = torch.nn.Parameter(torch.ones(2), requires_grad=False)

        model = TinyGLiREL()
        config = V1TrainingConfig(device="cpu", mixed_precision="none")
        optimizer = _build_v1_optimizer(model, config)

        grouped = {}
        grouped_ids = []
        for group in optimizer.param_groups:
            for parameter in group["params"]:
                grouped[id(parameter)] = (
                    float(group["lr"]),
                    float(group["weight_decay"]),
                )
                grouped_ids.append(id(parameter))

        expected = {
            "token_rep_layer.0.weight": (1e-5, 0.01),
            "token_rep_layer.0.bias": (1e-5, 0.0),
            "token_rep_layer.1.weight": (1e-5, 0.0),
            "token_rep_layer.1.bias": (1e-5, 0.0),
            "other.0.weight": (1e-4, 0.01),
            "other.0.bias": (1e-4, 0.0),
            "other.1.weight": (1e-4, 0.0),
            "other.1.bias": (1e-4, 0.0),
        }
        named_parameters = dict(model.named_parameters())
        self.assertFalse(hasattr(model, "_rel_filtering"))
        self.assertEqual(
            set(grouped),
            {
                id(parameter)
                for parameter in named_parameters.values()
                if parameter.requires_grad
            },
        )
        self.assertEqual(len(grouped_ids), len(set(grouped_ids)))
        for name, parameter in named_parameters.items():
            if parameter.requires_grad:
                self.assertEqual(grouped[id(parameter)], expected[name])
            else:
                self.assertNotIn(id(parameter), grouped)

        serialized = config.to_dict()
        self.assertEqual(serialized["weight_decay_encoder"], 0.01)
        self.assertEqual(serialized["weight_decay_other"], 0.01)

    def test_smoke_and_training_use_the_shared_optimizer_builder(self):
        class OptimizerBuilderCalled(RuntimeError):
            pass

        class FakeModel:
            def train(self):
                return self

        model = FakeModel()
        example = {
            "metadata": {"document_id": "PM1"},
            "tokenized_text": ["G"],
            "ner": [],
            "relations": [],
        }
        config = V1TrainingConfig(
            device="cpu",
            mixed_precision="none",
            num_steps=1,
            gradient_accumulation=1,
            save_every=1,
        )

        with tempfile.TemporaryDirectory() as directory:
            plan = TrainingPlan(
                Path(directory) / "train.jsonl",
                Path(directory) / "checkpoints",
                config,
            )
            with patch(
                "biomedical_extractor.biored_training._load_glirel_model",
                return_value=model,
            ), patch(
                "biomedical_extractor.biored_training.load_training_examples",
                return_value=[example],
            ), patch(
                "biomedical_extractor.biored_training._native_loader",
                return_value=object(),
            ), patch(
                "biomedical_extractor.biored_training._build_v1_optimizer",
                side_effect=OptimizerBuilderCalled,
            ) as builder:
                with self.assertRaises(OptimizerBuilderCalled):
                    run_gpu_smoke_test(plan)
                with self.assertRaises(OptimizerBuilderCalled):
                    run_training(plan)

        self.assertEqual(builder.call_count, 2)
        self.assertIs(builder.call_args_list[0].args[0], model)
        self.assertIs(builder.call_args_list[1].args[0], model)
        self.assertIs(builder.call_args_list[0].args[1], config)
        self.assertIs(builder.call_args_list[1].args[1], config)

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

    def test_native_collator_uses_inference_order_and_negative_pairs(self):
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

        batch = next(iter(_native_loader(native, [example], V1TrainingConfig())))

        self.assertEqual(
            tuple(batch["classes_to_id"][0]),
            tuple(CANONICAL_TO_PROMPT.values()),
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

    def test_prepared_statistics_are_path_independent(self):
        root = {
            "source": "BioC",
            "date": "2021-11-30",
            "key": "BioC.key",
            "documents": [
                {
                    "id": "PM1",
                    "passages": [{"offset": 0, "text": "G", "annotations": []}],
                    "relations": [],
                }
            ],
        }

        stats_bytes = []
        with tempfile.TemporaryDirectory() as directory:
            for root_name in ("root_a", "root_b"):
                base = Path(directory) / root_name / "BioRED"
                base.mkdir(parents=True)
                for filename in ("Train.BioC.JSON", "Dev.BioC.JSON"):
                    (base / filename).write_text(json.dumps(root), encoding="utf-8")

                dataset = load_biored(base.parent, "train")
                dev_path = base / "Dev.BioC.JSON"
                dev_sha256 = hashlib.sha256(dev_path.read_bytes()).hexdigest()
                verified_dev = verify_biored_dev_hash(
                    base.parent, expected_sha256=dev_sha256
                )
                paths = write_prepared_corpus(
                    prepare_training_corpus(dataset),
                    Path(directory) / root_name / "output",
                    verified_dev=verified_dev,
                )
                stats_bytes.append(paths["stats"].read_bytes())

        self.assertEqual(stats_bytes[0], stats_bytes[1])
        stats = json.loads(stats_bytes[0])
        self.assertEqual(stats["dataset"]["filename"], "Train.BioC.JSON")
        self.assertNotIn("path", stats["dataset"])
        self.assertEqual(
            stats["verified_hashes"]["dev"]["filename"], "Dev.BioC.JSON"
        )
        self.assertNotIn("path", stats["verified_hashes"]["dev"])

    def test_json_writer_emits_canonical_lf_utf8_bytes(self):
        value = {"z": ["line", {"nested": True}], "a": "value"}
        expected = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.json"
            _write_json(path, value)
            emitted = path.read_bytes()

        self.assertNotIn(b"\r\n", emitted)
        self.assertNotIn(b"\r", emitted)
        self.assertEqual(emitted[-1:], b"\n")
        self.assertNotEqual(emitted[-2:], b"\n\n")
        self.assertEqual(emitted, expected)

    def test_training_plan_is_constructed_without_checkpoint_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            jsonl = Path(directory) / "train.jsonl"
            jsonl.write_text("{}\n", encoding="utf-8")
            plan = build_training_plan(jsonl, Path(directory) / "checkpoints")

        self.assertEqual(plan.config.checkpoint, "jackboyla/glirel-large-v0")
        self.assertEqual(plan.config.lr_encoder, 1e-5)
        self.assertEqual(plan.config.lr_others, 1e-4)
        self.assertEqual(plan.config.weight_decay_encoder, 0.01)
        self.assertEqual(plan.config.weight_decay_other, 0.01)
        self.assertEqual(plan.config.train_batch_size, 1)
        self.assertEqual(plan.config.gradient_accumulation, 8)
        self.assertEqual(plan.config.mixed_precision, "fp16")
        self.assertEqual(plan.config.num_steps, 4_000)
        self.assertEqual(plan.config.save_every, 1_000)
        self.assertEqual(plan.config.num_unseen_rel_types, 0)


if __name__ == "__main__":
    unittest.main()
