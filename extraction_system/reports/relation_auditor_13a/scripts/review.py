"""Preserve post-generation scientific classifications and hypothetical deltas.

Judgments below are a manual source comparison, not another inference pass or
gold annotation. Rejected proposals remain intact. No production set is built.
"""
import copy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import auditor as a

VALID = "VALID MATERIAL OMISSION"
REDUNDANT = "REDUNDANT / ALREADY REPRESENTED"
WRONG_ENDPOINT = "WRONG ENDPOINT"
DECISION = "SECOND-PASS AUDITOR FAILED — PRESERVE SINGLE-PASS PRODUCTION"

MISSING = {
    "pmcid_pmc11824863": [],
    "pmcid_pmc8605525": [
        (REDUNDANT, "Pass-1 P1R021 already states STAT4 improved Runx3 expression by regulating histone H3 lysine 4 trimethylation. Recasting its explicit mechanism as a STAT4-to-H3K4me3 edge changes granularity, not the represented scientific information. The Runx3 outcome also already exists in P1R021."),
        (VALID, "The source explicitly coordinates JAK2 and STAT4 overexpression as increasing HUVEC apoptosis and abrogating Cb1's endothelial effect. Pass 1 represents only the Runx3 alternative (P1R022); this JAK2-to-Cb1 assertion is absent. Joint intervention is preserved; no claim of independent JAK2 manipulation is added."),
        (VALID, "The same explicit coordinated overexpression statement supports the STAT4-to-Cb1 reversal assertion absent from Pass 1. Both proposed edges preserve the joint JAK2/STAT4 intervention and the HUVEC apoptosis outcome."),
    ],
    "pmid_27172794": [
        (WRONG_ENDPOINT, "The causal subject in the evidence is colorectal cancer stem-like cells, not generic colorectal cancer. E5 is the Disease mention 'colorectal cancer'; selecting it as source attributes a cell-subpopulation prognosis claim to the disease. Supplied CCS mentions exist (E20/E40). The full assertion preserves the subgroup in prose but does not fix the source endpoint. The existing EZH2 prognosis relation P1R006 has a different scientific subject and is not the reason for rejection."),
    ],
    "pmid_33652126": [
        (VALID, "The exact observation says serum deprivation in H9c2 cells increased PTEN expression; no Pass-1 assertion includes it. E28 is the supplied 'serum deficiency' condition later in the same abstract, referring to the same deprivation experiment; E19 is PTEN in the observation. This is an explicitly asserted condition-to-gene effect, not mere setting coexistence, and is not a PTEN self-edge."),
    ],
    "contract11u_passage_001": [
        (VALID, "The source explicitly reports the AST/ALT ratio of approximately 1 versus approximately 2 in the two named mouse groups. Pass 1 represents plasma AST, ALT comparability and suggested liver damage, but none of its assertions preserves these ratio values. AST and ALT are supplied endpoints; no process node or extra causal claim is introduced."),
    ],
}

