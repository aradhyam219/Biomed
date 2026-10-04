/** Verify frozen graphs through the unchanged viewer adapter and evidence seam. */
import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { buildDisplayModel, toCytoscapeElements } from "../../../viewer/adapter.js";

const root = fileURLToPath(new URL("../../../", import.meta.url));
const files = process.argv.slice(2);
assert.ok(files.length > 0, "Supply baseline and candidate graph JSON paths");
const checks = files.map((file) => {
  const graph = JSON.parse(readFileSync(file, "utf8"));
  const original = JSON.stringify(graph);
  const nodeIds = new Set(graph.nodes.map((node) => node.id));
  for (const edge of graph.edges) {
    assert.ok(nodeIds.has(edge.source) && nodeIds.has(edge.target), "Valid endpoints");
  }
  const hidden = buildDisplayModel(graph);
  const revealed = buildDisplayModel(graph, { showUnconnected: true });
  assert.equal(revealed.nodes.length, graph.nodes.length);
  assert.equal(hidden.nodes.length + hidden.unconnectedNodeCount, graph.nodes.length);
  assert.equal(hidden.displayedRelationCount, graph.edges.length);
  assert.equal(revealed.displayedRelationCount, graph.edges.length);
  assert.equal(revealed.hiddenUnconnectedCount, 0);

  for (const model of [hidden, revealed]) {
    const retained = model.edges.flatMap((edge) => edge.relations);
    assert.equal(retained.length, graph.edges.length);
    assert.deepEqual(
      retained.map((edge) => edge.id).sort(),
      graph.edges.map((edge) => edge.id).sort(),
    );
    for (const display of model.edges) {
      for (const relation of display.relations) {
        assert.equal(display.source, relation.source);
        assert.equal(display.target, relation.target);
        assert.deepEqual(relation, graph.edges.find((edge) => edge.id === relation.id));
      }
    }
  }
  const elements = toCytoscapeElements(graph, { showUnconnected: true });
  const nodes = elements.filter((element) => element.group === "nodes");
  assert.equal(nodes.length, graph.nodes.length);
  for (const node of nodes) {
    const source = graph.nodes.find((value) => value.id === node.data.id);
    assert.deepEqual(node.data.mentions, source.mentions);
    assert.deepEqual(node.data.aliases, source.aliases);
  }
  for (const element of elements.filter((value) => value.group === "edges")) {
    for (const relation of element.data.relations) {
      assert.deepEqual(relation.evidence, graph.edges.find((edge) => edge.id === relation.id).evidence);
    }
  }
  assert.equal(JSON.stringify(graph), original, "Viewer leaves graph JSON unchanged");
  return {
    graph: relative(root, resolve(file)).replaceAll("\\", "/"),
    status: "passed",
    canonical_nodes: graph.nodes.length,
    unconnected_nodes: hidden.unconnectedNodeCount,
    relations: graph.edges.length,
    displayed_connections: revealed.edges.length,
    directional_bundles: revealed.edges.filter((edge) => edge.isBundle).length,
    mixed_negation_bundles: revealed.edges.filter((edge) => edge.negationState === "mixed").length,
    self_relations: graph.edges.filter((edge) => edge.source === edge.target).length,
    evidence_instances: graph.edges.reduce((count, edge) => count + edge.evidence.length, 0),
    rich_evidence_preserved: true,
    hidden_and_revealed_nodes_checked: true,
  };
});
const result = { status: "passed", mechanism: "unchanged viewer adapter and Cytoscape element conversion", checks };
writeFileSync(new URL("../viewer_smoke.json", import.meta.url), `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify(result, null, 2));
