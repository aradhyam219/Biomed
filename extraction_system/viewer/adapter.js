/**
 * Adapt the frontend-neutral graph JSON contract to Cytoscape elements.
 *
 * The adapter keeps domain metadata in each element's data object so the
 * viewer can inspect source mentions and evidence without reconstructing or
 * reinterpreting backend values.
 */

const DEFAULT_TYPE = "Unknown";
const PAIR_LANE_SPACING = 96;

/**
 * Return a stable CSS-safe key for an entity type without changing its label.
 *
 * @param {unknown} value
 * @returns {string}
 */
export function entityTypeKey(value) {
  const normalized = String(value ?? DEFAULT_TYPE)
    .trim()
    .replace(/([a-z])([A-Z])/g, "$1-$2")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return normalized || "unknown";
}

function arrayOrEmpty(value) {
  return Array.isArray(value) ? value : [];
}

function unconnectedNodeIds(nodes, relations) {
  const connectedIds = new Set();
  for (const relation of relations) {
    connectedIds.add(String(relation?.source ?? ""));
    connectedIds.add(String(relation?.target ?? ""));
  }
  return new Set(
    nodes
      .filter((node) => !connectedIds.has(String(node?.id ?? "")))
      .map((node) => String(node?.id ?? "")),
  );
}

function displayNodeSelection(nodes, relations, options = {}) {
  const canonicalUnconnectedIds = unconnectedNodeIds(nodes, relations);
  const revealedNodeIds = new Set(
    arrayOrEmpty(options?.revealedNodeIds).map((nodeId) => String(nodeId)),
  );
  const showUnconnected = options?.showUnconnected === true;
  const displayedUnconnectedIds = showUnconnected
    ? canonicalUnconnectedIds
    : new Set(
        [...canonicalUnconnectedIds].filter((nodeId) => revealedNodeIds.has(nodeId)),
      );
  const displayedNodeIds = new Set(
    nodes
      .map((node) => String(node?.id ?? ""))
      .filter((nodeId) => !canonicalUnconnectedIds.has(nodeId) || displayedUnconnectedIds.has(nodeId)),
  );
  const canonicalNodeIds = new Set(
    nodes.map((node) => String(node?.id ?? "")),
  );
  const displayedNodes = nodes.filter((node) => displayedNodeIds.has(String(node?.id ?? "")));
  const displayedRelations = relations.filter(
    (relation) =>
      (!canonicalNodeIds.has(String(relation?.source ?? "")) ||
        displayedNodeIds.has(String(relation?.source ?? ""))) &&
      (!canonicalNodeIds.has(String(relation?.target ?? "")) ||
        displayedNodeIds.has(String(relation?.target ?? ""))),
  );
  return {
    canonicalUnconnectedIds,
    displayedUnconnectedIds,
    displayedNodes,
    displayedRelations,
    hiddenUnconnectedCount: canonicalUnconnectedIds.size - displayedUnconnectedIds.size,
  };
}

function compactPredicate(value) {
  const predicate = String(value ?? "");
  return predicate.length > 28 ? `${predicate.slice(0, 25).trimEnd()}…` : predicate;
}

function directionalRelationKey(source, target) {
  return JSON.stringify([source, target]);
}

function unorderedPairKey(source, target) {
  return JSON.stringify([source, target].sort());
}

function groupDirectionalRelations(edges) {
  const groups = new Map();
  for (const edge of edges) {
    const source = String(edge?.source ?? "");
    const target = String(edge?.target ?? "");
    const key = directionalRelationKey(source, target);
    let group = groups.get(key);
    if (!group) {
      group = { source, target, relations: [] };
      groups.set(key, group);
    }
    group.relations.push(edge);
  }
  return [...groups.values()];
}

function sharedNegation(relations) {
  if (relations.length === 0) return null;
  const first = relations[0]?.negated === true;
  return relations.every((relation) => (relation?.negated === true) === first)
    ? first
    : null;
}

function edgeRoutingMetadata(edges) {
  const positions = new Map();
  const totals = new Map();
  for (const edge of edges) {
    const source = String(edge?.source ?? "");
    const target = String(edge?.target ?? "");
    const key = unorderedPairKey(source, target);
    totals.set(key, (totals.get(key) ?? 0) + 1);
  }

  return edges.map((edge) => {
    const source = String(edge?.source ?? "");
    const target = String(edge?.target ?? "");
    const key = unorderedPairKey(source, target);
    const position = positions.get(key) ?? 0;
    positions.set(key, position + 1);
    const total = totals.get(key) ?? 1;
    const midpoint = (total - 1) / 2;
    const laneDistance = source === target ? 0 : (position - midpoint) * PAIR_LANE_SPACING;
    const directionSign = source === target ? 0 : source < target ? 1 : -1;
    return {
      pairKey: key,
      pairLane: position,
      pairLaneCount: total,
      curveDistance: laneDistance,
      controlPointDistance: laneDistance * directionSign,
      labelOffset: source === target ? 0 : (position - midpoint) * 20,
    };
  });
}

