"""User-authorized extra xhigh run, separate from the frozen three-candidate trial."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
REPORT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("trial",ROOT/"reports/model_selection_11u/scripts/run_trial.py")
trial=importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)
trial.REPORT=REPORT
trial.CANDIDATES=[dict(number=1,directory="gpt_61_sol_xhigh_standard",model="gpt-6.1-sol",effort="xhigh",tier="default",
    rates=dict(input=2.00,cached=0.10,cache_write=2.50,output=10.00))]
original_prepare=trial.prepare


def prepare():
    preflight=original_prepare()
    preflight.update(contract="supplemental GPT-6.1 Sol xhigh",purpose="User-requested additional run; outside frozen Contract 11U",
                     compared_configuration="11U Candidate 2 Standard/medium; only reasoning changed to xhigh")
    trial.write("preflight.json",preflight)
    return preflight


def finish(results,preflight,interruption=None):
    state=trial.baseline()
    preserved=trial.existing_reports()==preflight["existing_report_hashes"]
    if not preserved:
        raise RuntimeError("Existing reports changed")
    assert len(results)==1
    row=results[0]
    synthetic=trial.costs(row["synthetic"],row["candidate"])
    real=trial.costs(row["real"],row["candidate"])
    requests=synthetic+real
    complete=all(r["estimated_request_cost_usd"] is not None for r in requests)
    cost=dict(currency="USD",estimated_not_invoice=True,synthetic_requests=synthetic,real_requests=real,
        total_cost_usd=sum(r["estimated_request_cost_usd"] for r in requests) if complete else None,
        cost_complete=complete)
    trial.write("operations.json",results)
    trial.write("costs.json",cost)
    summary=dict(execution_complete=True,configuration=row["candidate"],synthetic=row["synthetic"],real=row["real"],
        costs=cost,production_code_unchanged=True,production_default_unchanged=True,
        existing_reports_preserved=preserved,nothing_committed_or_pushed=True,final_baseline=state)
    trial.write("summary.json",summary)
    g=row["real"].get("generations",[])
    primary=g[0] if g else {}
    report=["# Supplemental GPT-6.1 Sol xhigh Standard", "", "Separate from the frozen Contract 11U trial.", "",
        "Synthetic: "+row["synthetic"]["status"], "Real passage: "+row["real"]["status"],
        "Response ID: "+str(primary.get("response_id")),
        "Create latency (s): "+str(primary.get("initial_create_latency_seconds")),
        "Background elapsed (s): "+str(primary.get("background_elapsed_seconds")),
        "Total phase elapsed (s): "+str(row["real"].get("total_elapsed_seconds")),
        "Repairs: "+str(row["real"].get("repair_count",0)),
        "Validated relations: "+str(row["real"].get("validated_relation_count")),
        "Estimated total cost (USD): "+str(cost["total_cost_usd"]), "",
        "Production code and default unchanged. All existing reports preserved. Nothing committed or pushed.",
        "No scientific-quality judgment made."]
    (REPORT/"summary.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    print(json.dumps({"execution_complete":True,"real_status":row["real"]["status"]}))


trial.prepare=prepare
trial.finish=finish
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--prepare",action="store_true")
    parser.add_argument("--run",action="store_true")
    args=parser.parse_args()
    if args.prepare==args.run:
        parser.error("Choose exactly one of --prepare or --run")
    if args.prepare:
        pre=prepare()
        print(json.dumps({"baseline":pre["baseline"],"configuration":trial.CANDIDATES[0],
                          "semantic_schema_sha256":pre["semantic_schema_sha256"],"transport_schema_sha256":pre["transport_schema_sha256"]}))
    else:
        trial.run()
