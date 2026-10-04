"""Preserve primary-agent judgments made against every saved relation/evidence.

These annotations are review data, never model instructions or automatic gold.
Indices refer to unchanged normalized output arrays; source text is frozen.
"""
import json
from pathlib import Path

REPORT = Path(__file__).resolve().parents[1]
GATE = "FORMATTING EXPERIMENT FAILED — PRESERVE 12A CONTROL PROMPT"

CASES = {
    "pmcid_pmc11824863": {
        "valid_matched_pairs": [[0,0],[1,1],[2,2],[4,3],[5,4],[6,5],[7,8],[8,9],[9,10],[10,11],[11,12],[12,13]],
        "losses": ["Control [3] AAV administration to overexpress SFPQ in the hippocampus of AD mice is omitted; cognition/memory [4] is retained as formatted [3]."],
        "gains": ["Explicit effects populated for APP/Tau, GST/HO-1, Bcl-2:Bax, and PI3K/AKT ratios.", "Two grounded APP/Tau marker-of-AD relations [6,7]."],
        "flags": [],
        "notes": [
            "Disease classification is explicit; multifaceted pathogenesis detail is shortened.",
            "Role, antioxidant functions, and brain-neuron gene regulation are explicit in evidence.",
            "Injection intervention, mouse context, and model establishment outcome are explicit and belong to amyloid-beta-to-AD model edge.",
            "Overexpression, mice context, recognition and memory effects are explicit; disease endpoint supplies AD. Cognition/memory retained.",
            "SFPQ intervention, AD-mice setting, and reduced APP outcome are explicit in the same sentence; no new causal claim.",
            "SFPQ intervention, AD-mice setting, and reduced Tau outcome are explicit in the same sentence.",
            "APP marker-of-AD classification is explicit; no invented intervention or outcome.",
            "Tau marker-of-AD classification is explicit; no invented intervention or outcome.",
            "The contiguous results sentences connect SFPQ overexpression in AD mice to GST upregulation; all fields remain within that experimental finding.",
            "The contiguous results sentences connect SFPQ overexpression in AD mice to HO-1 upregulation; all fields remain within that experimental finding.",
            "Increased Bcl-2:Bax ratio is explicit. Effect restates that ratio; no SFPQ causality added on this edge.",
            "Full contiguous results block supports SFPQ intervention, AD-mice context, and increased p-PI3K/PI3K ratio; evidence includes both subject setup and outcome.",
            "Full contiguous results block supports SFPQ intervention, AD-mice context, and increased p-AKT/AKT ratio; no inferred mechanism beyond reported result.",
            "Potential therapeutic-target status and prevention/treatment remain qualified in assertion and predicate."
        ]
    },
    "pmcid_pmc8605525": {
        "valid_matched_pairs": [[3,16],[7,1],[9,2],[10,3],[12,4],[13,5],[14,6],[15,7],[16,8],[17,9],[18,10],[19,11],[23,13],[24,14],[25,15]],
        "excluded_matches": [{"control":8,"formatted":0,"reason":"Predicate loses appears-to qualification; assertion retains it."},{"control":20,"formatted":12,"reason":"Runx3 expression finding retained but explicit H3 trimethylation mechanism is lost."}],
        "losses": ["JAK2/STAT4 joint overexpression and Runx3 overexpression apoptosis/reversal findings all missing; Runx3 control [21] lost.", "Control [11] decreased Cbl expression in DM tissues omitted; [12-14] elevated JAK2/Runx3/STAT4 remain.", "HG-induced HUVEC setting is absent from all three surviving expression assertions/context; no dual-setting recovery.", "Title Cbl inhibition of Runx3-mediated H3K4me3 omitted; title overexpression-specific JAK2/STAT4 signaling context omitted although conclusion inactivation remains.", "DM chronic-disease classification and impaired endothelial-function relation omitted.", "STAT4-to-Runx3 H3 trimethylation mechanism omitted from assertion [12]."],
        "gains": [],
        "flags": [{"index":0,"kind":"predicate_qualification_loss","detail":"alleviates drops appears-to; assertion still says appears."}],
        "notes": [
            "Evidence/assertion preserve appears-to alleviate; predicate loses uncertainty, a graph-facing qualification regression. No unsupported rich field.",
            "DM impaired nitric oxide bioavailability is explicit; no causal strengthening or added fields.",
            "Streptozotocin intraperitoneal injection and rat-model context are explicit; model induction is a supported experimental edge.",
            "High-glucose culture induces an in-vitro DM model in HUVECs, explicitly stated. This edge is supported; it is not a glucose-to-gene-expression claim.",
            "Elevated JAK2 in DM rat tissues is explicit; rat context belongs to the observation, but HG-HUVEC coverage is lost.",
            "Elevated Runx3 in DM rat tissues is explicit; rat context belongs to the observation, but HG-HUVEC coverage is lost.",
            "Elevated STAT4 in DM rat tissues is explicit; rat context belongs to the observation, but HG-HUVEC coverage is lost.",
            "Cbl overexpression, endothelial dysfunction alleviation, restored vasodilation, and HUVEC apoptosis suppression are all in the evidence; outcomes belong to this intervention edge.",
            "Cbl overexpression increasing NO production is explicit and intervention is edge-specific.",
            "Cb1 enhancing JAK2 ubiquitination is explicit; no unsupported metadata.",
            "Cb1 decreasing JAK2 expression is explicit; no context causality is invented.",
            "Cb1 decreasing STAT4 expression is explicit; no context causality is invented.",
            "STAT4 increasing Runx3 expression is explicit, but histone trimethylation explanatory detail is omitted.",
            "Cbl inactivation of JAK2/STAT4 pathway in DM is explicit; DM context is an explicit disease setting.",
            "Cbl inactivation of JAK2/STAT4 pathway in DM is explicit; split STAT4 endpoint retains pathway assertion.",
            "Cbl inhibition of Runx3 expression in DM is explicit; this is not the lost Runx3 overexpression reversal finding.",
            "Runx3-mediated H3K4me3 is explicit in title; no new qualifier or unsupported intervention."
        ]
    },
    "pmid_27172794": {
        "valid_matched_pairs": [[0,0],[1,1],[2,2],[3,3],[4,4],[5,5],[6,6],[7,7],[9,8],[10,9],[12,10],[13,11],[17,14],[18,15],[19,16]],
        "losses": ["Control [11] knockdown impairment of tumor-initiating capacity in re-implantation mouse model omitted; mammosphere/self-renewal outcomes are not recovered.", "Maintenance effects empty on matched pathway relations control [12,13] to formatted [10,11]; maintenance remains in assertions.", "Control [14-16] p21 requirement for EZH2 and EZH2-to-Wnt/beta-catenin conditional activation topology replaced by p21-to-Wnt/beta-catenin [12,13].", "Inverse non-CCS comparison control [8] not emitted separately; comparative meaning is retained in [7], not scored as a material loss."],
        "gains": ["Poor prognosis retained in [5] and additionally recorded as an observed effects value.", "Title expansion effects [0] and final maintenance effects [16] populated; context added to tumor high expression [4] and CCS expression [7]."],
        "flags": [{"indices":[12,13],"kind":"changed_conditional_requirement_topology","detail":"Assertion preserves EZH2 dependence but endpoints replace EZH2 with Wnt/beta-catenin. Not treated as equivalent to control or credited as new clean coverage."}],
        "notes": [
            "Stem-like-cell expansion and pathway mechanism are explicit in title; effect belongs to EZH2-to-CRC expansion edge.",
            "EZH2 activation of compound p21cip1-Wnt/beta-catenin signaling is explicit; supplied compound endpoint is unchanged.",
            "Beta-catenin activation is retained as part of the explicitly named pathway; assertion does not claim isolated activation.",
            "High expression in advanced-stage CRC patients is explicit; long-name EZH2 endpoint is source-explicit and assembly-compatible. Context is not a causal edge.",
            "Tumor tissue high expression and tumor-tissue setting are explicit; no new causality.",
            "Poor prognosis is an explicitly correlated observed outcome; assertion and associated-with predicate preserve correlation, not causation. Effect belongs to this prognosis edge.",
            "EZH2 silencing and reduced CRC proliferation are explicit; intervention and effect match the edge.",
            "Higher EZH2 in CCS-like vs non-CCS-like cells is explicit; CCS context belongs to expression comparison.",
            "EZH2 knockdown reduces the jointly CD133+/CD44+ positive population; assertion/effects preserve joint positivity rather than independent CD133 biology.",
            "EZH2 knockdown reduces the jointly CD133+/CD44+ positive population; split CD44 endpoint retains the same joint qualification.",
            "EZH2 pathway activation, CCS maintenance, TCGA 433-human-CRC dataset and in-vitro settings are explicit in one sentence. Context is supported; maintenance effects are lost.",
            "Same explicit pathway and experimental setting for beta-catenin endpoint; maintenance effects are lost although assertion preserves them.",
            "p21-mediated G1/S arrest requirement is explicit but concerns EZH2 activation of Wnt pathway. Changed conditional requirement endpoints hide EZH2 dependence in assertion; topology flagged, no rich additions.",
            "p21-mediated G1/S arrest requirement is explicit but concerns EZH2 activation of beta-catenin pathway. Changed conditional endpoints are flagged and excluded from matched-finding gains.",
            "Specific EPZ-6438 inhibition of EZH2 is explicit; no unsupported qualifiers.",
            "EPZ-6438 prevention of CRC progression is explicit; treatment intervention is supported by drug action and effect belongs to this edge. Clinical-trial descriptor stays in assertion, not context causality.",
            "EZH2 maintaining CCS characteristics by G1/S arrest is explicit; new maintenance effect directly belongs to this edge."
        ]
    },
    "pmid_33652126": {
        "valid_matched_pairs": [[0,0],[1,1],[2,2],[3,3]],
        "losses": ["Required serum-deprivation-in-H9c2 increased PTEN expression finding remains absent; valid H9c2/PTEN supplied endpoints exist.", "Control [4] PI3K inhibitor reversal of PTEN-knockdown effects omitted.", "Control [5,6] PI3K/AKT possible critical components of PTEN effects omitted."],
        "gains": [],
        "flags": [],
        "notes": [
            "PTEN mediation of cytotoxicity via PI3K/AKT under serum deprivation in H9c2 is explicit; intervention and cell context belong to edge.",
            "AMI association with cardiomyocyte necrosis is explicit; no unsupported causal promotion.",
            "H9c2 serum-deprivation culture as myocardial-infarction apoptosis model is explicit; culture intervention belongs to the model relation.",
            "PTEN siRNA knockdown inhibiting ROS under serum deprivation is explicit; intervention/context are supported. Other outcomes are not recovered."
        ]
    },
    "contract11u_passage_001": {
        "valid_matched_pairs": [[i,i] for i in range(10)],
        "losses": ["Effects removed from HMGB1 knockdown/hyperglycemia [0] and HMGB1/liver damage [4].", "Plasma and 10-week context absent from AST [2] and Cystatin C [9]; evidence is narrowed to result sentence/fragment.", "No AST/ALT ratio added; like the 11U Candidate C control, the explicit ratio observations remain unrepresented."],
        "gains": [],
        "flags": [],
        "notes": [
            "HMGB1 knockdown reduces hyperglycemia, explicitly stated; same IDs/direction and intervention as control, but effects empty.",
            "Comparable ALT between both mice cohorts is symmetric and explicit; plasma and last-injection 10-week contexts are in evidence. Source E517 is the supplied mice mention, unchanged.",
            "Flox-cohort elevated AST vs KO cohort is explicit, same IDs/direction. Plasma/timing context omitted rather than unsupported import from absent evidence.",
            "AST as liver-damage indicator is explicit; unchanged endpoint and direction.",
            "HMGB1 contribution to more severe liver damage remains qualified by findings suggest and hyperglycemic setting. Evidence supports context; effects emptied.",
            "Flox mice increased macrovesicular lipid droplets vs KO cohort is explicit; unchanged supplied mice/lipid endpoints, no gene-to-gene cohort replacement or imported liver context.",
            "Flox mice greater mononuclear inflammatory infiltration vs KO cohort is explicit; unchanged supplied endpoints/direction, no imported liver context.",
            "Flox mice increased glycogen storage is explicit; unchanged mice-to-measurement direction and no inferred staining intervention.",
            "Flox mice increased lipid uptake is explicit; unchanged mice-to-measurement direction and no inferred staining intervention.",
            "KO mice elevated Cystatin C vs Flox cohort is explicit; unchanged IDs/direction. Circulating/plasma and 10-week qualifiers omitted rather than imported from outside saved evidence."
        ]
    }
}


