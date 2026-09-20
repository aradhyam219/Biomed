import { entityTypeKey, toCytoscapeElements } from "./adapter.js";

const graphContainer = document.querySelector("#cy");
const graphStatus = document.querySelector("#graph-status");
const detailsPanel = document.querySelector("#details");
const graphSummary = document.querySelector("#graph-summary");
const legend = document.querySelector("#entity-legend");

let graphData = null;
let cy = null;

const typeShapes = {
  gene: "ellipse",
  disease: "round-rectangle",
  "cell-line": "rectangle",
  chemical: "diamond",
  organism: "hexagon",
  rna: "vee",
  dna: "octagon",
  unknown: "ellipse",
};

const cytoscapeStyle = [
  {
    selector: "node",
    style: {
      "background-color": "#4c78a8",
      "border-color": "#b7d4f3",
      "border-width": 2,
      color: "#f8fafc",
      content: "data(label)",
      "font-family": "Inter, Segoe UI, sans-serif",
      "font-size": 12,
      "font-weight": 600,
      height: 46,
      label: "data(label)",
      padding: "6px",
      shape: "ellipse",
      "text-max-width": "110px",
      "text-outline-color": "#1b2638",
      "text-outline-width": 2,
      "text-wrap": "wrap",
      "text-valign": "center",
      "text-halign": "center",
      width: 130,
    },
  },
  {
    selector: ".entity-type-gene",
    style: {
      "background-color": "#3b82f6",
      shape: "ellipse",
    },
  },
  {
    selector: ".entity-type-disease",
    style: {
      "background-color": "#d97706",
      shape: "round-rectangle",
    },
  },
  {
    selector: ".entity-type-cell-line",
    style: {
      "background-color": "#059669",
      shape: "rectangle",
    },
  },
  {
    selector: ".entity-type-chemical",
    style: {
      "background-color": "#9333ea",
      shape: "diamond",
    },
  },
  {
    selector: ".entity-type-organism",
    style: {
      "background-color": "#0f766e",
      shape: "hexagon",
    },
  },
  {
    selector: ".entity-type-rna",
    style: {
      "background-color": "#be185d",
      shape: "vee",
    },
  },
  {
    selector: ".entity-type-dna",
    style: {
      "background-color": "#4f46e5",
      shape: "octagon",
    },
  },
  {
    selector: "edge",
    style: {
      "curve-style": "unbundled-bezier",
      "control-point-distances": "data(controlPointDistance)",
      "control-point-weights": 0.5,
      "font-family": "Inter, Segoe UI, sans-serif",
      "font-size": 10,
      "line-color": "#91a4bd",
      "target-arrow-color": "#91a4bd",
      "target-arrow-shape": "triangle",
      label: "data(predicateLabel)",
      "text-margin-y": "data(labelOffset)",
      color: "#f8fafc",
      "text-background-color": "#202d42",
      "text-background-opacity": 0.92,
      "text-background-padding": "3px",
      "text-max-width": "110px",
      "text-rotation": "none",
      "text-wrap": "wrap",
      width: 2,
      "loop-direction": "-45deg",
      "loop-sweep": "40deg",
    },
  },
  {
    selector: "edge.self-edge",
    style: {
      "curve-style": "bezier",
    },
  },
  {
    selector: "edge.bundle-edge",
    style: {
      "line-color": "#b8d4ee",
      "target-arrow-color": "#b8d4ee",
      width: 3,
    },
  },
  {
    selector: "edge.negated",
    style: {
      "line-style": "dashed",
      "line-dash-pattern": [7, 4],
      "line-color": "#f59e0b",
      "target-arrow-color": "#f59e0b",
      width: 3,
    },
  },
  {
    selector: ".is-dimmed",
    style: {
      opacity: 0.22,
    },
  },
  {
    selector: ".is-focused",
    style: {
      opacity: 1,
    },
  },
  {
    selector: "node:selected",
    style: {
      "border-color": "#f8fafc",
      "border-width": 4,
      "overlay-color": "#dbeafe",
      "overlay-opacity": 0.18,
    },
  },
  {
    selector: "edge:selected",
    style: {
      "line-color": "#f8fafc",
      "target-arrow-color": "#f8fafc",
      width: 4,
    },
  },
];

function appendText(parent, text, className = "") {
  const element = document.createElement("span");
  if (className) element.className = className;
  element.textContent = text;
  parent.append(element);
  return element;
}

function appendHeading(parent, title, eyebrow = "") {
  const heading = document.createElement("div");
  heading.className = "detail-heading";
  if (eyebrow) appendText(heading, eyebrow, "detail-eyebrow");
  appendText(heading, title, "detail-title");
  parent.append(heading);
}

function appendField(parent, label, value) {
  const row = document.createElement("div");
  row.className = "detail-field";
  appendText(row, label, "detail-label");
  appendText(row, value, "detail-value");
  parent.append(row);
}

