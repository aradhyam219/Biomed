import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  buildDisplayModel,
  entityTypeKey,
  paperRoleAffordance,
  toCytoscapeElements,
} from "../adapter.js";

function nodeElements(elements) {
  return elements.filter((element) => element.group === "nodes");
}

function edgeElements(elements) {
  return elements.filter((element) => element.group === "edges");
}

function authenticFixture() {
  return JSON.parse(readFileSync(new URL("../graph-fixture.json", import.meta.url), "utf8"));
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
          {
            text: "first evidence",
            assertion: "CDK1 interacts with BRCA1.",
            intervention: "CDK1 activation",
            effects: ["increased signaling"],
            context: ["treated cells"],
            surface_form: "interacts",
            score: 0.7,
          },
          {
            text: "second evidence",
            assertion: "CDK1 interaction was observed.",
            intervention: null,
            effects: [],
            context: [],
            surface_form: "interaction",
            score: null,
          },
        ],
      },
    ],
  };

  const elements = toCytoscapeElements(graph);
  assert.deepEqual(nodeElements(elements)[0].data.aliases, graph.nodes[0].aliases);
  assert.deepEqual(nodeElements(elements)[0].data.mentions, graph.nodes[0].mentions);
  assert.deepEqual(edgeElements(elements)[0].data.evidence, graph.edges[0].evidence);
  assert.equal(edgeElements(elements)[0].data.evidence.length, 2);
  assert.equal(
    edgeElements(elements)[0].data.evidence[0].assertion,
    "CDK1 interacts with BRCA1.",
  );
  assert.deepEqual(edgeElements(elements)[0].data.evidence[0].effects, ["increased signaling"]);
  assert.deepEqual(edgeElements(elements)[0].data.evidence[0].context, ["treated cells"]);
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

test("bundles same-direction relations while preserving reverse direction", () => {
  const first = {
    id: "doc_r_001",
    source: "A",
    target: "B",
    predicate: "interacts with",
    negated: false,
    evidence: [{ text: "A interacts with B" }],
  };
  const second = {
    id: "doc_r_002",
    source: "A",
    target: "B",
    predicate: "inhibits expression of",
    negated: true,
    evidence: [{ text: "A does not inhibit B" }, { text: "A inhibits B" }],
  };
  const reverse = {
    id: "doc_r_003",
    source: "B",
    target: "A",
    predicate: "rescues regulation of",
    negated: false,
    evidence: [{ text: "B rescues A" }],
  };

  const model = buildDisplayModel({ nodes: [], edges: [first, second, reverse] });
  assert.equal(model.relationCount, 3);
  assert.equal(model.edges.length, 2);

  const forward = model.edges.find((edge) => edge.source === "A" && edge.target === "B");
  const backward = model.edges.find((edge) => edge.source === "B" && edge.target === "A");
  assert.equal(forward.isBundle, true);
  assert.equal(forward.predicateLabel, "2 relations");
  assert.equal(forward.relationCount, 2);
  assert.equal(forward.relations[0], first);
  assert.equal(forward.relations[1], second);
  assert.equal(forward.relations[1].evidence.length, 2);
  assert.equal(forward.relations[1].evidence[0].context, undefined);
  assert.equal(forward.negated, null);
  assert.equal(forward.negationState, "mixed");

  assert.equal(backward.isBundle, false);
  assert.equal(backward.relationCount, 1);
  assert.equal(backward.relations[0], reverse);
  assert.equal(backward.predicateLabel, "rescues regulation of");
  assert.equal(forward.pairKey, backward.pairKey);
  assert.notEqual(forward.curveDistance, backward.curveDistance);
  assert.equal(forward.pairLaneCount, 2);
  assert.equal(backward.pairLaneCount, 2);
});

test("multi-relation self-edges form a readable bundle", () => {
  const first = {
    id: "doc_r_001",
    source: "A",
    target: "A",
    predicate: "binds",
    negated: false,
    evidence: [{ text: "A binds A" }],
  };
  const second = {
    id: "doc_r_002",
    source: "A",
    target: "A",
    predicate: "regulates",
    negated: false,
    evidence: [{ text: "A regulates A" }],
  };

  const [edge] = edgeElements(toCytoscapeElements({ nodes: [{ id: "A" }], edges: [first, second] }));
  assert.equal(edge.data.isBundle, true);
  assert.equal(edge.data.relations[0], first);
  assert.equal(edge.data.relations[1], second);
  assert.equal(edge.data.curveDistance, 0);
  assert.match(edge.classes, /(?:^| )self-edge(?: |$)/);
});

