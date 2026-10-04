"""Contract 11U: sequential candidate orchestration around the frozen 11S-R adapter.

The adapter retains creation, ID persistence, polling, cancellation and repairs.
This wrapper records tier/timing metadata, computes costs, and freezes a blind
review packet without judging the scientific content.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
REPORT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "reports/luna_gpt6_background_probe_11s/scripts/run_background_probe_11sr.py"
ADAPTER_SHA = "9bfeabafb9c22606669fa857cf3af8c0eee8fcc255b1c87e4bf8e689b2a9ba10"
TRANSPORT_SHA = "b0506680756b7ad8332d976a419cdee57a81e1051dd115f291f65d77bd656510"
spec = importlib.util.spec_from_file_location("contract11sr_adapter", ADAPTER)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
BASELINE = p.baseline
WRITE = p.write
CANDIDATES = [
    dict(number=1, directory="gpt_56_luna_max_fast", model="gpt-5.6-luna", effort="max", tier="fast",
         rates=dict(input=0.40, cached=0.04, cache_write=0.50, output=2.40)),
    dict(number=2, directory="gpt_61_sol_medium_standard", model="gpt-6.1-sol", effort="medium", tier="default",
         rates=dict(input=2.00, cached=0.10, cache_write=2.50, output=10.00)),
    dict(number=3, directory="gpt_6_luna_max_fast", model="gpt-6-luna", effort="max", tier="fast",
         rates=dict(input=0.20, cached=0.02, cache_write=0.25, output=1.00)),
]
OBSERVATIONS = {}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    p.REPORT = REPORT
    WRITE(name, value)


def existing_reports():
    return {str(path.relative_to(ROOT)):digest(path) for path in (ROOT/"reports").rglob("*")
            if path.is_file() and REPORT not in path.parents}


def baseline():
    if digest(ADAPTER) != ADAPTER_SHA:
        raise RuntimeError("Background adapter integrity mismatch")
    state = BASELINE()
    if state["production_model_default"] != "gpt-5.6-luna":
        raise RuntimeError("Production default changed")
    p.frozen()
    wire=p.REPORT/"transport_schema.json"
    if wire.exists() and p.sha(p.canonical(json.loads(wire.read_text()))) != TRANSPORT_SHA:
        raise RuntimeError("Transport schema integrity mismatch")
    return state


def prepare():
    p.REPORT = REPORT
    current = p.git("rev-parse", "HEAD")
    if current != p.AUTHORIZED_HEAD:
        delta = p.git("diff", "--name-only", p.AUTHORIZED_HEAD+"..HEAD").splitlines()
        if not delta or not all(path.startswith(("reports/", "extraction_system/reports/")) for path in delta):
            raise RuntimeError("HEAD changed outside benchmark reports")
        p.AUTHORIZED_HEAD = current
    state = baseline()
    manifest, text, entities = p.frozen()
    transport = p.strict_transport_schema()
    equivalence = p.verify_transport(transport)
    if p.sha(p.canonical(transport)) != TRANSPORT_SHA:
        raise RuntimeError("Transport schema hash mismatch")
    write("semantic_schema.json",p.SCHEMA)
    write("transport_schema.json",transport)
    write("frozen_input.json",manifest)
    write("offline_equivalence.json",equivalence)
    preflight = dict(contract="11U", created_timestamp=p.now(), baseline=state,
        adapter_path=str(ADAPTER), adapter_sha256=digest(ADAPTER),
        semantic_schema_sha256=p.EXPECTED_SCHEMA, transport_schema_sha256=TRANSPORT_SHA,
        real_passage={key:manifest[key] for key in ("paper_id","passage_id","source_range","source_characters",
                      "entity_count","source_sha256","entity_packet_sha256","prompt_sha256")},
        candidates=CANDIDATES, execution_order=[c["number"] for c in CANDIDATES],
        shared_configuration=dict(background=True,store=False,max_output_tokens=128000,provider_sdk_retries=0,
                                  temperature="unset",synthetic_deadline_seconds=120,
                                  real_deadline_seconds=900,repair_budget=2,poll_interval_seconds=3,
                                  consecutive_poll_error_limit=5),
        network_execution_mode="require_escalated / network-capable for every live provider operation",
        offline_equivalence=equivalence, existing_report_hashes=existing_reports())
    write("preflight.json",preflight)
    write("cost_assumptions.json",dict(pricing_snapshot_date="2026-10-04",currency="USD",
        estimated_not_invoice=True,context="short-context text",rates_per_million={c["directory"]:c["rates"] for c in CANDIDATES},
        reasoning_tokens="included in output_tokens; never charged twice",
        decomposition="regular_input=input_tokens-cached_input_tokens-cache_write_tokens",
        unavailable_usage="unknown, not zero; candidate totals are partial when usage is absent"))
    return preflight


class ObservedResponses:
    """Delegate SDK calls unchanged and record only public response metadata."""
    def __init__(self, sdk):
        self.sdk = sdk
        self.responses = self

    def observe(self, response, operation):
        item = dict(timestamp=p.now(), operation=operation, status=response.status,
                    returned_service_tier=response.service_tier)
        OBSERVATIONS.setdefault(response.id, []).append(item)
        p.write("response_observations.json",OBSERVATIONS)
        return response

    def create(self, **kwargs):
        baseline()
        if p.sha(kwargs["input"]) != p.EXPECTED_PROMPT and "REPAIR INSTRUCTION:" not in kwargs["input"]:
            expected = p.sha(p._build_prompt(p.SYNTHETIC,p.SYNTHETIC_ENTITIES,p.RELATION_EXTRACTION_SYSTEM_PROMPT))
            if p.sha(kwargs["input"]) != expected:
                raise RuntimeError("Prompt integrity mismatch")
        if p.sha(p.canonical(kwargs["text"]["format"]["schema"])) != TRANSPORT_SHA:
            raise RuntimeError("Transport schema integrity mismatch")
        return self.observe(self.sdk.responses.create(**kwargs),"create")

    def retrieve(self, response_id, **kwargs):
        return self.observe(self.sdk.responses.retrieve(response_id,**kwargs),"retrieve")

    def cancel(self, response_id, **kwargs):
        return self.observe(self.sdk.responses.cancel(response_id,**kwargs),"cancel")


def enrich(outcome, candidate):
    """Attach poll-resolution timing/tier estimates and preserve parsed payloads."""
    mismatches = []
    for g in outcome.get("generations",[]):
        events = OBSERVATIONS.get(g.get("response_id"),[])
        tiers = sorted({event["returned_service_tier"] for event in events if event["returned_service_tier"]})
        expected = {"fast","priority"} if candidate["tier"] == "fast" else {"default"}
        mismatch = bool(tiers) and any(tier not in expected for tier in tiers)
        mismatches.append(mismatch)
        g.update(requested_service_tier=candidate["tier"],returned_service_tiers=tiers,
                 returned_service_tier=tiers[-1] if len(tiers)==1 else None,
                 service_tier_mismatch=mismatch,service_tier_verified=bool(tiers) and not mismatch,
                 status_history=events)
        if events:
            from datetime import datetime
            start=datetime.fromisoformat(events[0]["timestamp"])
            first_progress=next((event for event in events if event["status"]=="in_progress"),None)
            first_queued=next((event for event in events if event["status"]=="queued"),None)
            offset=lambda event:round((datetime.fromisoformat(event["timestamp"])-start).total_seconds(),3) if event else None
            g.update(time_to_first_known_queued_seconds=offset(first_queued),
                     time_to_first_observed_in_progress_seconds=offset(first_progress),
                     approximate_queue_duration_seconds=offset(first_progress) if first_queued else None,
                     approximate_in_progress_duration_seconds=round(offset(events[-1])-offset(first_progress),3) if first_progress else None,
                     timing_estimates="poll-resolution observations; exact queue/inference boundaries unavailable")
        usage=g.get("usage")
        if usage:
            input_details=usage.get("input_tokens_details") or {}
            output_details=usage.get("output_tokens_details") or {}
            g["derived_usage"]=dict(cached_input_tokens=input_details.get("cached_tokens"),
                cache_write_tokens=input_details.get("cache_write_tokens"),reasoning_tokens=output_details.get("reasoning_tokens"),
                visible_output_tokens_derived=usage["output_tokens"]-output_details["reasoning_tokens"]
                    if output_details.get("reasoning_tokens") is not None else None)
        if g.get("structured_output"):
            try:
                parsed=p._parse_structured_response(g["structured_output"])
            except p.RelationValidationError as error:
                g.update(parser_result="rejected",parser_error=p.redact(str(error)))
            else:
                g.update(parser_result="accepted",parsed_contract10_output={"relations":list(parsed)})
        else:
            g["parser_result"]="not_run"
        g["validation_result"]="accepted" if g["status"]=="success" else (
            "rejected" if g["status"]=="contract10_validation_failure" else "not_accepted")
    outcome["service_tier_mismatch"]=any(mismatches)
    outcome["service_tier_verified"]=bool(outcome.get("generations")) and all(
        g["service_tier_verified"] for g in outcome["generations"])
    return outcome


def costs(outcome,candidate):
    requests=[]
    for g in outcome.get("generations",[]):
        usage=g.get("usage")
        row=dict(response_id=g.get("response_id"),repair=g.get("repair",False),usage=usage,
                 estimated_request_cost_usd=None)
        if usage:
            details=usage.get("input_tokens_details") or {}
            cached=details.get("cached_tokens")
            writes=details.get("cache_write_tokens")
            if cached is not None and writes is not None:
                regular=usage["input_tokens"]-cached-writes
                if regular>=0:
                    rates=candidate["rates"]
                    parts=dict(input_cost=regular*rates["input"]/1e6,cached_cost=cached*rates["cached"]/1e6,
                        cache_write_cost=writes*rates["cache_write"]/1e6,output_cost=usage["output_tokens"]*rates["output"]/1e6)
                    row.update(regular_input_tokens=regular,cached_input_tokens=cached,cache_write_tokens=writes,
                        components_usd=parts,estimated_request_cost_usd=sum(parts.values()))
                else:
                    row["limitation"]="input usage components overlap or exceed input total"
            else:
                row["limitation"]="provider omitted cache usage fields; decomposition cannot be verified"
        else:
            row["limitation"]="provider usage unavailable; cost unknown"
        if g.get("service_tier_mismatch"):
            row["limitation"]="service tier mismatch; requested-tier estimate does not establish served-tier cost"
            row["estimated_request_cost_usd"]=None
        requests.append(row)
    return requests


def finish(results,preflight,interruption=None):
    """Freeze outputs and a randomized blind packet after terminal experiments."""
    preserved=existing_reports()==preflight["existing_report_hashes"]
    state=baseline()
    operations=[]
    cost_rows=[]
    for row in results:
        candidate=row["candidate"]
        operations.append(row)
        synthetic=costs(row["synthetic"],candidate)
        real=costs(row["real"],candidate)
        known=lambda items:sum(item["estimated_request_cost_usd"] or 0 for item in items)
        all_requests=synthetic+real
        complete=bool(all_requests) and all(item["estimated_request_cost_usd"] is not None for item in all_requests)
        cost_rows.append(dict(candidate=candidate,synthetic_requests=synthetic,real_requests=real,
            synthetic_cost_usd=known(synthetic) if all(item["estimated_request_cost_usd"] is not None for item in synthetic) else None,
            primary_real_generation_cost_usd=next((item["estimated_request_cost_usd"] for item in real if not item["repair"]),None),
            repair_cost_usd=known([item for item in real if item["repair"]]) if all(item["estimated_request_cost_usd"] is not None for item in real if item["repair"]) else None,
            total_candidate_cost_usd=known(all_requests) if complete else None,
            known_partial_cost_usd=known(all_requests),cost_complete=complete))
    write("operations.json",operations)
    write("comparison_unblinded.json",operations)
    write("costs.json",dict(currency="USD",estimated_not_invoice=True,candidates=cost_rows))
    manifest,source,entities=p.frozen()
    eligible=[row for row in results if row["real"].get("contract10_success")]
    random.SystemRandom().shuffle(eligible)
    labels=["Candidate A","Candidate B","Candidate C"]
    packet=dict(source_text=source,supplied_entities=manifest["entity_packet"],candidates=[])
    key={}
    output_hashes={}
    for label,row in zip(labels,eligible):
        relations=row["real"]["validated_relations"]
        packet["candidates"].append(dict(candidate=label,relations=relations))
        key[label]=row["candidate"]
        output_hashes[label]=p.sha(p.canonical({"relations":relations}))
    write("review/blind_packet.json",packet)
    write("review/model_key.json",key)
    write("review/review_freeze.json",dict(created_timestamp=p.now(),source_sha256=p.sha(source),
        entity_packet_sha256=manifest["entity_packet_sha256"],validated_output_sha256=output_hashes,
        blind_packet_sha256=digest(REPORT/"review/blind_packet.json"),model_key_sha256=digest(REPORT/"review/model_key.json"),
        hash_conventions=dict(validated_output="compact sorted JSON {relations: [...]}",
                             entities="indent=2 sorted JSON, frozen entity packet")))
    rubric=["explicit-source support","missed explicit relations","unsupported relations","endpoint correctness",
        "directionality","negation handling","predicate fidelity","assertion completeness","evidence grounding",
        "intervention preservation","effects preservation","context preservation","multi-entity mechanism handling",
        "duplicate/redundant relations","alias/naming-only noise","semantic compression loss",
        "overall usefulness for the evidence-backed graph"]
    write("review/review_template.json",dict(reviewer="",review_frozen_timestamp=None,
        candidates={item["candidate"]:{criterion:None for criterion in rubric} for item in packet["candidates"]}))
    md=["# Blind scientific review", "", "Review and freeze this assessment before opening the model key or operational metrics.",
        "", "## Exact source", "", source, "", "## Exact supplied entities", "", "```json",
        json.dumps(manifest["entity_packet"],ensure_ascii=False,indent=2), "```"]
    for item in packet["candidates"]:
        md += ["", "## "+item["candidate"], "", "```json",json.dumps(item["relations"],ensure_ascii=False,indent=2),"```"]
    (REPORT/"review/blind_packet.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    serialized=json.dumps(packet)
    for token in ("gpt-", "resp_", "service_tier", "reasoning_tokens", "elapsed_seconds", "cost_usd"):
        if token in serialized:
            raise RuntimeError("Blind packet contains operational identity metadata")
    summary=dict(contract="11U",execution_complete=len(results)==3 and not interruption,
        candidate_terminal={str(c["number"]):any(row["candidate"]["number"]==c["number"] for row in results) for c in CANDIDATES},
        production_code_unchanged=True,production_default_unchanged=state["production_model_default"]=="gpt-5.6-luna",
        existing_reports_preserved=preserved,nothing_committed_or_pushed=True,
        blind_review_packet=str(REPORT/"review/blind_packet.json"),model_key=str(REPORT/"review/model_key.json"),
        unblinded_operations=str(REPORT/"operations.json"),cost_report=str(REPORT/"costs.json"),
        interruption=interruption,final_baseline=state)
    write("summary.json",summary)
    (REPORT/"summary.md").write_text("# Contract 11U\n\n"+json.dumps(summary,indent=2)+
        "\n\nGive Talia review/blind_packet.json first. Keep the model key and unblinded metrics separate until her semantic review is frozen.\n",encoding="utf-8")
    if not preserved:
        raise RuntimeError("Existing benchmark reports changed")
    print(json.dumps({"execution_complete":summary["execution_complete"],"candidate_terminal":summary["candidate_terminal"]}))


def run():
    if (REPORT/"run_state.json").exists():
        raise RuntimeError("Run state already exists; refusing duplicate trial")
    preflight=prepare()
    p.SECRET=p.env_value(p.env_value("OPENAI_API_KEY_ENV") or "OPENAI_API_KEY") or ""
    if not p.SECRET:
        raise RuntimeError("Provider credential unavailable")
    results=[]
    manifest,text,entities=p.frozen()
    with p.OpenAI(api_key=p.SECRET,base_url=p.env_value("OPENAI_BASE_URL") or None,max_retries=0,timeout=20) as sdk:
        client=ObservedResponses(sdk)
        for candidate in CANDIDATES:
            baseline()
            p.frozen()
            p.REPORT=REPORT/"candidate_runs"/candidate["directory"]
            p.REPORT.mkdir(parents=True,exist_ok=True)
            p.CONFIG=dict(model=candidate["model"],reasoning={"effort":candidate["effort"]},
                max_output_tokens=128000,background=True,store=False,service_tier=candidate["tier"])
            p.HISTORY.clear()
            OBSERVATIONS.clear()
            def candidate_write(name,value):
                name={"synthetic_background.json":"synthetic.json","real_passage_background.json":"real.json"}.get(name,name)
                WRITE(name,value)
            p.write=candidate_write
            WRITE("transport_schema.json",json.loads((REPORT/"transport_schema.json").read_text()))
            WRITE("poll_history.json",[])
            real=dict(status="not_run",reason="Synthetic control must succeed",contract10_success=False,generations=[])
            WRITE("real.json",real)
            # This root-level write preserves p.REPORT for the reused adapter.
            active=p.REPORT
            write("run_state.json",dict(active_candidate=candidate["number"],terminal_candidates=len(results),status="running"))
            p.REPORT=active
            control=enrich(p.phase(client,"synthetic_background.json",p.SYNTHETIC,p.SYNTHETIC_ENTITIES,120),candidate)
            WRITE("synthetic.json",control)
            if control["contract10_success"] and control["validated_relation_count"]==1 and control["service_tier_verified"]:
                real=enrich(p.phase(client,"real_passage_background.json",text,entities,900),candidate)
            else:
                real["reason"]="Synthetic transport/schema/validation/tier control did not satisfy the contract"
            WRITE("real.json",real)
            row=dict(candidate=candidate,synthetic=control,real=real,terminal_experimental_state=True,
                classification="service_tier_mismatch" if control.get("service_tier_mismatch") or real.get("service_tier_mismatch") else real["status"])
            results.append(row)
            active=p.REPORT
            write("operations.json",results)
            write("run_state.json",dict(active_candidate=None,terminal_candidates=len(results),status="candidate_terminal"))
            p.REPORT=active
    p.write=WRITE
    finish(results,preflight)
    write("run_state.json",dict(active_candidate=None,terminal_candidates=len(results),status="complete"))


p.baseline=baseline
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--run",action="store_true")
    args=parser.parse_args()
    if args.prepare==args.run:
        parser.error("Choose exactly one of --prepare or --run")
    if args.prepare:
        prepared=prepare()
        print(json.dumps({"baseline":prepared["baseline"],"adapter_sha256":prepared["adapter_sha256"],
            "semantic_schema_sha256":prepared["semantic_schema_sha256"],"transport_schema_sha256":prepared["transport_schema_sha256"]}))
    else:
        run()