def main():
    """Materialize the fixed semantic review with one explicit judgment per output."""
    for slug, a in CASES.items():
        output = json.loads((REPORT / "cases" / slug / "refined.json").read_text(encoding="utf-8"))
        assert len(a["notes"]) == len(output["relations"])
        a["reviewed_indices"] = list(range(len(a["notes"])))
        a["relation_judgments"] = {str(i): dict(
            evidence_support="no_known_unsupported_assertion_or_rich_value", rich_values_belong_to_edge=True,
            new_unsupported_causality=False, evidence_adequate_for_emitted_values=True, note=note)
            for i,note in enumerate(a.pop("notes"))}
    packet = dict(scientific_gate=GATE,reviewer="primary agent", independent_adjudication=False,
        basis="Every normalized relation and every populated intervention/effects/context value reviewed directly against saved contiguous evidence and frozen source; matched finding identity is manual judgment, not accepted gold.",
        targets=dict(JAK2_overexpression_recovered=False,STAT4_overexpression_recovered=False,
            Runx3_overexpression_retained=False,other_Runx3_findings_retained=True,
            PTEN_expression_recovered=False,artificial_PTEN_self_edge=False,
            dual_DM_rat_HG_HUVEC_expression_context_retained=False,
            unsupported_glucose_gene_causal_edges=0,known_new_unsupported_rich_values=0,
            original_11u_ten_endpoint_pairs_and_directions_preserved=True,
            original_11u_cohort_findings_preserved=True,original_11u_richness_preserved=False,
            SFPQ_cognition_memory_preserved=True,EZH2_poor_prognosis_preserved=True,
            EZH2_pathway_maintenance_effects_preserved=False),
        material_rejection_basis=["Cbl overexpression reversal findings lost, including original Runx3 finding.",
            "PTEN PI3K/AKT mechanism and PI3K-inhibitor reversal lost; expression target not recovered.",
            "EZH2 tumor-initiating capacity lost and conditional pathway topology changed.",
            "11U effects/plasma/timing metadata regressed despite preserving all ten original core findings."],
        no_automatic_promotion=True,stop_prompt_experiments=True,cases=CASES)
    (REPORT / "scientific_review.json").write_text(json.dumps(packet,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")


if __name__ == "__main__":
    main()
