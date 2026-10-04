"""Run Contract 12B-R using the preserved 12B lifecycle, replacing its amendment.

Only this report's prompt and artifacts vary. Frozen inputs, semantic contract,
graph composition, configuration, repair budget and submission guards are reused.
No production defaults or historical experiment files are changed.
"""
from pathlib import Path
import argparse
import sys

REPORT = Path(__file__).resolve().parents[1]
ROOT = REPORT.parents[1]
HISTORY = ROOT / "reports/relation_prompt_refinement_12b"
sys.path.insert(0, str(HISTORY / "scripts"))
import experiment as e

e.REPORT = REPORT
e.START_SHA = "f92ce7e91b62ed069c4479f75a0820ae24d0848f"


def freeze():
    """Prove five-case equivalence and freeze the replacement before submission."""
    if (REPORT / "frozen_set_manifest.json").exists():
        raise RuntimeError("Refusing to overwrite the experiment freeze")
    (REPORT / "prompt_12b_failed.txt").write_bytes((HISTORY / "prompt_refined.txt").read_bytes())
    e.freeze()
    manifest = e.read(REPORT / "frozen_set_manifest.json")
    assert (REPORT / "prompt_control.txt").read_bytes() == (HISTORY / "prompt_control.txt").read_bytes()
    for row in manifest["cases"]:
        base = REPORT / row["directory"] / row["slug"]
        old = HISTORY / row["directory"] / row["slug"]
        case = e.read(base / "input.json")
        assert case == e.read(old / "input.json")
        assert e.read(base / "control.json") == e.read(old / "control.json")
        output = old / "refined_retry_01.json"
        if not output.exists():
            output = old / "refined.json"
        assert e.read(output)["status"] == "success"
        e.write(base / "failed_12b.json", e.read(output))
        row["failed_12b_output_path"] = output.relative_to(ROOT).as_posix()
    # Preserve every historical artifact as well as production code and viewer.
    manifest["dependencies"].update({p.relative_to(ROOT).as_posix(): e.sha(p.read_bytes())
        for p in HISTORY.rglob("*") if p.is_file() and "__pycache__" not in p.parts})
    manifest["frozen_files"] = {p.relative_to(ROOT).as_posix(): e.sha(p.read_bytes())
        for p in REPORT.rglob("*") if p.is_file() and "__pycache__" not in p.parts
        and p.name != "frozen_set_manifest.json"}
    manifest.update(contract="12B-R", five_inputs_identical_to_12b=True,
                    failed_amendment_stacked=False, remote_baseline_sha=e.START_SHA)
    e.write(REPORT / "frozen_set_manifest.json", manifest)
    e.verify_freeze()
    print("12B-R replacement and historical dependencies frozen; five exact inputs.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("freeze", "run", "compare", "verify"))
    mode = parser.parse_args().mode
    {"freeze": freeze, "run": e.run, "compare": e.compare, "verify": e.verify_freeze}[mode]()
