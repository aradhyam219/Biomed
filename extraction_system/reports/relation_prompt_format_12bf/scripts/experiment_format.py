"""One frozen formatting variant over the exact 12A/11U controls and inputs.

Reuse the preserved 12B background lifecycle, validation, and graph pipeline.
Only presentation changes; production and historical artifacts are hash guarded.
"""
from pathlib import Path
import argparse
import ast
import difflib
import re
import sys

REPORT = Path(__file__).resolve().parents[1]
ROOT = REPORT.parents[1]
HISTORY = ROOT / "reports/relation_prompt_refinement_12br"
sys.path.insert(0, str(ROOT / "reports/relation_prompt_refinement_12b/scripts"))
import experiment as e

START = "78b656011c8a6bf0231c57d121bc7ea4fd465b5a"
TAGS = ("grounding", "identity", "relation_semantics", "rich_relation_fields",
        "context_rules", "final_constraints")


def normalize(prompt):
    """Remove only the finite markup actually introduced, preserving punctuation."""
    prompt = re.sub(r"</?(?:" + "|".join(TAGS) + r")>", "", prompt)
    return " ".join(prompt.replace("**", "").split())


def format_prompt(control):
    """Insert tags and sparse emphasis without editing or reordering any wording."""
    groups = control.strip().split("\n\n")
    assert len(groups) == 6
    opening, grounding, identity, rich, context, final = groups
    # Sentence splitting here is safe: the dense opening contains no abbreviations.
    grounding = "\n".join("**" + sentence + "**" for sentence in
                          re.split(r"(?<=\.) ", grounding))
    boundary = "When an explicit manipulation, treatment,"
    semantics, rest = rich.split(boundary, 1)
    rest = boundary + rest
    emphasized = (
        "When an explicit manipulation, treatment,\nperturbation, or comparable condition materially changes the meaning, record it\nin intervention.",
        "Record explicit outcomes that would otherwise be lost from a\nbinary edge in effects, and explicit contextual qualifiers needed for\ninterpretation in context.",
        "Preserve intervention, effects, and context in the\nassertion when they are material.",
        "If another supplied entity participates in a\ndistinct explicitly asserted relationship, represent that relationship\nseparately when supported by the text.",
    )
    for sentence in emphasized:
        assert rest.count(sentence) == 1
        rest = rest.replace(sentence, "\n\n**" + sentence + "**\n\n")
    sections = (("grounding", grounding), ("identity", identity),
                ("relation_semantics", semantics.strip()), ("rich_relation_fields", rest.strip()),
                ("context_rules", context), ("final_constraints", final))
    return opening + "\n\n" + "\n\n".join(
        f"<{tag}>\n{text}\n</{tag}>" for tag, text in sections) + "\n"


