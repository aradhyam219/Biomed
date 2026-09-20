import assert from "node:assert/strict";
import test from "node:test";

import { entityTypeKey, toCytoscapeElements } from "../adapter.js";

function nodeElements(elements) {
  return elements.filter((element) => element.group === "nodes");
}

function edgeElements(elements) {
  return elements.filter((element) => element.group === "edges");
}

test("adapts graph nodes and edges without changing domain direction", () => {
  const graph = {
    nodes: [
      {
        id: "doc_e_001",
        label: "KNTC1",
        type: "Gene",
        aliases: ["KNTC1"],
        mentions: [{ id: "E1", text: "KNTC1", start: 0, end: 5, score: 0.9 }],
      },
      {
        id: "doc_e_002",
        label: "disease",
        type: "Disease",
        aliases: ["disease"],
        mentions: [],
      },
    ],
    edges: [
      {
        id: "doc_r_001",
        source: "doc_e_001",
        target: "doc_e_002",
        predicate: "affects",
        negated: false,
        evidence: [{ text: "KNTC1 affects disease" }],
      },
    ],
  };

  const elements = toCytoscapeElements(graph);
  assert.equal(nodeElements(elements).length, 2);
  assert.equal(edgeElements(elements).length, 1);
  assert.deepEqual(edgeElements(elements)[0].data.source, "doc_e_001");
  assert.deepEqual(edgeElements(elements)[0].data.target, "doc_e_002");
  assert.equal(edgeElements(elements)[0].data.predicate, "affects");
  assert.equal(edgeElements(elements)[0].data.predicateLabel, "affects");
});

test("preserves aliases, mentions, and all evidence records", () => {
  const graph = {
    nodes: [
      {
        id: "doc_e_001",
        label: "CDK1",
        type: "Gene",
        aliases: ["cyclin-dependent kinase 1", "CDK1"],
        mentions: [{ id: "E1", text: "CDK1", start: 2, end: 6, score: 0.8 }],
      },
    ],
    edges: [
      {
        id: "doc_r_001",
        source: "doc_e_001",
        target: "doc_e_001",
        predicate: "interacts with",
        negated: false,
        evidence: [
          { text: "first evidence", surface_form: "interacts", score: 0.7 },
          { text: "second evidence", surface_form: "interaction", score: null },
        ],
      },
    ],
  };

  const elements = toCytoscapeElements(graph);
  assert.deepEqual(nodeElements(elements)[0].data.aliases, graph.nodes[0].aliases);
  assert.deepEqual(nodeElements(elements)[0].data.mentions, graph.nodes[0].mentions);
  assert.deepEqual(edgeElements(elements)[0].data.evidence, graph.edges[0].evidence);
  assert.equal(edgeElements(elements)[0].data.evidence.length, 2);
});

test("marks negated relations for visual styling while retaining negated state", () => {
  const [edge] = edgeElements(
    toCytoscapeElements({
      nodes: [],
      edges: [
        {
          id: "doc_r_001",
          source: "doc_e_001",
          target: "doc_e_001",
          predicate: "interacts",
          negated: true,
          evidence: [{ text: "does not interact" }],
        },
      ],
    }),
  );

  assert.equal(edge.data.negated, true);
  assert.match(edge.classes, /(?:^| )negated(?: |$)/);
});

test("retains valid self-edges as Cytoscape edges", () => {
  const [edge] = edgeElements(
    toCytoscapeElements({
      nodes: [{ id: "doc_e_001", label: "BRCA1", type: "Gene" }],
      edges: [
        {
          id: "doc_r_001",
          source: "doc_e_001",
          target: "doc_e_001",
          predicate: "interacts",
          negated: false,
          evidence: [{ text: "BRCA1 interacts with BRCA1" }],
        },
      ],
    }),
  );

  assert.equal(edge.data.source, "doc_e_001");
  assert.equal(edge.data.target, "doc_e_001");
  assert.equal(edge.data.curveDistance, 0);
});

test("empty or partially absent graph arrays produce no elements", () => {
  assert.deepEqual(toCytoscapeElements({}), []);
  assert.deepEqual(toCytoscapeElements(null), []);
});

test("entity type keys remain presentation-only and extensible", () => {
  assert.equal(entityTypeKey("CellLine"), "cell-line");
  assert.equal(entityTypeKey("Gene or Gene Product"), "gene-or-gene-product");
  assert.equal(entityTypeKey(""), "unknown");
});
