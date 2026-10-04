"""One operational recovery of frozen requests that failed before an ID existed.

Initial failures remain intact. No successful case is rerun, no prompt is
changed, and a second recovery is refused. Record safe causal transport types
without storing provider bodies or credentials.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment as e


def main():
    manifest = e.verify_freeze()
    assert e.git("rev-parse", "HEAD") == e.START_SHA
    state_path = e.REPORT / "recovery_state.json"
    if state_path.exists():
        raise RuntimeError("Recovery already attempted; refusing a second recovery")
    config = e.previous._candidate_config()
    assert e.previous._config_record(config) == manifest["configuration"]
    prompt = (e.REPORT / "prompt_refined.txt").read_text(encoding="utf-8")
    state = dict(status="running", reason="Initial DNS transport failures; subsequent endpoint DNS resolved", cases=[])
    e.write(state_path, state)
    for row in manifest["cases"]:
        base = e.REPORT / row["directory"] / row["slug"]
        initial = e.read(base / "refined.json")
        if initial["status"] == "success":
            continue
        assert all(d.get("status") == "create_failed" and not d.get("response_id") for d in initial["generation_diagnostics"])
        e.verify_freeze()
        attempt_path = base / "recovery_attempt_01.json"
        assert not attempt_path.exists()
        case = e.read(base / "input.json")
        entities = tuple(e.Entity(**v) for v in case["entities"])
        assert e.sha(e._build_prompt(case["source_text"],entities,prompt).encode()) == row["refined_request_sha256"]
        attempt = dict(status="launch_started", started_at_utc=e.previous._utc_now(), diagnostic_events=[])
        e.write(attempt_path, attempt)

        def diagnostic(snapshot):
            attempt["diagnostic_events"].append({"recorded_at_utc":e.previous._utc_now(), **e.previous._sanitize_diagnostic(snapshot)})
            e.write(attempt_path, attempt)

        started = time.perf_counter()
        extractor = e.LLMRelationExtractor.from_openai(config,prompt=prompt,diagnostics_callback=diagnostic)
        try:
            recording = e.previous._RecordingRelationExtractor(extractor)
            pipeline = e.LLMExtractionPipeline(e.previous._FrozenEntityExtractor(case["source_text"],entities),recording)
            graph = pipeline.extract_graph(case["source_text"],document_id=case["paper_id"],paper_title=case["title"]).to_dict()
            result = dict(status="success", relations=[r.to_dict() for r in recording.last_result.relations], graph=graph)
            e.write(e.REPORT / "graphs/refined" / f"{row['slug']}.json", graph)
        except Exception as error:
            result = dict(status="failed", error_class=type(error).__name__)
        diagnostics = [e.previous._sanitize_diagnostic(v) for v in extractor.last_generation_diagnostics]
        result.update(elapsed_seconds=round(time.perf_counter()-started,6), completed_at_utc=e.previous._utc_now(),
                      generation_diagnostics=diagnostics,repair_attempts=max(0,len(diagnostics)-1),
                      operational_recovery_number=1,initial_attempt_path=(base/'refined.json').relative_to(e.ROOT).as_posix())
        e.write(base / "refined_retry_01.json", result)
        attempt.update(status=result["status"],final_generation_diagnostics=diagnostics)
        e.write(attempt_path,attempt)
        state["cases"].append(dict(slug=row["slug"],status=result["status"]))
        e.write(state_path,state)
        print(f"{row['slug']}: {result['status']}, {len(result.get('relations',[]))} relations, {result['elapsed_seconds']:.1f}s",flush=True)
    state.update(status="complete",completed_at_utc=e.previous._utc_now())
    e.write(state_path,state)


if __name__ == "__main__":
    main()