# One entry per value, in field order intervention, effects, context. Scientific
# support, missingness and admission are separate dimensions in the artifact.
PATCHES = {
    "pmcid_pmc11824863": {
        "P1R010": [
            (True, "The contiguous results paragraph attributes the coordinated Bcl-2/Bax ratio increase to the SFPQ overexpression experiment. The baseline ratio assertion has no intervention. This preserves the experiment on the ratio, without asserting separate marginal changes in Bcl-2 or Bax."),
            (True, "AD mice is the local results setting for the ratio finding and is absent from this relation's assertion and rich fields."),
        ],
        "P1R011": [(True, "The ratio sentence explicitly says the elevated phosphorylation ratios indicate PI3K/AKT pathway activation. Pass 1 states the ratio change but omits that interpretive outcome. Both pathway components already have separate Pass-1 relations, so no absent component interaction is concealed.")],
        "P1R012": [(True, "The same locally explicit activation interpretation applies to the coordinated AKT ratio finding and is absent from this relation. The related PI3K component already has its own Pass-1 relation.")],
    },
    "pmcid_pmc8605525": {
        "P1R012": [(True, "The support explicitly says Cbl was reduced in both DM rat tissues and HG-induced HUVECs. The baseline captures only rat tissue; the new value adds the parallel in-vitro setting of the same expression observation without a glucose-to-Cbl causal edge.")],
        "P1R013": [(True, "The coordinated 'where JAK2, Runx3 and STAT4 were elevated' clause covers DM rat tissues and HG-induced HUVECs. JAK2's baseline has only rat-tissue context; this adds the explicit second setting, not causality.")],
        "P1R014": [(True, "Runx3 is explicitly coordinated in the same dual-setting expression observation. HG-induced HUVECs is absent from the baseline rat-tissue relation; no setting-to-gene causal claim is added.")],
        "P1R015": [(True, "STAT4 is explicitly coordinated in the same dual-setting expression observation. The second source-supported expression setting is omitted from Pass 1; the patch changes no endpoint or causal predicate.")],
    },
    "pmid_27172794": {},
    "pmid_33652126": {
        "P1R004": [(True, "The adjacent results sentences explicitly locate the PTEN-knockdown experiment in H9c2 cells. This adds cellular context to the baseline PTEN-to-ROS relation, whose rich context contains only serum deprivation.")],
        "P1R005": [
            (False, "The outcomes are verbatim-supported and the PI3K-inhibitor reversal assignment is correct, but ROS is a supplied entity (E21). Reversal of the PTEN-knockdown-associated ROS reduction is a distinct explicit PI3K-to-ROS assertion absent from Pass 1; hiding it in a PI3K-to-PTEN effects patch violates the audit's third-entity constraint. Preserve as rejected, not an applied field gain."),
            (True, "The local results chain identifies H9c2 as the cellular model for the PTEN knockdown and PI3K-inhibitor reversal; this context is absent from P1R005."),
        ],
    },
    "contract11u_passage_001": {
        "P1R006": [(True, "The immediately preceding investigation sentence explicitly sets the lipid-droplet comparison in the liver under a hyperglycemic state; this setting is absent from the baseline relation.")],
        "P1R007": [(True, "The same local liver/hyperglycemia setting applies to the coordinated inflammatory-infiltration comparison and is omitted from its baseline relation.")],
        "P1R008": [(True, "The source explicitly names PAS and Oil Red O staining for the glycogen finding. Pass 1 says only 'Staining revealed'; this adds the omitted measurement method, not a chemical-to-glycogen causal interaction.")],
        "P1R009": [(True, "The same staining sentence supports the lipid-uptake finding. Naming both methods is source-supported additional measurement context; no distinct causal interaction is hidden." )],
    },
}


