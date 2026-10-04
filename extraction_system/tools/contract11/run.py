"""Portable entry point for the preserved Contract 11 benchmark infrastructure.

Runs write to a fresh reports directory. Provider lifecycle and biomedical
semantics are reused from the frozen 11S-R/11U code, without production changes.
"""
import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("contract11_trial",ROOT/"reports/model_selection_11u/scripts/run_trial.py")
trial=importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)
ORIGINAL_PREPARE=trial.prepare
ORIGINAL_FINISH=trial.finish


def prepare():
    # Preservation commits also add tooling/docs. Production parity, rather than
    # the historical reports-only HEAD gate, protects this new benchmark run.
    trial.p.AUTHORIZED_HEAD=trial.p.git("rev-parse","HEAD")
    value=ORIGINAL_PREPARE()
    value["baseline"]["baseline_exception"]="Current HEAD accepted after exact protected Contract 10 production parity check"
    value.update(contract="new Contract 11 benchmark rerun",historical_records_overwritten=False)
    trial.write("preflight.json",value)
    return value


def finish(results,preflight,interruption=None):
    with redirect_stdout(io.StringIO()):
        ORIGINAL_FINISH(results,preflight,interruption)
    path=trial.REPORT/"summary.json"
    summary=json.loads(path.read_text())
    summary.update(contract="new Contract 11 benchmark rerun",execution_complete=len(results)==len(trial.CANDIDATES) and not interruption)
    trial.write("summary.json",summary)
    (trial.REPORT/"summary.md").write_text("# New Contract 11 benchmark rerun\n\n"+
        json.dumps(summary,indent=2)+"\n\nHistorical 11U and supplemental D records were not overwritten.\n",encoding="utf-8")
    print(json.dumps({"execution_complete":summary["execution_complete"],"candidate_terminal":summary["candidate_terminal"]}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True,help="Fresh report directory within this checkout")
    parser.add_argument("--candidate",choices=["11u","61-medium-standard","61-xhigh-standard"],default="11u")
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare",action="store_true",help="Offline preparation only; no provider calls")
    action.add_argument("--run",action="store_true",help="Explicitly execute paid provider calls")
    args=parser.parse_args()
    output=args.output.resolve()
    reports=(ROOT/"reports").resolve()
    if output.parent!=reports:
        parser.error("--output must be a new direct child of reports/")
    protected={path.name for path in reports.iterdir() if path.is_dir() and path!=output}
    if output.name in protected or output.exists():
        parser.error("--output already exists; choose a fresh directory")
    trial.REPORT=output
    if args.candidate!="11u":
        candidate=dict(trial.CANDIDATES[1])
        if args.candidate=="61-xhigh-standard":
            candidate.update(effort="xhigh",directory="gpt_61_sol_xhigh_standard")
        candidate["number"]=1
        trial.CANDIDATES=[candidate]
    trial.prepare=prepare
    trial.finish=finish
    if args.prepare:
        value=prepare()
        print(json.dumps({"output":str(output),"semantic_schema_sha256":value["semantic_schema_sha256"],
                          "transport_schema_sha256":value["transport_schema_sha256"],"provider_calls":0}))
    else:
        trial.run()


if __name__=="__main__":
    main()
