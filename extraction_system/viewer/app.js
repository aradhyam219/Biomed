import { entityTypeKey, toCytoscapeElements } from "./adapter.js";

const graphContainer = document.querySelector("#cy");
const graphStatus = document.querySelector("#graph-status");
const detailsPanel = document.querySelector("#details");
const graphSummary = document.querySelector("#graph-summary");
const legend = document.querySelector("#entity-legend");
const unconnectedList = document.querySelector("#unconnected-list");
const showUnconnectedControl = document.querySelector("#show-unconnected");

let graphData = null;
let cy = null;
let showUnconnected = false;
let revealedUnconnectedIds = new Set();

const typeShapes = {
  gene: "ellipse",
  disease: "round-rectangle",
  "cell-line": "rectangle",
  chemical: "diamond",
  species: "hexagon",
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
    selector: ".entity-type-species",
    style: {
      "background-color": "#84cc16",
      shape: "hexagon",
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

function roleCategory(node) {
  if (node?.paper_role?.category === "contextual") return "contextual";
  if (node?.paper_role?.category === "substantive") return "substantive";
  return entityTypeKey(node?.type) === "species" ? "contextual" : "substantive";
}

function appendPaperRole(parent, node, options = {}) {
  const includeHeading = options.includeHeading !== false;
  const role = node?.paper_role;
  if (includeHeading) appendSection(parent, "Role in paper");
  if (!role) {
    appendText(parent, "No grounded role overview is available for this node.", "role-unavailable");
    return;
  }

  appendField(parent, "Role category", String(role.category ?? "—"));
  const roleBlock = document.createElement("div");
  roleBlock.className = "role-panel";
  const roleHeading = document.createElement("h4");
  roleHeading.textContent = "ROLE IN PAPER";
  roleBlock.append(roleHeading);
  for (const paragraph of Array.isArray(role.paragraphs) ? role.paragraphs : []) {
    const element = document.createElement("p");
    element.textContent = String(paragraph);
    roleBlock.append(element);
  }
  const evidenceHeading = document.createElement("h4");
  evidenceHeading.textContent = "SOURCE EVIDENCE";
  roleBlock.append(evidenceHeading);
  const evidence = Array.isArray(role.evidence) ? role.evidence : [];
  if (evidence.length === 0) {
    appendText(roleBlock, "No source evidence recorded.", "role-unavailable");
  } else {
    const list = document.createElement("ul");
    list.className = "role-evidence";
    for (const value of evidence) {
      const item = document.createElement("li");
      item.textContent = String(value);
      list.append(item);
    }
    roleBlock.append(list);
  }
  parent.append(roleBlock);
}

function renderNode(node) {
  detailsPanel.replaceChildren();
  appendHeading(detailsPanel, node.label, "NODE");
  appendField(detailsPanel, "Node ID", String(node.id));
  appendField(detailsPanel, "Entity type", String(node.type));
  if (node.paper_role) appendPaperRole(detailsPanel, node);

  appendSection(detailsPanel, "Aliases");
  appendList(detailsPanel, node.aliases, "No aliases recorded.");

  const mentions = Array.isArray(node.mentions) ? node.mentions : [];
  appendSection(detailsPanel, `Source mentions (${mentions.length})`);
  if (mentions.length === 0) {
    appendText(detailsPanel, "No source mentions recorded.", "detail-empty");
    return;
  }

  const mentionList = document.createElement("div");
  mentionList.className = "mention-list";
  for (const mention of mentions) {
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

function appendEvidenceValue(parent, label, value, className = "") {
  const block = document.createElement("div");
  block.className = "evidence-detail";
  appendText(block, label, "evidence-detail-label");
  appendText(block, String(value), className);
  parent.append(block);
}

function appendEvidenceList(parent, label, values) {
  if (!Array.isArray(values) || values.length === 0) return;
  const block = document.createElement("div");
  block.className = "evidence-detail";
  appendText(block, label, "evidence-detail-label");
  const list = document.createElement("ul");
  list.className = "detail-list evidence-detail-list";
  for (const value of values) {
    const item = document.createElement("li");
    item.textContent = String(value);
    list.append(item);
  }
  block.append(list);
  parent.append(block);
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
    if (record.assertion) {
      appendEvidenceValue(card, "Assertion", record.assertion, "evidence-assertion");
    }
    if (record.intervention) {
      appendEvidenceValue(card, "Intervention", record.intervention);
    }
    appendEvidenceList(card, "Effects", record.effects);
    appendEvidenceList(card, "Context", record.context);
    appendEvidenceValue(card, "Evidence", `“${record.text ?? ""}”`, "evidence-text");
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

function canonicalUnconnectedNodes() {
  const nodes = Array.isArray(graphData?.nodes) ? graphData.nodes : [];
  const relations = Array.isArray(graphData?.edges) ? graphData.edges : [];
  const connectedIds = new Set();
  for (const relation of relations) {
    connectedIds.add(String(relation?.source ?? ""));
    connectedIds.add(String(relation?.target ?? ""));
  }
  return nodes.filter((node) => !connectedIds.has(String(node?.id ?? "")));
}

function renderUnconnectedPanel() {
  if (!unconnectedList) return;
  unconnectedList.replaceChildren();
  const nodes = canonicalUnconnectedNodes();
  if (nodes.length === 0) {
    appendText(unconnectedList, "No unconnected entities in this graph.", "detail-empty");
    return;
  }

  const groups = new Map([
    ["substantive", []],
    ["contextual", []],
  ]);
  for (const node of nodes) groups.get(roleCategory(node)).push(node);
  for (const [category, values] of groups) {
    if (values.length === 0) continue;
    const group = document.createElement("section");
    group.className = "unconnected-group";
    const heading = document.createElement("h3");
    heading.textContent = category === "substantive" ? "Substantive entities" : "Contextual entities";
    const count = document.createElement("span");
    count.className = "unconnected-group-count";
    count.textContent = ` · ${values.length}`;
    heading.append(count);
    group.append(heading);

    const cards = document.createElement("div");
    cards.className = "unconnected-cards";
    for (const node of values) {
      const card = document.createElement("details");
      card.className = "unconnected-card";
      const summary = document.createElement("summary");
      const title = document.createElement("span");
      title.className = "unconnected-card-title";
      title.textContent = String(node?.label ?? node?.id ?? "");
      const meta = document.createElement("span");
      meta.className = "unconnected-card-meta";
      meta.textContent = `${String(node?.type ?? "Unknown")} · ${category}`;
      const roleHint = document.createElement("span");
      roleHint.className = "unconnected-card-role-hint";
      roleHint.textContent = "View role in paper";
      summary.append(title, meta, roleHint);
      card.append(summary);

      const body = document.createElement("div");
      body.className = "unconnected-card-body";
      const revealLabel = document.createElement("label");
      revealLabel.className = "reveal-control";
      const reveal = document.createElement("input");
      reveal.type = "checkbox";
      reveal.checked = showUnconnected || revealedUnconnectedIds.has(String(node.id));
      reveal.disabled = showUnconnected;
      reveal.addEventListener("change", () => {
        const nodeId = String(node.id);
        if (reveal.checked) revealedUnconnectedIds.add(nodeId);
        else revealedUnconnectedIds.delete(nodeId);
        renderGraph(graphData);
      });
      revealLabel.append(reveal, document.createTextNode("Show on graph"));
      body.append(revealLabel);

      const roleDetails = document.createElement("details");
      roleDetails.className = "role-details";
      const roleSummary = document.createElement("summary");
      roleSummary.textContent = "View role in paper";
      roleDetails.append(roleSummary);
      appendPaperRole(roleDetails, node, { includeHeading: false });
      body.append(roleDetails);
      card.append(body);
      cards.append(card);
    }
    group.append(cards);
    unconnectedList.append(group);
  }
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
  if (showUnconnectedControl) showUnconnectedControl.checked = showUnconnected;
  renderUnconnectedPanel();

  if (cy) cy.destroy();
  const elements = toCytoscapeElements(graph, {
    showUnconnected,
    revealedNodeIds: [...revealedUnconnectedIds],
  });
  const displayConnectionCount = elements.filter((element) => element.group === "edges").length;
  const displayedNodeCount = elements.filter((element) => element.group === "nodes").length;
  const hiddenUnconnectedCount = canonicalUnconnectedNodes().length -
    elements.filter((element) => element.group === "nodes" && canonicalUnconnectedNodes().some((node) => String(node.id) === String(element.data.id))).length;
  graphSummary.textContent = `${nodes.length} entities · ${displayedNodeCount} displayed · ${hiddenUnconnectedCount} unconnected hidden · ${relations.length} directed relations · ${displayConnectionCount} displayed connections`;
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
    graphStatus.textContent = `Loaded ${nodes.length} canonical entities; displaying ${displayedNodeCount}, ${relations.length} directed relations, and ${displayConnectionCount} displayed connections.`;
  }
}

showUnconnectedControl?.addEventListener("change", () => {
  showUnconnected = showUnconnectedControl.checked;
  renderGraph(graphData);
});

async function loadGraph() {
  try {
    if (!globalThis.cytoscape) {
      throw new Error("Cytoscape.js did not load.");
    }
    const graphSource = new URLSearchParams(globalThis.location.search).get("graph") || "./graph-fixture.json";
    const response = await fetch(graphSource, { cache: "no-store" });
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
