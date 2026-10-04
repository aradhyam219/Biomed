"""Print complete evidence and rich fields for direct offline scientific review."""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
report = Path(__file__).resolve().parents[1]
manifest = json.loads((report / "frozen_set_manifest.json").read_text(encoding="utf-8"))
slug = sys.argv[1]
row = next(v for v in manifest["cases"] if v["slug"] == slug)
base = report / row["directory"] / slug
case = json.loads((base / "input.json").read_text(encoding="utf-8"))
labels = {v["id"]: v["text"] for v in case["entities"]}
print("SOURCE:", case["source_text"])
for mode in sys.argv[2:] or ["control", "failed_12b", "refined"]:
    path = base / f"{mode}.json"
    if not path.exists():
        continue
    packet = json.loads(path.read_text(encoding="utf-8"))
    relations = packet["control_relations"] if mode == "control" else packet.get("relations", [])
    print("\nMODE:", mode, "COUNT:", len(relations))
    for i, r in enumerate(relations):
        print(f"[{i}] {r['source']}({labels[r['source']]}) -> {r['target']}({labels[r['target']]}) {r['predicate']} negated={r['negated']}")
        print(json.dumps({k:r.get(k) for k in ("assertion", "intervention", "effects", "context", "evidence")}, ensure_ascii=True))