test("authentic Contract 05R fixture preserves domain and display counts", () => {
  const graph = authenticFixture();
  const model = buildDisplayModel(graph);
  const elements = toCytoscapeElements(graph);
  const displayEdges = edgeElements(elements);

  assert.equal(model.nodes.length, 5);
  assert.equal(model.relationCount, 7);
  assert.equal(model.edges.length, 5);
  assert.equal(displayEdges.length, 5);
  assert.equal(
    model.edges.reduce((total, edge) => total + edge.relationCount, 0),
    7,
  );

  const forwardCdk1 = model.edges.find(
    (edge) => edge.source === "doc_e_001" && edge.target === "doc_e_005",
  );
  const reverseCdk1 = model.edges.find(
    (edge) => edge.source === "doc_e_005" && edge.target === "doc_e_001",
  );
  const hepatocellularCarcinoma = model.edges.find(
    (edge) => edge.source === "doc_e_001" && edge.target === "doc_e_004",
  );
  assert.equal(forwardCdk1.predicateLabel, "2 relations");
  assert.equal(forwardCdk1.relationCount, 2);
  assert.equal(reverseCdk1.isBundle, false);
  assert.equal(reverseCdk1.predicate, "overexpression rescues regulation of");
  assert.equal(reverseCdk1.predicateLabel, "overexpression rescues re…");
  assert.equal(hepatocellularCarcinoma.predicateLabel, "2 relations");
  assert.equal(hepatocellularCarcinoma.relationCount, 2);
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

test("hides unconnected nodes by default while retaining truthful canonical counts", () => {
  const graph = {
    nodes: [
      { id: "A", label: "GeneA", type: "Gene" },
      { id: "B", label: "Disease", type: "Disease" },
      {
        id: "C",
        label: "mice",
        type: "Species",
        paper_role: { category: "contextual", paragraphs: ["The model was mice."], evidence: ["mice"] },
      },
      { id: "D", label: "GeneX", type: "Gene" },
    ],
    edges: [{ id: "R", source: "A", target: "B", predicate: "affects", negated: false }],
  };

  const model = buildDisplayModel(graph);
  assert.equal(model.canonicalNodeCount, 4);
  assert.equal(model.displayedNodeCount, 2);
  assert.equal(model.unconnectedNodeCount, 2);
  assert.equal(model.hiddenUnconnectedCount, 2);
  assert.equal(model.relationCount, 1);
  assert.equal(model.edges.length, 1);

  const oneRevealed = buildDisplayModel(graph, { revealedNodeIds: ["C"] });
  assert.equal(oneRevealed.displayedNodeCount, 3);
  assert.equal(oneRevealed.hiddenUnconnectedCount, 1);

  const allRevealed = buildDisplayModel(graph, { showUnconnected: true });
  assert.equal(allRevealed.displayedNodeCount, 4);
  assert.equal(allRevealed.hiddenUnconnectedCount, 0);
});

test("preserves role metadata and gives Species an explicit presentation class", () => {
  const [species] = toCytoscapeElements({
    nodes: [
      {
        id: "S",
        label: "mice",
        type: "Species",
        paper_role: {
          category: "contextual",
          paragraphs: ["Mice supplied the model context."],
          evidence: ["mice supplied the model context."],
        },
      },
    ],
    edges: [],
  }, { showUnconnected: true });

  assert.match(species.classes, /entity-type-species/);
  assert.equal(species.data.paper_role.category, "contextual");
  assert.deepEqual(species.data.paper_role.evidence, ["mice supplied the model context."]);
});

test("a missing role exposes only a non-interactive diagnostic state", () => {
  const state = paperRoleAffordance({
    id: "unconnected",
    label: "GeneX",
    type: "Gene",
  });

  assert.deepEqual(state, {
    available: false,
    category: null,
    label: "Role enrichment unavailable",
  });

  const app = readFileSync(new URL("../app.js", import.meta.url), "utf8");
  assert.match(app, /if \(affordance\.available\)/);
});

test("bundle warning CSS is a single wrapping block", () => {
  const styles = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  const warning = styles.slice(styles.indexOf(".bundle-note"), styles.indexOf(".back-button"));
  assert.match(warning, /display:\s*block/);
  assert.match(warning, /overflow-wrap:\s*anywhere/);
  assert.match(warning, /white-space:\s*normal/);
});

test("viewer exposes unconnected role and reveal controls", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  const app = readFileSync(new URL("../app.js", import.meta.url), "utf8");

  assert.match(html, /Unconnected entities/);
  assert.match(html, /show-unconnected/);
  assert.match(app, /paperRoleAffordance/);
  assert.match(app, /if \(affordance\.available\)/);
  assert.match(app, /ROLE IN PAPER/);
  assert.match(app, /SOURCE EVIDENCE/);
  const adapter = readFileSync(new URL("../adapter.js", import.meta.url), "utf8");
  assert.match(adapter, /View role in paper/);
});