/**
 * Build the viewer-only display model without changing graph semantics.
 *
 * Relations are grouped only when both their source and target IDs match. Each
 * display edge retains the original relation objects under `relations`, while
 * the source graph remains responsible for the underlying relation count.
 *
 * @param {object | null | undefined} graph
 * @returns {{nodes: Array<object>, edges: Array<object>, relationCount: number}}
 */
export function buildDisplayModel(graph, options = {}) {
  const canonicalNodes = arrayOrEmpty(graph?.nodes);
  const canonicalRelations = arrayOrEmpty(graph?.edges);
  const selection = displayNodeSelection(canonicalNodes, canonicalRelations, options);
  const nodes = selection.displayedNodes;
  const relations = selection.displayedRelations;
  const groups = groupDirectionalRelations(relations);
  const displayEdges = groups.map((group, index) => {
    const groupRelations = group.relations;
    const firstRelation = groupRelations[0] ?? {};
    const isBundle = groupRelations.length > 1;
    const negated = sharedNegation(groupRelations);

    return {
      ...(isBundle ? {} : firstRelation),
      id: isBundle
        ? `bundle-${String(index + 1).padStart(3, "0")}`
        : String(firstRelation?.id ?? ""),
      source: group.source,
      target: group.target,
      predicate: isBundle ? "" : String(firstRelation?.predicate ?? ""),
      predicateLabel: isBundle
        ? `${groupRelations.length} relations`
        : compactPredicate(firstRelation?.predicate),
      relationCount: groupRelations.length,
      isBundle,
      relations: groupRelations,
      relationIds: groupRelations.map((relation) => String(relation?.id ?? "")),
      negated,
      negationState: negated === null ? "mixed" : negated ? "negated" : "affirmed",
      evidence: isBundle ? [] : arrayOrEmpty(firstRelation?.evidence),
    };
  });
  const routing = edgeRoutingMetadata(displayEdges);

  return {
    nodes,
    edges: displayEdges.map((edge, index) => ({ ...edge, ...routing[index] })),
    relationCount: canonicalRelations.length,
    displayedRelationCount: relations.length,
    canonicalNodeCount: canonicalNodes.length,
    displayedNodeCount: nodes.length,
    unconnectedNodeCount: selection.canonicalUnconnectedIds.size,
    hiddenUnconnectedCount: selection.hiddenUnconnectedCount,
    displayedUnconnectedIds: [...selection.displayedUnconnectedIds],
  };
}

/**
 * Convert graph JSON nodes and edges into Cytoscape's element shape.
 *
 * Direction is copied directly to `source` and `target`. All domain metadata
 * is retained under `data`, while the generated classes only control visual
 * presentation (entity shape, bundle styling, and negated-edge styling).
 *
 * @param {object | null | undefined} graph
 * @returns {Array<object>}
 */
export function toCytoscapeElements(graph, options = {}) {
  const { nodes, edges } = buildDisplayModel(graph, options);

  const nodeElements = nodes.map((node) => {
    const type = String(node?.type ?? DEFAULT_TYPE);
    const label = String(node?.label ?? node?.id ?? "");
    return {
      group: "nodes",
      data: {
        ...node,
        id: String(node?.id ?? ""),
        label,
        type,
        aliases: arrayOrEmpty(node?.aliases),
        mentions: arrayOrEmpty(node?.mentions),
      },
      classes: `entity-node entity-type-${entityTypeKey(type)}`,
    };
  });

  const edgeElements = edges.map((edge) => {
    const negated = edge?.negated === true;
    const displayNegated = edge?.negationState === "mixed" ? null : negated;
    const source = String(edge?.source ?? "");
    const target = String(edge?.target ?? "");
    return {
      group: "edges",
      data: {
        ...edge,
        id: String(edge?.id ?? ""),
        source,
        target,
        predicate: String(edge?.predicate ?? ""),
        predicateLabel: String(edge?.predicateLabel ?? compactPredicate(edge?.predicate)),
        relationCount: Number(edge?.relationCount ?? 1),
        isBundle: edge?.isBundle === true,
        relations: arrayOrEmpty(edge?.relations),
        relationIds: arrayOrEmpty(edge?.relationIds),
        negationState: String(edge?.negationState ?? (negated ? "negated" : "affirmed")),
        pairKey: String(edge?.pairKey ?? ""),
        pairLane: Number(edge?.pairLane ?? 0),
        pairLaneCount: Number(edge?.pairLaneCount ?? 1),
        curveDistance: Number(edge?.curveDistance ?? 0),
        controlPointDistance: Number(edge?.controlPointDistance ?? edge?.curveDistance ?? 0),
        labelOffset: Number(edge?.labelOffset ?? 0),
        negated: displayNegated,
        evidence: arrayOrEmpty(edge?.evidence),
      },
      classes: `relation-edge${edge?.isBundle ? " bundle-edge" : ""}${negated ? " negated" : ""}${source === target ? " self-edge" : ""}`,
    };
  });

  return [...nodeElements, ...edgeElements];
}