function appendList(parent, values, emptyText) {
  if (!Array.isArray(values) || values.length === 0) {
    appendText(parent, emptyText, "detail-empty");
    return;
  }
  const list = document.createElement("ul");
  list.className = "detail-list";
  for (const value of values) {
    const item = document.createElement("li");
    item.textContent = String(value);
    list.append(item);
  }
  parent.append(list);
}

function appendSection(parent, title) {
  const heading = document.createElement("h3");
  heading.className = "detail-section-title";
  heading.textContent = title;
  parent.append(heading);
}

function displayScore(score) {
  return score === null || score === undefined ? "—" : String(score);
}

function getNode(nodeId) {
  const nodes = Array.isArray(graphData?.nodes) ? graphData.nodes : [];
  return nodes.find((node) => String(node?.id) === String(nodeId)) ?? null;
}

function displayNode(nodeId) {
  const node = getNode(nodeId);
  return node ? `${node.label} (${node.id})` : String(nodeId);
}

function renderIntro(message = "Select a node or relationship to inspect its evidence.") {
  detailsPanel.replaceChildren();
  appendHeading(detailsPanel, "Details", "INSPECTABLE GRAPH");
  appendText(detailsPanel, message, "detail-intro");
}

function renderNode(node) {
  detailsPanel.replaceChildren();
  appendHeading(detailsPanel, node.label, "NODE");
  appendField(detailsPanel, "Node ID", String(node.id));
  appendField(detailsPanel, "Entity type", String(node.type));

  appendSection(detailsPanel, "Aliases");
  appendList(detailsPanel, node.aliases, "No aliases recorded.");

  appendSection(detailsPanel, `Source mentions (${node.mentions.length})`);
  if (node.mentions.length === 0) {
    appendText(detailsPanel, "No source mentions recorded.", "detail-empty");
    return;
  }

  const mentionList = document.createElement("div");
  mentionList.className = "mention-list";
  for (const mention of node.mentions) {
    const card = document.createElement("article");
    card.className = "mention-record";
    appendText(card, mention.text ?? "", "mention-text");
    appendField(card, "Mention ID", String(mention.id ?? "—"));
    appendField(card, "Span", `[${mention.start ?? "—"}, ${mention.end ?? "—"})`);
    appendField(card, "Score", displayScore(mention.score));
    mentionList.append(card);
  }
  detailsPanel.append(mentionList);
}

function evidenceRecords(relation) {
  return Array.isArray(relation?.evidence) ? relation.evidence : [];
}

