"""Check source-only review provenance without reading model identities or output.

Reference claims are machine review aids. This check proves their quoted evidence
and candidate IDs occur in the frozen packet; it does not certify biomedical truth.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPORT = Path(__file__).resolve().parents[1]


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    paths = [REPORT / "review" / f"source_reference_{half}_four.json"
             for half in ("first", "last")]
    seen_papers: set[str] = set()
    seen_claims: set[str] = set()
    counts = {}
    packets = {read(path)["paper_id"]: read(path)
               for path in (REPORT / "inputs").glob("*.json")}
    aliases = {}
    for paper_id in packets:
        aliases[paper_id] = paper_id
        aliases[paper_id.replace(":", "")] = paper_id
        if paper_id.startswith("PMCID:"):
            aliases[paper_id.split(":", 1)[1]] = paper_id
    categories = ("clear_claims", "ambiguous_claims", "tentative_claims",
                  "excluded_study_aims_and_naming_constructions", "excluded_items")
    for path in paths:
        reference = read(path)
        assert reference["phase"] == "source_only_before_output_review"
        assert reference["reviewer_model"] == "gpt-6-luna"
        for paper in reference["papers"]:
            supplied_id = paper.get("paper_id") or "PMID:" + paper["pmid"]
            paper_id = aliases[supplied_id]
            assert paper_id not in seen_papers, paper_id
            seen_papers.add(paper_id)
            packet = packets[paper_id]
            entity_ids = {entity["id"] for entity in packet["entities"]}
            counts[paper_id] = {}
            for category in categories:
                claims = paper.get(category, [])
                counts[paper_id][category] = len(claims)
                for index, claim in enumerate(claims):
                    claim_id = claim.get("claim_id", claim.get("reference_id",
                                         f"{paper_id}/{category}/{index}"))
                    assert claim_id not in seen_claims, claim_id
                    seen_claims.add(claim_id)
                    evidence = claim["evidence"]
                    quotes = evidence if isinstance(evidence, list) else [evidence]
                    assert quotes and all(isinstance(quote, str) and quote and
                                          quote in packet["source_text"] for quote in quotes), claim_id
                    for field in ("source_entity_ids", "target_entity_ids", "related_entity_ids"):
                        if field in claim:
                            assert isinstance(claim[field], list), (claim_id, field)
                            assert set(claim[field]) <= entity_ids, (claim_id, field)
                    if category.endswith("claims"):
                        assert "claim_id" in claim, claim_id
                        assert "source_entity_ids" in claim and "target_entity_ids" in claim, claim_id
    expected = set(packets)
    assert seen_papers == expected, (seen_papers, expected)
    result = {
        "status": "passed",
        "scope": "Exact source quotes and candidate entity IDs; no semantic certification",
        "items_per_paper": counts,
        "total_review_items": len(seen_claims),
        "reference_file_sha256": {
            str(path.relative_to(REPORT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths
        },
    }
    target = REPORT / "review" / "source_reference_verification.json"
    if target.exists():
        raise RuntimeError("Do not overwrite a frozen reference verification")
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