def build():
    """Serialize judgments, value-level counts and proposed-only field deltas."""
    a.verify()
    review = dict(contract="13A", judgment=DECISION,
        review_method="Manual comparison of every proposal with frozen source, supplied entities, all Pass-1 assertions and rich fields; no reviewer LLM call",
        limitation="One frozen generation per case; classifications are review judgments, not independently annotated gold. Local structural validity does not establish scientific correctness.",
        rejection_reason="Four of six missing proposals are admissible. One merely recasts an already represented mechanism; one misattributes a cell-subpopulation prognosis assertion to a generic disease endpoint. One of fifteen rich values hides a distinct supplied ROS interaction. These are material precision/topology-contract failures despite useful target recovery and no causal inflation.",
        cases={})
    telemetry = a.read(a.REPORT / "telemetry.json")
    totals = dict(input_tokens=0, output_tokens=0, reasoning_tokens=0, latency_seconds=0.0,
                  scientific_generations=5, repairs=0, poll_count=0, poll_errors=0,
                  cost=None, cost_reason="Existing experiment tooling provides no reliable price or billed cost for this model; token totals are observed and cost is unavailable.")
    for slug in a.SLUGS:
        case = a.read(a.REPORT / "inputs" / f"{slug}.json")
        output = a.read(a.REPORT / "audit_outputs" / slug / "validated.json")
        missing = []
        assert len(MISSING[slug]) == len(output["missing_relations"])
        for index, (proposal, (classification, reason)) in enumerate(zip(output["missing_relations"], MISSING[slug]), 1):
            missing.append(dict(proposal_index=index, classification=classification,
                                justification=reason, proposal=proposal))
        rich = []
        deltas = []
        counts = {field: dict(proposed=0, supported=0, genuinely_missing=0, valid=0,
            redundant=0, unsupported=0, wrong_relation=0, hidden_supplied_entity=0)
            for field in ("intervention", "effects", "context")}
        for patch in output["enrichment_patches"]:
            ref = patch["relation_ref"]
            original = next(r for r in case["pass1_relations"] if r["relation_ref"] == ref)
            judgments = iter(PATCHES[slug][ref])
            accepted_fields = {}
            for field in counts:
                accepted_fields[field] = []
                for index, item in enumerate(patch[field]):
                    accepted, reason = next(judgments)
                    counts[field]["proposed"] += 1
                    counts[field]["supported"] += 1
                    counts[field]["genuinely_missing"] += 1
                    counts[field]["valid"] += int(accepted)
                    counts[field]["hidden_supplied_entity"] += int(not accepted)
                    rich.append(dict(relation_ref=ref, field=field, value_index=index,
                        **item, scientifically_supported=True, genuinely_missing=True,
                        redundant=False, unsupported=False, wrong_relation=False,
                        hidden_supplied_entity=not accepted, admissible=accepted,
                        classification="VALID ENRICHMENT" if accepted else "HIDDEN SUPPLIED ENTITY",
                        justification=reason))
                    if accepted:
                        accepted_fields[field].append(item["value"])
            assert next(judgments, None) is None
            # Keep additions separate for scalar intervention: no fabricated
            # replacement string or production-style merge is constructed.
            deltas.append(dict(relation_ref=ref,
                before={field: copy.deepcopy(original[field]) for field in counts},
                hypothetical_admissible_additions=accepted_fields,
                protected_fields={field: original[field] for field in ("source", "target", "predicate", "negated")},
                applied=False))
        row = telemetry[slug]
        for generation in row:
            for field in ("input_tokens", "output_tokens", "reasoning_tokens", "poll_count", "poll_errors"):
                totals[field] += generation[field]
            totals["latency_seconds"] += generation["elapsed_seconds"]
            totals["repairs"] += int(generation["repair"])
        entry = dict(paper_id=case["paper_id"], missing_relations=missing,
            enrichment_values=rich, richness_counts=counts,
            counts=dict(missing_proposed=len(missing), valid_material_omissions=sum(r["classification"] == VALID for r in missing),
                redundant=sum(r["classification"] == REDUNDANT for r in missing),
                unsupported=0, wrong_endpoint=sum(r["classification"] == WRONG_ENDPOINT for r in missing),
                wrong_direction=0, causal_overreach=0, alias_identity_only=0, other_error=0,
                enrichment_patches_proposed=len(output["enrichment_patches"]),
                enrichment_values_proposed=len(rich), valid_enrichment_values=sum(r["admissible"] for r in rich),
                invalid_enrichment_values=sum(not r["admissible"] for r in rich)),
            latency_seconds=round(sum(g["elapsed_seconds"] for g in row), 3),
            tokens={k: sum(g[k] for g in row) for k in ("input_tokens", "output_tokens", "reasoning_tokens")},
            repairs=sum(bool(g["repair"]) for g in row),
            hypothetical_delta=dict(missing_relations=[r["proposal"] for r in missing if r["classification"] == VALID],
                rich_field_additions=deltas, applied=False))
        review["cases"][slug] = entry
        a.write(a.REPORT / "audit_outputs" / slug / "review.json", entry)
        a.write(a.REPORT / "audit_outputs" / slug / "hypothetical_delta.json", entry["hypothetical_delta"])
    totals["latency_seconds"] = round(totals["latency_seconds"], 3)
    review["operational_totals"] = totals
    review["target_findings"] = dict(
        jak2_overexpression_reversal="Recovered with joint JAK2/STAT4 intervention",
        stat4_overexpression_reversal="Recovered with joint JAK2/STAT4 intervention",
        coordinated_apoptosis_reversal="Recovered for both JAK2 and STAT4; Runx3 already represented",
        pten_increased_expression="Recovered, using supplied serum-deficiency condition E28; no PTEN self-edge",
        cbl_dual_context="Four valid HG-induced-HUVEC context additions complement existing DM-rat expression context",
        sfpq="Cognition/memory already present; no new relation required. Four valid rich values: ratio intervention/setting and two pathway-activation interpretations",
        ezh2="EZH2 poor prognosis, tumor initiation and pathway-maintenance findings already present. New background cell-prognosis proposal rejected for disease-source endpoint",
        passage_11u="Valid AST/ALT numerical comparison and four measurement/liver context additions. Plasma/timing already present and no redundant additions proposed",
        glucose_context_causal_inflation=False, other_unsupported_causal_edges=False,
        production_merge=False)
    a.write(a.REPORT / "scientific_review.json", review)
    a.write(a.REPORT / "operational_totals.json", totals)
    print(totals)


if __name__ == "__main__":
    build()
