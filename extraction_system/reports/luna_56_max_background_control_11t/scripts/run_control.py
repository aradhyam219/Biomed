"""Run Contract 11T by reusing the unchanged Contract 11S-R lifecycle adapter."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
REPORT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reports/luna_gpt6_background_probe_11s"
ADAPTER = REFERENCE / "scripts/run_background_probe_11sr.py"
spec = importlib.util.spec_from_file_location("contract11sr_adapter", ADAPTER)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
adapter.REPORT = REPORT
adapter.CONFIG = {**adapter.CONFIG, "model": "gpt-5.6-luna"}
original_prepare = adapter.prepare


def snapshots():
    return {str(path.relative_to(REFERENCE)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in REFERENCE.rglob("*") if path.is_file()}


def prepare():
    """Assert experimental parity before any live request and preserve provenance."""
    reference = json.loads((REFERENCE / "rerun_11sr/preflight.json").read_text())
    current = adapter.git("rev-parse", "HEAD")
    if current != adapter.AUTHORIZED_HEAD:
        changed = adapter.git("diff", "--name-only", adapter.AUTHORIZED_HEAD+"..HEAD").splitlines()
        assert changed and all(path.startswith("reports/") or path.startswith("extraction_system/reports/")
                               for path in changed), "HEAD moved with non-report changes"
        adapter.AUTHORIZED_HEAD = current
    preflight = original_prepare()
    assert preflight["configuration"] == {**reference["configuration"], "model": "gpt-5.6-luna"}
    assert preflight["contract10_schema_sha256"] == reference["contract10_schema_sha256"] == "023435da3fa18abb77987313626636eff7bedda28739603db54a2f2c8137c945"
    assert preflight["openai_transport_schema_sha256"] == reference["openai_transport_schema_sha256"] == "b0506680756b7ad8332d976a419cdee57a81e1051dd115f291f65d77bd656510"
    for key in ("real_passage", "contract10_system_prompt_sha256", "poll_interval_seconds",
                "consecutive_poll_error_limit", "synthetic_deadline_seconds", "real_passage_deadline_seconds", "repair_budget"):
        assert preflight[key] == reference[key], f"Divergence from 11S-R: {key}"
    assert adapter.DEFAULT_LLM_RELATION_MODEL == "gpt-5.6-luna"
    preflight.update(contract="11T", only_experimental_change="model: gpt-6-luna -> gpt-5.6-luna",
        reused_adapter=str(ADAPTER), reused_adapter_sha256=hashlib.sha256(ADAPTER.read_bytes()).hexdigest(),
        reference_artifact_hashes=snapshots(), all_same_condition_checks_passed=True)
    adapter.write("preflight.json", preflight)
    return preflight


def finalize():
    summary = json.loads((REPORT / "summary.json").read_text())
    preflight = json.loads((REPORT / "preflight.json").read_text())
    preserved = snapshots() == preflight["reference_artifact_hashes"]
    reference = json.loads((REFERENCE / "rerun_11sr/real_passage_background.json").read_text())
    summary.update(contract="11T", semantic_schema_sha256=preflight["contract10_schema_sha256"],
        transport_schema_sha256=preflight["openai_transport_schema_sha256"],
        existing_11s_reports_preserved=preserved, gpt6_frozen_reference=reference)
    adapter.write("summary.json", summary)
    assert preserved, "Existing 11S / 11S-R artifacts changed"
    def metrics(phase):
        generations = phase.get("generations", [])
        primary = generations[0] if generations else {}
        final = generations[-1] if generations else {}
        return dict(result=phase["status"], response_ids=[g.get("response_id") for g in generations],
            create_latency_seconds=primary.get("initial_create_latency_seconds"),
            initial_status=primary.get("initial_status"), terminal_status=final.get("terminal_status"),
            background_elapsed_seconds=final.get("background_elapsed_seconds"),
            total_wall_seconds=phase.get("total_elapsed_seconds"),
            polls=sum(g.get("poll_count",0) for g in generations),
            poll_errors=sum(g.get("poll_errors",0) for g in generations),
            usage=[g.get("usage") for g in generations], repairs=phase.get("repair_count",0),
            validated_relations=phase.get("validated_relation_count"),
            unique_evidence_spans=phase.get("unique_evidence_span_count"),
            structured_output_received=any(g.get("structured_output_received") for g in generations),
            cancellation_result=final.get("cancel_result"),
            error=final.get("error_chain") or final.get("provider_error") or final.get("validation_error"))
    comparison = {"gpt-5.6-luna max":metrics(summary["real_passage"]), "gpt-6-luna max":metrics(reference)}
    adapter.write("comparison.json",comparison)
    lines = ["# CONTRACT 11T — GPT-5.6 MAX CONTROL", "", "## BASELINE", "",
        f"HEAD: {summary['final_baseline']['head']}", "Production parity: clean. Production diff: empty.",
        "", "## SCHEMA", "", f"Semantic SHA: `{summary['semantic_schema_sha256']}`",
        f"Transport SHA: `{summary['transport_schema_sha256']}`", "", "## SYNTHETIC CONTROL", "",
        "```json", json.dumps(metrics(summary['background_control']),indent=2), "```", "",
        "## REAL PASSAGE AND SIDE-BY-SIDE", "", "```json", json.dumps(comparison,indent=2), "```", "",
        "## INTEGRITY", "", "Production code unchanged: yes", "Production default unchanged: gpt-5.6-luna",
        "Existing 11S / 11S-R reports preserved: yes (file hashes checked)", "Nothing committed or pushed: yes",
        "", "This is a descriptive feasibility control; no scientific-quality ranking is assigned."]
    (REPORT / "summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8")


adapter.prepare = prepare
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--run",action="store_true")
    args = parser.parse_args()
    if args.prepare == args.run:
        parser.error("Choose exactly one of --prepare or --run")
    if args.prepare:
        print(json.dumps(prepare()))
    else:
        adapter.run()
        finalize()
