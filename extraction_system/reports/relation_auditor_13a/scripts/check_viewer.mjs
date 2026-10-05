/** Check all five unchanged frozen graphs through the actual viewer adapter. */
import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { buildDisplayModel, toCytoscapeElements } from "../../../viewer/adapter.js";

const report = fileURLToPath(new URL("../", import.meta.url));
const controls = new URL("../../relation_prompt_format_12bf/graphs/control/", import.meta.url);
const slugs = ["pmcid_pmc11824863", "pmcid_pmc8605525", "pmid_27172794",
  "pmid_33652126", "contract11u_passage_001"];
const checks = slugs.map((slug) => {
  const graph = JSON.parse(readFileSync(new URL(`${slug}.json`, controls), "utf8"));
  const before = JSON.stringify(graph);
  const ids = new Set(graph.nodes.map((node) => node.id));
  for (const edge of graph.edges) {
    assert.ok(ids.has(edge.source) && ids.has(edge.target));
  }
  for (const showUnconnected of [false, true]) {
    const model = buildDisplayModel(graph, { showUnconnected });
    const relations = model.edges.flatMap((edge) => edge.relations);
    assert.equal(relations.length, graph.edges.length);
    assert.deepEqual(relations.map((r) => r.id).sort(), graph.edges.map((r) => r.id).sort());
    for (const relation of relations) {
      assert.deepEqual(relation, graph.edges.find((edge) => edge.id === relation.id));
    }
    assert.equal(model.nodes.length + model.hiddenUnconnectedCount, graph.nodes.length);
    const elements = toCytoscapeElements(model);
    assert.ok(elements.length >= model.nodes.length);
  }
  assert.equal(JSON.stringify(graph), before);
  return { case: slug, passed: true, canonical_nodes: graph.nodes.length,
    canonical_edges: graph.edges.length, domain_mutation: false };
});
writeFileSync(`${report}/viewer_compatibility.json`, JSON.stringify(checks, null, 2) + "\n");
console.log("Five frozen graphs retain direction, complete evidence and visibility behavior.");