function pluralize(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function renderRelation(relation, bundle = null) {
  detailsPanel.replaceChildren();
  if (bundle) {
    const backButton = document.createElement("button");
    backButton.type = "button";
    backButton.className = "back-button";
    backButton.textContent = `← Back to ${pluralize(bundle.relationCount, "relation")}`;
    backButton.addEventListener("click", () => renderBundle(bundle));
    detailsPanel.append(backButton);
  }

  appendHeading(detailsPanel, String(relation?.predicate ?? "Relationship"), "RELATIONSHIP");
  appendField(detailsPanel, "Relation ID", String(relation?.id ?? "—"));
  appendField(detailsPanel, "Source node", displayNode(relation?.source));
  appendField(detailsPanel, "Target node", displayNode(relation?.target));
  appendField(detailsPanel, "Predicate", String(relation?.predicate ?? ""));
  appendField(detailsPanel, "Negated", relation?.negated === true ? "Yes" : "No");

  const evidence = evidenceRecords(relation);
  appendSection(detailsPanel, `Evidence (${evidence.length})`);
  if (evidence.length === 0) {
    appendText(detailsPanel, "No evidence records recorded.", "detail-empty");
    return;
  }

  const evidenceList = document.createElement("div");
  evidenceList.className = "evidence-list";
  evidence.forEach((record, index) => {
    const card = document.createElement("article");
    card.className = "evidence-record";
    appendText(card, `Evidence ${index + 1}`, "evidence-label");
    appendText(card, `“${record.text ?? ""}”`, "evidence-text");
    if (record.surface_form) {
      appendField(card, "Surface form", String(record.surface_form));
    }
    if (record.score !== null && record.score !== undefined) {
      appendField(card, "Score", String(record.score));
    }
    evidenceList.append(card);
  });
  detailsPanel.append(evidenceList);
}

function renderBundle(bundle) {
  detailsPanel.replaceChildren();
  appendHeading(
    detailsPanel,
    `${displayNode(bundle.source)} → ${displayNode(bundle.target)}`,
    "RELATIONSHIP BUNDLE",
  );
  appendField(detailsPanel, "Connections", pluralize(bundle.relationCount, "relation"));
  if (bundle.negationState === "mixed") {
    appendText(
      detailsPanel,
      "This bundle contains both affirmed and negated relations; inspect each relation for its state.",
      "bundle-note",
    );
  }

  appendSection(detailsPanel, "Underlying relations");
  const relationList = document.createElement("div");
  relationList.className = "relation-list";
  for (const relation of bundle.relations) {
    const evidence = evidenceRecords(relation);
    const choice = document.createElement("button");
    choice.type = "button";
    choice.className = "relation-choice";
    choice.setAttribute(
      "aria-label",
      `Inspect ${String(relation?.predicate ?? "relation")} ${String(relation?.id ?? "")}`,
    );
    appendText(choice, String(relation?.predicate ?? "Relationship"), "relation-choice-predicate");
    appendText(choice, `Relation ${String(relation?.id ?? "—")}`, "relation-choice-id");
    appendText(
      choice,
      `${relation?.negated === true ? "Negated · " : ""}${pluralize(evidence.length, "evidence record")}`,
      "relation-choice-meta",
    );
    choice.addEventListener("click", () => renderRelation(relation, bundle));
    relationList.append(choice);
  }
  detailsPanel.append(relationList);
}

function renderLegend(nodes) {
  legend.replaceChildren();
  const types = [...new Set(nodes.map((node) => String(node?.type ?? "Unknown")))].sort();
  for (const type of types) {
    const item = document.createElement("span");
    item.className = "legend-item";
    const marker = document.createElement("span");
    marker.className = `legend-marker entity-type-${entityTypeKey(type)}`;
    marker.dataset.shape = typeShapes[entityTypeKey(type)] ?? typeShapes.unknown;
    marker.setAttribute("aria-hidden", "true");
    item.append(marker);
    appendText(item, type);
    legend.append(item);
  }
  const negatedItem = document.createElement("span");
  negatedItem.className = "legend-item";
  const line = document.createElement("span");
  line.className = "legend-negated";
  line.setAttribute("aria-hidden", "true");
  negatedItem.append(line);
  appendText(negatedItem, "Negated relation");
  legend.append(negatedItem);
}

function clearGraphFocus() {
  if (!cy) return;
  cy.elements().removeClass("is-dimmed is-focused");
}

function focusElements(elements) {
  if (!cy) return;
  const all = cy.elements();
  all.removeClass("is-focused").addClass("is-dimmed");
  elements.removeClass("is-dimmed").addClass("is-focused");
}

function focusNode(node) {
  focusElements(node.union(node.neighborhood()));
}

function focusEdge(edge) {
  focusElements(edge.union(edge.source()).union(edge.target()));
}

function renderGraph(graph) {
  graphData = graph;
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const relations = Array.isArray(graph?.edges) ? graph.edges : [];
  renderLegend(nodes);
  renderIntro();

  if (cy) cy.destroy();
  const elements = toCytoscapeElements(graph);
  const displayConnectionCount = elements.filter((element) => element.group === "edges").length;
  graphSummary.textContent = `${nodes.length} nodes · ${relations.length} directed relations · ${displayConnectionCount} displayed connections`;
  cy = globalThis.cytoscape({
    container: graphContainer,
    elements,
    style: cytoscapeStyle,
    minZoom: 0.35,
    maxZoom: 3,
    layout: {
      name: "cose",
      animate: false,
      fit: true,
      idealEdgeLength: 150,
      avoidOverlap: true,
      avoidOverlapPadding: 12,
      minNodeSpacing: 48,
      nodeDimensionsIncludeLabels: true,
      nodeRepulsion: 6000,
      numIter: 500,
      padding: 28,
    },
  });

  cy.on("tap", "node", (event) => {
    cy.elements().unselect();
    event.target.select();
    focusNode(event.target);
    renderNode(event.target.data());
  });
  cy.on("tap", "edge", (event) => {
    cy.elements().unselect();
    event.target.select();
    focusEdge(event.target);
    const edge = event.target.data();
    if (edge.isBundle) {
      renderBundle(edge);
    } else {
      renderRelation(edge.relations?.[0] ?? edge);
    }
  });
  cy.on("tap", (event) => {
    if (event.target === cy) {
      cy.elements().unselect();
      clearGraphFocus();
      renderIntro();
    }
  });

  if (nodes.length === 0 && relations.length === 0) {
    graphStatus.textContent = "Empty graph: no nodes or relationships to display.";
  } else {
    graphStatus.textContent = `Loaded ${nodes.length} nodes, ${relations.length} directed relations, and ${displayConnectionCount} displayed connections.`;
  }
}

async function loadGraph() {
  try {
    if (!globalThis.cytoscape) {
      throw new Error("Cytoscape.js did not load.");
    }
    const response = await fetch("./graph-fixture.json", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`Graph fixture request failed with HTTP ${response.status}.`);
    }
    const graph = await response.json();
    renderGraph(graph);
  } catch (error) {
    graphContainer.replaceChildren();
    graphSummary.textContent = "Graph unavailable";
    renderIntro(String(error?.message ?? error));
    graphStatus.textContent = "Unable to load the graph fixture. Start the documented local server and reload.";
    graphStatus.classList.add("status-error");
  }
}

loadGraph();