def freeze():
    """Prove control provenance and exact wording equivalence before live execution."""
    if (REPORT / "frozen_set_manifest.json").exists():
        raise RuntimeError("Refusing to overwrite the experiment freeze")
    assert e.git("rev-parse", "HEAD") == e.git("rev-parse", "origin/extraction_system_v2") == START
    assert e.git("branch", "--show-current") == "extraction_system_v2"
    e.REPORT = HISTORY
    old = e.verify_freeze()
    e.previous._runtime_semantic_controls(e.previous._verify_frozen_inputs())
    source = e.git("show", START + ":extraction_system/src/biomedical_extractor/llm_relation_extraction.py")
    assignment = next(n for n in ast.parse(source).body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == "RELATION_EXTRACTION_SYSTEM_PROMPT" for t in n.targets))
    control = ast.literal_eval(assignment.value)
    assert control == e.RELATION_EXTRACTION_SYSTEM_PROMPT
    assert control == (HISTORY / "prompt_control.txt").read_text(encoding="utf-8")
    formatted = format_prompt(control)
    assert normalize(control) == normalize(formatted)
    e.REPORT = REPORT
    e.START_SHA = START
    for name, value in (("control", control), ("formatted", formatted), ("refined", formatted)):
        (REPORT / f"prompt_{name}.txt").write_text(value, encoding="utf-8", newline="\n")
    (REPORT / "prompt_format_diff.txt").write_text("".join(difflib.unified_diff(
        control.splitlines(keepends=True), formatted.splitlines(keepends=True),
        fromfile="control", tofile="formatted")), encoding="utf-8", newline="\n")
    e.write(REPORT / "prompt_equivalence.json", dict(passed=True,
        method="Remove only six approved XML tag pairs and inserted **; normalize whitespace; compare full sequence including all substantive punctuation",
        approved_tags=list(TAGS), same_words=True, same_order=True, same_sentences=True,
        substantive_punctuation_preserved=True, normalized_sha256=e.sha(normalize(control).encode()),
        control_sha256=e.sha(control.encode()), formatted_sha256=e.sha(formatted.encode()),
        authoritative_start_sha=START, prompt_refined_is_harness_alias=True))
    rows = []
    for row in old["cases"]:
        original = HISTORY / row["directory"] / row["slug"]
        case, saved = e.read(original / "input.json"), e.read(original / "control.json")
        # Independently verify the preserved control output against its original source.
        packet = e.read(ROOT / saved["control_path"])
        relations = packet.get("candidate_relations", packet.get("validated_relations"))
        assert relations == saved["control_relations"]
        graph = e.replay(case, relations)
        assert graph == e.read(HISTORY / "graphs/control" / f"{row['slug']}.json")
        for predecessor in ("relation_prompt_refinement_12b", "relation_prompt_refinement_12br"):
            prior = ROOT / "reports" / predecessor / row["directory"] / row["slug"]
            assert e.read(prior / "input.json") == case
        base = REPORT / "cases" / row["slug"]
        e.write(base / "input.json", case)
        e.write(base / "control.json", saved)
        e.write(REPORT / "graphs/control" / f"{row['slug']}.json", graph)
        entities = tuple(e.Entity(**v) for v in case["entities"])
        assert e.sha(e._build_prompt(case["source_text"], entities, control).encode()) == row["control_request_sha256"]
        rows.append({**row, "directory": "cases", "refined_request_sha256":
                     e.sha(e._build_prompt(case["source_text"], entities, formatted).encode())})
    assert len(rows) == 5
    protected = {p.relative_to(ROOT).as_posix():e.sha(p.read_bytes())
        for directory in ("src", "viewer") for p in (ROOT / directory).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts}
    dependencies = {p.relative_to(ROOT).as_posix():e.sha(p.read_bytes())
        for directory in ("relation_migration_12a", "model_selection_11u", "relation_prompt_refinement_12b", "relation_prompt_refinement_12br")
        for p in (ROOT / "reports" / directory).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts}
    frozen = {p.relative_to(ROOT).as_posix():e.sha(p.read_bytes()) for p in REPORT.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts}
    manifest = dict(contract="12B-F", starting_sha=START, remote_baseline_sha=START,
        frozen_at_utc=e.previous._utc_now(), cases=rows, configuration=old["configuration"],
        production_defaults=old["production_defaults"], prompt_control_sha256=e.sha(control.encode()),
        prompt_refined_sha256=e.sha(formatted.encode()), prompt_formatted_sha256=e.sha(formatted.encode()),
        control_equivalence_established=True, control_reruns_required=False,
        five_inputs_identical_to_12b_and_12br=True, transport_equivalence=old["transport_equivalence"],
        protected_files=protected, dependencies=dependencies, frozen_files=frozen)
    e.write(REPORT / "frozen_set_manifest.json", manifest)
    e.verify_freeze()
    print("Frozen one lexically equivalent formatting variant and five exact inputs; no control reruns.")


if __name__ == "__main__":
    mode = argparse.ArgumentParser(description=__doc__)
    mode.add_argument("mode", choices=("freeze", "run", "compare", "verify"))
    action = mode.parse_args().mode
    e.REPORT, e.START_SHA = REPORT, START
    {"freeze":freeze, "run":e.run, "compare":e.compare, "verify":e.verify_freeze}[action]()
