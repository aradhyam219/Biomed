"""Freeze the unassessable review, then unblind this no-response experiment.

This deliberately handles only the aborted experiment with no provider outputs.
It cannot score empty graphs, extrapolate costs, or turn timeouts into quality.
"""

from __future__ import annotations

import argparse
from collections import Counter

from run_comparison import CACHE, REPORT, digest, now, read, verify, write


def outcomes():
    preflight = read(REPORT / "preflight.json")
    state = read(REPORT / "run_state.json")
    assert state["status"] == "aborted_stop_condition"
    results = []
    for job in preflight["execution_order"]:
        path = REPORT / "outputs" / job["paper_id"].replace(":", "_").lower() / (job["alias"].replace(" ", "_").lower() + ".json")
        result = read(path)
        assert result["status"] in {"provider_failure", "not_run_aborted"}
        assert result.get("validated_relations") is None
        assert all(not attempt["provider_response_received"] and attempt["usage"] is None
                   for attempt in result["attempts"])
        results.append((path, result))
    return preflight, state, results


def freeze_review():
    verify()
    _, _, results = outcomes()
    reference_check = read(REPORT / "review" / "source_reference_verification.json")
    for relative, expected in reference_check["reference_file_sha256"].items():
        assert digest((REPORT / relative).read_bytes()) == expected
    review = {
        "frozen_utc": now(),
        "phase": "before_model_key_disclosure",
        "status": "not_assessable_no_provider_outputs",
        "model_quality_winner": None,
        "semantic_relation_review_performed": False,
        "coverage": "Every clear, ambiguous, and tentative reference claim is not_assessable for both conditions; neither condition supplied any final relation output.",
        "observed_errors": [
            {"paper_id": result["paper_id"], "alias": result["alias"],
             "status": result["status"], "exact_error": result.get("exact_error")}
            for _, result in results
        ],
        "reference_items_per_paper": reference_check["items_per_paper"],
        "human_gold": False,
        "reason": "Transport timeouts and unattempted jobs cannot establish omissions, direction errors, hallucinations, or an intelligence ranking.",
    }
    target = REPORT / "review" / "semantic_review.json"
    freeze = REPORT / "review" / "review_freeze.json"
    if target.exists() or freeze.exists():
        raise RuntimeError("Do not overwrite a frozen review")
    write(target, review)
    paths = [target, REPORT / "review" / "source_reference_verification.json",
             *(REPORT / relative for relative in reference_check["reference_file_sha256"]),
             *(path for path, _ in results)]
    write(freeze, {"frozen_utc": now(), "model_key_read_by_analysis": False,
                   "sha256": {str(path.relative_to(REPORT)): digest(path.read_bytes()) for path in paths}})
    print("Review frozen before model-key disclosure; no semantic comparison is assessable.")


def unblind():
    freeze = read(REPORT / "review" / "review_freeze.json")
    for relative, expected in freeze["sha256"].items():
        assert digest((REPORT / relative).read_bytes()) == expected
    preflight, state, results = outcomes()
    mapping = read(CACHE / "model_key.json")
    assert set(mapping.values()) == set(preflight["models"])
    counts = {}
    for alias, model in mapping.items():
        selected = [result for _, result in results if result["alias"] == alias]
        counts[model] = {
            "alias": alias, "planned_jobs": len(selected),
            "status_counts": dict(Counter(result["status"] for result in selected)),
            "provider_requests": sum(len(result["attempts"]) for result in selected),
            "provider_responses_received": 0,
            "successful_validated_outputs": 0,
            "returned_token_usage": None,
            "estimated_actual_cost_usd": None,
            "attempts": [{"paper_id": result["paper_id"], "elapsed_seconds": result["elapsed_seconds"],
                          "exact_error": result["exact_error"]}
                         for result in selected if result["attempts"]],
        }
    output = {
        "unblinded_utc": now(), "status": state["status"],
        "baseline_repository_sha": preflight["baseline_head"],
        "model_mapping": mapping, "model_results": counts,
        "planned_jobs": 16, "completed_attempted_jobs": len(state["completed"]),
        "unattempted_jobs": 16 - len(state["completed"]),
        "successful_paired_papers": 0,
        "intelligence_comparison": "unresolved_no_outputs",
        "model_quality_winner": None,
        "cost_status": "Unknown. No usage was returned; a timed-out request is not assumed free.",
        "started_utc": state["started_utc"], "completed_utc": state["completed_utc"],
        "review_freeze_sha256": digest((REPORT / "review" / "review_freeze.json").read_bytes()),
        "production_changed": False,
    }
    target = REPORT / "analysis.json"
    if target.exists():
        raise RuntimeError("Do not overwrite the analysis")
    write(target, output)
    print(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-review", action="store_true")
    parser.add_argument("--unblind", action="store_true")
    args = parser.parse_args()
    if args.freeze_review and not args.unblind:
        freeze_review()
    elif args.unblind and not args.freeze_review:
        unblind()
    else:
        parser.error("Choose exactly one phase")
