"""Render the source-read Contract 13C judgments and verify ledger coverage.

The entries below are explicit human-readable scientific judgments, not an
exact-JSON matching algorithm. Indices are zero-based frozen relation indices.
Qualifiers can be assessed separately from the surviving core of a claim.
"""
from collections import Counter
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("audit13c", Path(__file__).with_name("audit.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)
R = "RETAINED"
E = "EQUIVALENT / REPHRASED"
B = "BENEFICIAL PRUNING"
H = "HARMFUL OMISSION"
T = "HARMFUL TOPOLOGY CHANGE"
U = "UNCERTAIN"

# Each entry is (baseline indices, candidate indices, verdict, rationale).
REVIEWS = {
"pmcid_pmc10770459": [
([0,9],[6,8],E,"Glucose reduction in knockdown mice and causal hyperglycemia relationship retain the title's mitigation finding."),
([1,8],[],B,"Exploring a role/evaluating an effect are study-purpose statements; outcome relations now convey the actual results."),
([2],[1],E,"Inflammation initiation survives through the exact long-form HMGB1 alias."),
([3],[2],E,"Strong correlation with DM onset/progression survives through the long-form alias."),
([4],[3],R,"Hypothesis remains explicitly a hypothesis, not an observed result."),
([5],[4],E,"Glucose-tolerance hypothesis survives; using glucose avoids making the NER fragment tolerance a gene participant."),
([6],[],B,"Method-only mouse-model edge is removed; knockdown mice and systemic in-vivo knockdown remain in outcome assertions. Inducible-model detail is absent from structured fields, but is experimental setup rather than a lost observed finding."),
([7],[5],R,"STZ induction of the hyperglycemic phenotype is retained."),
([10],[7],E,"Observed enhanced glucose tolerance in knockdown mice survives."),
([11],[8],E,"Systemic knockdown/causal hyperglycemia relationship survives."),
([12],[9],E,"Tentative therapeutic target for hyperglycemia survives without promotion to proven therapy."),
([13],[10],E,"Tentative extension to DM therapy survives."),
([14],[11],E,"Therapeutic potential in DM management survives.")],
"pmcid_pmc11824863": [
([0,10],[4],E,"Cognition/recognition and memory improvement survives once instead of title/result duplication."),
([1],[],B,"AD naming-only relation excluded by the Contract-10 prompt."),
([2],[0],R,"AD disease classification survives."),
([3],[],B,"Fragmented proline and glutamine rich to SFPQ naming-only edge is removed; not an independent biological participant."),
([4],[1],E,"Neurodegenerative-disease role, antioxidant functions and neuronal gene regulation survive."),
([5],[],U,"The explicit knowledge-gap/negated well-understood claim is absent. It is a background uncertainty, not a positive experimental result; significance cannot be defensibly equated with a lost mechanism."),
([6],[],B,"Amyloid-beta/Aβ naming-only link is removed under the protected prompt; long-form model-induction relation survives."),
([7],[2],R,"Amyloid-beta injection establishing AD model survives."),
([8],[2,3],E,"AD mouse model survives in assertions/context rather than a separate AD-to-mouse edge."),
([9],[3],E,"Viral hippocampal SFPQ overexpression in AD mice survives."),
([11],[5],E,"APP reduction survives."),
([12],[6],E,"Tau reduction survives."),
([13],[5],E,"APP being an AD-related marker survives explicitly inside the reduction assertion."),
([14],[6],E,"Tau being an AD-related marker survives explicitly inside the reduction assertion."),
([15,16,17],[],B,"APP, GST and HO-1 naming-only relations are removed; substantive antioxidant/marker findings survive."),
([18],[7],E,"GST upregulation survives."),
([19],[8],E,"HO-1 upregulation survives."),
([20],[9],E,"Bcl-2/Bax ratio increase survives."),
([21,23],[],B,"Phosphorylated-form naming relations are removed; evaluate the actual ratio findings separately."),
([22],[10],T,"Elevated p-PI3K/PI3K ratio survives in assertion, but the edge now ends at phosphoinositide 3-kinase; supplied PI3K denominator node loses all connectivity."),
([24],[11],T,"Elevated p-AKT/AKT ratio survives in assertion, but the edge now ends at protein kinase B; supplied AKT denominator node loses all connectivity."),
([25],[],H,"Explicit activation of the PI3K/AKT signaling pathway is absent from candidate assertion/predicate/effects/context. Increased ratios alone do not explicitly represent the pathway-activation finding."),
([26],[12],E,"Potential prevention/treatment target survives.")],
"pmcid_pmc8605525": [
([0,12],[],U,"Cbl's E3-ligase class/identity is explicit in source but these fragment-to-Cbl edges mix class and identity. The prompt confound and incomplete long-form fragment prevent a confident damage-versus-cleanup verdict."),
([1],[0],E,"Title-level endothelial dysfunction attenuation survives; pathway components survive in separate candidate claims."),
([2],[1],E,"JAK2 pathway inhibition survives."),
([3],[2],E,"STAT4 pathway inhibition survives."),
([4],[4],E,"Inhibition of Runx3-mediated H3K4me3 survives."),
([5],[3],R,"Runx3-mediated H3K4me3 relationship survives."),
([6],[5],E,"Chronic disease description survives."),
([7],[6],E,"Impaired endothelial function survives."),
([8],[7],E,"Impaired NO bioavailability survives."),
([9,13,15],[],B,"NO, Cbl and Runx3 abbreviation links are naming-only pruning under the prompt confound."),
([10],[8],E,"E3-ligase alleviation claim survives, retaining appears-to uncertainty."),
([11,34],[],H,"Potential E3/Cbl-based treatment against DM is not represented in current structured fields; retained DM disease context does not state therapeutic potential."),
([14],[9],E,"STZ DM rat-model induction survives."),
([16],[10],E,"HG-HUVEC in-vitro DM model induction survives without turning glucose into a mechanistic gene regulator."),
([17],[12],E,"JAK2 elevation survives in rat tissues; missing HG-HUVEC qualifier is assessed separately."),
([18],[13],E,"Runx3 elevation survives in rat tissues; missing HG-HUVEC qualifier is assessed separately."),
([19],[14],E,"STAT4 elevation survives in rat tissues; missing HG-HUVEC qualifier is assessed separately."),
([17],[],H,"JAK2 elevation in HG-induced HUVECs is lost; candidate restricts the expression result to diabetic rat tissues."),
([18],[],H,"Runx3 elevation in HG-induced HUVECs is lost; candidate restricts the expression result to diabetic rat tissues."),
([19],[],H,"STAT4 elevation in HG-induced HUVECs is lost; candidate restricts the expression result to diabetic rat tissues."),
([20],[15,16],E,"Dysfunction improvement, restored vasodilation, suppressed HUVEC apoptosis and increased NO survive across two assertions."),
([21],[16],E,"Increased NO survives; cellular setting is present in the adjacent linked result, though per-edge context is thinner."),
([22],[17],R,"Cb1-enhanced JAK2 ubiquitination survives without merging Cb1 into Cbl."),
([23],[18],R,"Cb1-decreased JAK2 expression survives."),
([24],[19],R,"Cb1-decreased STAT4 expression survives."),
([25,26],[20],E,"STAT4 improves Runx3 expression by regulating H3 trimethylation survives in one assertion; the separate H3K4me3 edge is gone, but the mechanism is explicit."),
([27,28],[],H,"The source's joint JAK2-and-STAT4 overexpression rescue/abrogation finding, including increased HUVEC apoptosis, is absent. Count one joint experiment, not two independent experiments."),
([29],[21],E,"Runx3 overexpression rescue/abrogation and apoptosis survives."),
([30],[22,23,24,25],E,"Conclusion mechanism survives across explicit pathway-inactivation/Runx3 inhibition claims."),
([31],[23],E,"JAK2 pathway inactivation survives."),
([32],[24],E,"STAT4 pathway inactivation survives."),
([33],[25],E,"Runx3 inhibition survives.")],
"pmid_27172794": [
([0],[0],E,"Stem-like-cell expansion and activation mechanism survive."),
([1],[1],E,"p21cip1-Wnt signaling activation survives."),
([2],[2],E,"Beta-catenin signaling activation survives."),
([3],[],H,"Explicit CRC stem-like cells contributing to poor patient prognosis is absent; EZH2-to-prognosis is a different finding. Historical disease-level endpoint was imprecise, but the assertion supplied the material stem-cell claim."),
([4],[3],E,"Advanced-stage CRC patients' high EZH2 expression survives; patients are assertion/cohort rather than endpoint."),
([5],[4],E,"Tumor-tissue EZH2 expression survives."),
([6],[5],E,"EZH2 correlation with poor prognosis survives."),
([7],[6],E,"Silencing reduces CRC proliferation survives."),
([8,9],[7,8],E,"One comparative expression finding survives in both directions; count one biological comparison."),
([10,11],[9,10],E,"One double-positive CD133+/CD44+ subpopulation reduction survives with both supplied marker endpoints."),
([12],[11],E,"Tumor-initiating capacity impairment survives."),
([13,14],[12,13],E,"Wnt/beta-catenin activation for CCS maintenance survives with both components."),
([15,16,17],[14,15,16],E,"p21cip1-mediated G1/S requirement and EZH2 pathway activation survive explicitly. Contract10's extra requirement endpoints are represented through EZH2; no material participant is lost."),
([18],[17],R,"EPZ-6438 specific inhibition survives."),
([19],[18],E,"EPZ-6438 prevents CRC progression survives."),
([20],[19],E,"EZH2 G1/S arrest maintaining CCS characteristics survives.")],
"pmid_27370646": [
([0,5],[0,4],E,"One knockdown phenotype experiment retains apoptosis/autophagy, reduced proliferation and reduced migration."),
([1],[],B,"OSCC abbreviation-only edge is removed by the prompt change."),
([2],[2],R,"Disease malignancy classification survives."),
([3],[3],E,"p53 proliferation/apoptosis role in malignant tumors survives."),
([4],[],U,"The source's mutated-p53 knowledge gap/possible therapeutic implications is absent; this is not a demonstrated causal result and its materiality is uncertain."),
([6],[5],E,"VEGF expression block survives."),
([7],[6],E,"Knockdown-to-OSCC-cell-death connection survives."),
([8],[],B,"Generic conclusion about opening new therapeutic directions adds no tested relation beyond retained cell-death/VEGF findings.")],
"pmid_31324362": [
([0,14],[0,13],E,"Proliferation/migration outcome survives; mechanistic qualifiers are assessed separately."),
([1,12,15],[1,11,14],E,"GLS activity enhancement survives through exact assembled aliases; repeated title/results/conclusion claims count once."),
([2,13,16],[2,12,15],E,"GS activity enhancement survives through exact assembled aliases; repeated claims count once."),
([3,4],[3],E,"GS protein correlation with TNM stage survives via full form; no loss from dropping duplicate alias wording."),
([5],[4],E,"Positive c-Myc/GS mRNA correlation survives."),
([6],[5],E,"Increased colonies and S-phase fraction survive."),
([7],[6],E,"KB migration increase survives."),
([8],[7],E,"GLS-inhibitor reversal of colonies/S-phase/migration survives explicitly."),
([9],[8],E,"GS-inhibitor reversal survives explicitly."),
([10],[9],E,"E-cadherin inhibition survives as an outcome."),
([11],[10],E,"N-cadherin increase survives as an outcome."),
([10,12,13],[],H,"The explicit dependence of E-cadherin inhibition on enhanced GLS and GS activity is absent from current structured assertions/intervention/effects/context. Coexisting activity edges are not a stated causal mediation."),
([11,12,13],[],H,"The explicit dependence of N-cadherin promotion on enhanced GLS and GS activity is likewise absent. The outcome survives, but this mechanistic finding does not.")],
"pmid_33652126": [
([0],[0],R,"PTEN mediating cytotoxicity through PI3K/AKT in H9c2 survives."),
([1],[1],E,"AMI/necrosis association survives."),
([2],[2],E,"H9c2 serum-deprivation model of MI apoptosis survives."),
([3],[3],E,"siRNA-mediated ROS suppression survives."),
([4],[4],E,"PI3K-inhibitor reversal survives with scientifically faithful inhibitor-to-PTEN direction. Specific reversed outcomes are assessed separately."),
([4],[],H,"Reversal of PTEN-knockdown suppression of apoptosis is lost from structured meaning; generic effects does not specify apoptosis."),
([4],[],H,"Reversal of PTEN-knockdown suppression of DNA damage is lost from structured meaning."),
([4],[],H,"Reversal of PTEN-knockdown increased proliferation is lost from structured meaning."),
([5],[5],R,"Tentative PI3K critical-component claim survives."),
([6],[6],E,"Tentative AKT component claim survives through assembled long/short-form aliases."),
([7,8,9],[0,5,6],E,"Role of the PTEN/PI3K/AKT pathway in serum-deprivation cytotoxicity survives in title assertion plus explicit component relations. Loss of direct component-to-cytotoxicity edges is not counted as loss of this scientific finding.")],
"pmid_38569671": [
([0,17],[0,15],E,"Asthma alleviation by pyroptosis suppression survives; title/conclusion duplicates count once."),
([1],[1],E,"OVA asthma mouse-model establishment survives."),
([2],[],B,"Method-only detection of effects is replaced by explicit inflammation result claims."),
([3],[],B,"Investigated effect on p53 is replaced by actual suppression/inhibition results."),
([4],[2],E,"Caspase-3 increase survives."),
([5],[3],E,"Serum IgG increase survives."),
([6],[4],E,"IL-1beta increase and compartment qualifiers survive."),
([7],[5],E,"KC increase and compartment qualifiers survive."),
([8],[6],E,"TNF-alpha increase and compartment qualifiers survive."),
([9],[7],E,"Hub-gene identification survives."),
([10],[8,10],E,"In-vitro BEAS inflammation suppression survives; IL-13 induction is an explicit separate model relation."),
([11],[9,10],E,"BEAS proliferation increase/apoptosis suppression survives; IL-13 model relation remains."),
([12],[10],E,"IL-13 induction survives."),
([13],[11],E,"In-vivo inflammation suppression survives."),
([14],[11,12,13],E,"OVA asthma improvement with oxidative-stress/inflammation/pyroptosis suppression survives across result/model claims."),
([15],[13],R,"OVA-induced asthma survives."),
([16,18],[14,16],E,"One p53 suppression finding survives with both result/conclusion assertions.")]
}

# The four authoritative Contract10 views are reviewed independently.
TEN_MAP = {
"pmcid_pmc11824863": [[0,10],[2],[4],[5],[8],[7],[9],[10],[11],[12],[13],[14],[18],[19],[20],[22],[24],[25],[26]],
"pmcid_pmc8605525": [[1],[2],[3],[4],[5],[6],[7],[8],[10],[11,34],[14],[16],None,[17],[18],[19],[20],[21],[22],[23],[24],[25,26],[27,28],[27,28],[29],[30],[31],[32],[33],[11,34]],
"pmid_27172794": [[0],[1],[2],[3],[4],[5],[6],[7],[8,9],[8,9],[10,11],[10,11],[12],[13,14],[13,14],[15,16,17],[15,16,17],[15,16,17],[15,16,17],[18],[19],[20]],
"pmid_33652126": [[0],[1],[2],None,None,[3],[4],[5],[6],[7,8,9],[7,8,9],[7,8,9]]
}

SEVERITY = {
"pmcid_pmc10770459": ("GREEN","Observed glucose reduction, tolerance improvement, in-vivo causality and therapeutic potential remain. New orphans are a method-only mouse edge and mis-typed tolerance fragment."),
"pmcid_pmc11824863": ("ORANGE","Most SFPQ outcomes survive, but explicit PI3K/AKT activation is lost and both ratio-denominator nodes become orphaned. These are meaningful signaling/topology regressions, not just alias pruning."),
"pmcid_pmc8605525": ("ORANGE","Core Cb1-JAK2-STAT4-Runx3 mechanism remains, but the joint JAK2/STAT4 rescue experiment and several HG-HUVEC expression findings disappear; treatment potential is also lost."),
"pmid_27172794": ("YELLOW","The central EZH2/p21cip1/Wnt/beta-catenin mechanism and EPZ-6438 result remain; the explicit CCS contribution to poor prognosis is omitted."),
"pmid_27370646": ("GREEN","All demonstrated p53 knockdown phenotypes and VEGF suppression survive; the added cell-line relation is useful. Omitted mutation knowledge-gap claim is separately uncertain."),
"pmid_31324362": ("YELLOW","Core activity/outcome/inhibitor reversal findings survive, but GLS/GS mediation of both cadherin outcomes is no longer explicitly represented."),
"pmid_33652126": ("ORANGE","Central PTEN/PI3K/AKT framework remains, but specific apoptosis/DNA-damage/proliferation reversal outcomes disappear. Contract10 additionally reveals loss of serum-deprivation PTEN upregulation."),
"pmid_38569671": ("GREEN","KIF23/pyroptosis/p53 mechanism, inflammatory factors and in-vitro/in-vivo results remain; method-only edges are replaced by results.")}


def orphan_ids(g):
    connected = {e[k] for e in g['edges'] for k in ('source','target')}
    return {n['id'] for n in g['nodes']} - connected


def findings(slug, p, baseline):
    """Expand reviewed groups with exact frozen source and relation references."""
    groups = REVIEWS[slug]
    if baseline == 'baseline_contract10':
        mapped = []
        for old_indices, matches, verdict, note in groups:
            indices = [i for i, v in enumerate(TEN_MAP[slug]) if v is not None and set(v) == set(old_indices)]
            if indices:
                mapped.append((indices,matches,verdict,note))
        # Collapse the Contract10 title/result duplication into one finding.
        if slug == 'pmcid_pmc11824863':
            entry = next(v for v in mapped if v[0] == [0])
            entry[0].append(7)
        if slug == 'pmcid_pmc8605525':
            mapped.extend([([12],[11],E,'Cbl downregulation survives in rat tissues.'),([12],[],H,'Cbl reduction in HG-induced HUVECs is absent; candidate states only diabetic rat tissues.')])
        if slug == 'pmid_33652126':
            mapped.extend([([3],[3,4],E,'siRNA of PTEN used to knock down PTEN survives as intervention in other assertions. Dropped self-edge is not treated as invalid biological noise.'),([4],[],H,'Serum deprivation in H9c2 increased PTEN expression; no current assertion/intervention/effects/context states this finding.')])
        groups = mapped
    values = p[baseline]
    result = []
    # Different abbreviation pairs and different study-purpose statements are
    # separate pruning units, even when their rationale is shared.
    expanded = []
    for indices,matches,verdict,note in groups:
        if verdict == B and len(indices) > 1:
            expanded.extend(([j],matches,verdict,note) for j in indices)
        else:
            expanded.append((indices,matches,verdict,note))
    for i,(indices,matches,verdict,note) in enumerate(expanded):
        result.append({'finding_id':f'{baseline}:{i:03}', 'baseline_relation_indices':indices,'candidate_relation_indices':matches,'classification':verdict,'rationale':note,'baseline_assertions':[values[j]['assertion'] for j in indices], 'source_evidence':list(dict.fromkeys(values[j]['evidence'] for j in indices)), 'material':verdict not in (B,U)})
    assert set(range(len(values))) == {j for v in result for j in v['baseline_relation_indices']}, (slug,baseline,'coverage')
    return result


def main():
    a.verify()
    rows = []
    all_counts = Counter()
    for slug in a.SLUGS:
        p = a.read(a.OUT/'inputs'/f'{slug}.json')
        candidate = a.read(a.OUT/'candidate'/slug/'result.json')['relations']
        graphs = {n:a.read(a.OUT/'projections'/slug/f'{n}.json') for n in ('baseline_09b','candidate')}
        review = {}
        for baseline in ('baseline_09b','baseline_contract10'):
            if baseline not in p: continue
            g = a.read(a.OUT/'projections'/slug/f'{baseline}.json')
            cg = graphs['candidate']
            nodes = {n['id']:n for n in g['nodes']}
            assert g['nodes'] == cg['nodes']
            bo,co = orphan_ids(g),orphan_ids(cg)
            categories = {'INHERITED ORPHAN':bo&co,'NEW ORPHAN':co-bo,'RESOLVED ORPHAN':bo-co,'NEW NODE / IDENTITY DIFFERENCE':set()}
            fs = findings(slug,p,baseline)
            candidate_evidence = '\n'.join(r['evidence'] for r in candidate)
            for f in fs:
                if f['classification'] == H:
                    # This flag is textual recovery evidence, never a surrogate
                    # for a scientifically reviewed structured representation.
                    f['baseline_evidence_retained_in_candidate_quotes'] = all(q in candidate_evidence for q in f['source_evidence'])
                    f['loss_scope'] = 'explicit structured scientific meaning; may remain recoverable from evidence quotes'
                    note = f['rationale']
                    snippet = {
                        'pmcid_pmc11824863':'indicating activation of the PI3K/AKT signaling pathway',
                        'pmid_27172794':'Because colorectal cancer (CRC) stem-like cells (CCS-like cells) contribute to poor patient prognosis',
                        'pmid_31324362':'by enhancing the activity of GLS and GS',
                    }.get(slug)
                    if slug == 'pmcid_pmc8605525':
                        snippet = ('HG-induced HUVECs' if 'HG-induced' in note else 'Overexpression of JAK2 and STAT4, or Runx3' if 'joint JAK2' in note else 'These evidence might underlie novel Cbl-based treatment against DM in the future.')
                    if slug == 'pmid_33652126':
                        snippet = ('serum deprivation in H9c2 cells increased PTEN expression' if 'increased PTEN expression' in note else 'DNA damage' if 'DNA damage' in note else 'increased cell proliferation' if 'proliferation' in note else 'cell apoptosis')
                    assert snippet and snippet in p['source_text']
                    f['lost_meaning_source_excerpt'] = snippet
                    f['lost_meaning_recoverable_from_evidence'] = snippet in candidate_evidence
                    f['candidate_quote_indices'] = [i for i,r in enumerate(candidate) if snippet in r['evidence']]
            assembly = a.read(a.OUT/'projections'/slug/'assembly.json')['mention_to_document_entity']
            orphan_records = {}
            for label, ids in categories.items():
                records = []
                for node_id in sorted(ids):
                    record = {'id':node_id,'label':nodes[node_id]['label'],'type':nodes[node_id]['type']}
                    if label == 'NEW ORPHAN':
                        indices = [i for i,r in enumerate(p[baseline]) if node_id in (assembly[r['source']],assembly[r['target']])]
                        record['previous_relations'] = [{'index':i,**p[baseline][i]} for i in indices]
                        causes = {
                            ('pmcid_pmc10770459','mouse'):('relation represented through another alias/node','Knockdown mice remain in outcome assertions/context; mouse-model edge omitted.'),
                            ('pmcid_pmc10770459','tolerance'):('beneficial cleanup','Glucose tolerance is now linked to glucose, rather than the NER fragment tolerance tagged Gene.'),
                            ('pmcid_pmc11824863','proline and glutamine rich'):('beneficial cleanup','Naming-only fragmented long form edge removed.'),
                            ('pmcid_pmc11824863','Aβ1–42'):('beneficial cleanup','Naming-only alias edge removed; amyloid-beta1–42 model-induction finding survives.'),
                            ('pmcid_pmc11824863','mouse'):('relation represented through another alias/node','AD mouse model survives in assertion/context; no direct organism edge.'),
                            ('pmcid_pmc11824863','PI3K'):('endpoint changed','Ratio assertion survives on the separate long-form target; supplied denominator PI3K loses topology, and pathway edge is omitted.'),
                            ('pmcid_pmc11824863','AKT'):('endpoint changed','Ratio assertion survives on protein kinase B target; supplied denominator AKT loses topology, and pathway edge is omitted.'),
                            ('pmcid_pmc8605525','runt-related transcription factor 3'):('beneficial cleanup','Abbreviation-only Runx3 edge removed; assembled fragment identity is held identical on both sides.'),
                            ('pmid_27172794','patients'):('endpoint changed','Advanced-stage patients expressing EZH2 survives as EZH2-to-CRC assertion/cohort; plural patients node is no longer an endpoint.')}
                        record['cause'],record['explanation'] = causes.get((slug,record['label']),('uncertain','Requires source-grounded manual determination.'))
                        assert record['cause'] != 'uncertain', (slug,record)
                    records.append(record)
                orphan_records[label] = records
            count = Counter(f['classification'] for f in fs)
            historical = p['historical_09b_graph' if baseline=='baseline_09b' else 'historical_contract10_graph']
            review[baseline] = {'findings':fs,'classification_counts':dict(count),'orphans':orphan_records,'historical_graph_counts':{'nodes':len(historical['nodes']),'edges':len(historical['edges']),'orphans':len(orphan_ids(historical))},'controlled_counts':{'baseline_nodes':len(g['nodes']),'current_nodes':len(cg['nodes']),'baseline_orphans':len(bo),'current_orphans':len(co),'new_orphans':len(co-bo),'resolved_orphans':len(bo-co),'baseline_relations':len(p[baseline]),'current_relations':len(candidate),'baseline_edges':len(g['edges']),'current_edges':len(cg['edges']),'material_findings_lost':count[H],'beneficial_pruning':count[B],'harmful_topology_changes':count[T]}}
        mapped = {i for f in review['baseline_09b']['findings'] for i in f['candidate_relation_indices']}
        unmatched = sorted(set(range(len(candidate))) - mapped)
        additions = []
        for i in unmatched:
            note = {('pmcid_pmc10770459',0):'Useful explicit hyperglycemia contribution to DM complications/morbidity.',('pmcid_pmc8605525',11):'Useful rat-tissue Cbl downregulation relative to 09B; already present in Contract10.',('pmid_27370646',1):'Useful SSC-4 cell-line disease relation, source-grounded in title.'}.get((slug,i))
            assert note, (slug,i,'unreviewed addition')
            additions.append({'candidate_relation_index':i,'classification':'USEFUL CURRENT-ONLY','rationale':note,'relation':candidate[i]})
        if slug == 'pmid_38569671':
            additions.append({'candidate_relation_index':9,'classification':'USEFUL ADDED DETAIL','rationale':'In-vitro pyroptosis suppression is explicit in source and now included with BEAS cellular outcomes, while the other baseline findings remain.','relation':candidate[9]})
        severity, reason = SEVERITY[slug]
        value = {'paper_id':p['paper_id'],'title':p['title'],'severity':severity,'severity_justification':reason,'views':review,'current_additions':additions,'noise_additions':[],'source_grounding_policy':'Exact frozen title plus complete abstract only. Findings must survive in structured predicate/assertion/intervention/effects/context; an evidence quote alone does not establish retention. Source quotations are retained for review.'}
        a.write(a.OUT/'comparisons'/f'{slug}.json',value)
        view = review['baseline_09b']
        row = {'paper':p['paper_id'],'slug':slug,**view['controlled_counts'],'severity':severity}
        rows.append(row)
        all_counts.update(view['classification_counts'])
        md = [f'# {p["paper_id"]}: {severity}',reason,'','## Frozen source','',p['source_text'],'','## Orphan identities (controlled 09B)','']
        for category, records in view['orphans'].items():
            md.append(f'- {category}: '+(', '.join(f"{n['label']} [{n['id']}, {n['type']}]" for n in records) or 'none'))
            for n in records:
                if category=='NEW ORPHAN': md.append(f"  - {n['cause']}: {n['explanation']} Previous relation indices: "+', '.join(str(v['index']) for v in n['previous_relations']))
        for baseline,rv in review.items():
            md += ['',f'## {baseline} finding ledger','']
            for f in rv['findings']:
                md += [f"- **{f['classification']}** {f['finding_id']}; baseline {f['baseline_relation_indices']}; candidate {f['candidate_relation_indices']}. {f['rationale']}", '  Source: '+ ' / '.join(f['source_evidence'])]
        md += ['','## Current additions','']+[f"- {v['classification']}: {v['rationale']}" for v in additions]
        (a.OUT/'comparisons'/f'{slug}.md').write_text('\n'.join(md).rstrip()+'\n',encoding='utf-8')
    totals = {key:sum(r[key] for r in rows) for key in rows[0] if isinstance(rows[0][key],int)}
    totals.update({'material_findings_retained':all_counts[R],'material_findings_equivalently_represented':all_counts[E],'material_findings_beneficially_pruned':all_counts[B],'material_findings_genuinely_lost':all_counts[H],'harmful_topology_changes':all_counts[T],'uncertain_cases':all_counts[U]})
    totals['structured_losses_recoverable_from_evidence'] = sum(f['lost_meaning_recoverable_from_evidence'] for row in rows for f in a.read(a.OUT/'comparisons'/f'{row["slug"]}.json')['views']['baseline_09b']['findings'] if f['classification']==H)
    totals['losses_absent_from_candidate_evidence_too'] = totals['material_findings_genuinely_lost'] - totals['structured_losses_recoverable_from_evidence']
    severity_counts = {s:sum(r['severity']==s for r in rows) for s in ('GREEN','YELLOW','ORANGE','RED')}
    verdict = 'CURRENT SOL GRAPHS SHOW SIGNIFICANT MATERIAL REGRESSION'
    ten_views = [a.read(a.OUT/'comparisons'/f'{slug}.json')['views']['baseline_contract10'] for slug in TEN_MAP]
    ten_aggregate = {key:sum(v['controlled_counts'][key] for v in ten_views) for key in ten_views[0]['controlled_counts']}
    a.write(a.OUT/'summary.json',{'contract':'13C','starting_sha':a.START,'baseline':'09B controlled projection for all eight; authoritative Contract10 supplementary views for four','counting_policy':'Reviewed finding units deduplicate repeat assertions and joint experimental participants. Partial loss of material outcome/setting/mechanistic qualifiers is a separate unit from its retained core; classification counts are not relation-count differences. Beneficial pruning counts removed redundant/method/naming units, not lost supported biological results. Separate baseline views must never be summed. Losses are explicit structured meaning, with quote-only recovery counted separately.','rows':rows,'aggregate':totals,'authoritative_contract10_four_paper_aggregate':ten_aggregate,'additional_contract10_only_losses':['Cbl downregulation in HG-induced HUVECs','Serum deprivation increased PTEN expression in H9c2 cells'],'distinct_structured_losses_union_of_baseline_views':14,'severity_counts':severity_counts,'verdict':verdict,'confounds':a.read(a.OUT/'manifest.json')['09b_equivalence']})
    columns = ['paper','baseline_nodes','current_nodes','baseline_orphans','current_orphans','new_orphans','resolved_orphans','baseline_relations','current_relations','material_findings_lost','beneficial_pruning','severity']
    md = ['# Contract 13C — Eight-paper graph damage audit','',verdict,'','Four exact 12A reuses; four fresh Sol-medium/Standard background cases, each successful in one generation with zero repairs. No NER, role inference, auditor, second pass, repair experiment or production changes.','', 'All headline counts below use 09B relations versus Sol relations projected through the same current deterministic assembly and graph builder on the identical packet per paper, before roles. Contract10 is the authoritative additional four-paper view in each comparison JSON. Historical graph counts are stored separately.','', 'Confound: 09B lacks the Contract10 instruction excluding naming/alias-only relations; semantic schemas are identical. The exact prompt diff is preserved in prompt_confounds.diff. Four 09B packets have the same ID-keyed entity records as 12A but a different order; both sides use the unchanged 12A order. No historical artifacts were rewritten. Thus connectivity differences are relation-output differences, but 09B differences cannot all be attributed solely to model choice.','', '| Paper | Baseline nodes | Current nodes | Baseline orphans | Current orphans | New orphans | Resolved orphans | Baseline relations | Current relations | Material findings lost | Beneficial pruning | Severity |','|'+'|'.join(['---']+['---:']*10+['---'])+'|']
    for row in rows: md.append('| '+' | '.join(str(row[c]) for c in columns)+' |')
    for row in rows:
        comp = a.read(a.OUT/'comparisons'/f'{row["slug"]}.json')
        view = comp['views']['baseline_09b']
        md += ['',f'## {row["paper"]} — {row["severity"]}','',comp['severity_justification'],'','New orphans: '+(', '.join(n['label'] for n in view['orphans']['NEW ORPHAN']) or 'none')+'.','']
        md += ['- '+f['rationale'] for f in view['findings'] if f['classification'] in (H,T)] or ['- No demonstrated material finding lost.']
        if 'baseline_contract10' in comp['views']:
            cv = comp['views']['baseline_contract10']; md += ['', 'Authoritative Contract10 controlled view: '+str(cv['controlled_counts'])+'.']
        md += ['',f"[Full source-grounded ledger and all orphan identities](comparisons/{row['slug']}.md)."]
    md += ['','## Aggregate (09B controlled view)','']+[f'- {k}: {v}' for k,v in totals.items()]+['']+[f'- {k}: {v}' for k,v in severity_counts.items()]
    md += ['','Lost findings count distinct source-supported structured meaning, including lost material mechanistic/setting/outcome qualifiers. They are separate from two harmful SFPQ topology changes. Many lost meanings remain recoverable by reading the original source sentence in candidate evidence: this audit does not claim their source text was erased. A quote alone does not encode the missing result as an asserted graph finding. Each omission records whether its exact baseline evidence remains in candidate quotes. Beneficial pruning counts naming/method/redundant units; it does not imply those were material biological results. Full per-baseline relation coverage is verified in the machine-readable ledgers.','', 'No RED verdict: the eight abstracts still retain their main experimental frameworks. The signal nevertheless spans five papers and includes missing signaling, rescue, mechanistic and intervention-response content; fewer edges cannot be called a net scientific improvement.','',verdict]
    md.insert(-1, 'Authoritative Contract10 also exposes two losses not represented by 09B: Cbl reduction in HG-HUVECs and serum-deprivation PTEN upregulation. Thus the union of the two baseline views identifies 14 distinct structured losses; the eight-row table/aggregate deliberately remain the controlled full-eight 09B comparison. Do not add the two baseline totals.')
    (a.OUT/'summary.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    print(totals,severity_counts)

if __name__ == '__main__':
    main()
