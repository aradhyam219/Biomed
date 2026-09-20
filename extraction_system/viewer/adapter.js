/**
 * Adapt the frontend-neutral graph JSON contract to Cytoscape elements.
 *
 * The adapter keeps domain metadata in each element's data object so the
 * viewer can inspect source mentions and evidence without reconstructing or
 * reinterpreting backend values.
 */

const DEFAULT_TYPE = "Unknown";

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

function compactPredicate(value) {
  const predicate = String(value ?? "");
  return predicate.length > 28 ? `${predicate.slice(0, 25).trimEnd()}…` : predicate;
}

function edgeCurveDistances(edges) {
  const positions = new Map();
  const totals = new Map();
  for (const edge of edges) {
    const source = String(edge?.source ?? "");
    const target = String(edge?.target ?? "");
    const key = `${source}->${target}`;
    totals.set(key, (totals.get(key) ?? 0) + 1);
  }

  return edges.map((edge) => {
    const source = String(edge?.source ?? "");
    const target = String(edge?.target ?? "");
    const key = `${source}->${target}`;
    const position = positions.get(key) ?? 0;
    positions.set(key, position + 1);
    const total = totals.get(key) ?? 1;
    const midpoint = (total - 1) / 2;
    return source === target ? 0 : (position - midpoint) * 48;
  });
}

/**
 * Convert graph JSON nodes and edges into Cytoscape's element shape.
 *
 * Direction is copied directly to `source` and `target`. All domain metadata
 * is retained under `data`, while the generated classes only control visual
 * presentation (entity shape and negated-edge styling).
 *
 * @param {object | null | undefined} graph
 * @returns {Array<object>}
 */
export function toCytoscapeElements(graph) {
  const nodes = arrayOrEmpty(graph?.nodes);
  const edges = arrayOrEmpty(graph?.edges);
  const curveDistances = edgeCurveDistances(edges);

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

  const edgeElements = edges.map((edge, index) => {
    const negated = edge?.negated === true;
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
        predicateLabel: compactPredicate(edge?.predicate),
        curveDistance: curveDistances[index],
        negated,
        evidence: arrayOrEmpty(edge?.evidence),
      },
      classes: `relation-edge${negated ? " negated" : ""}${source === target ? " self-edge" : ""}`,
    };
  });

  return [...nodeElements, ...edgeElements];
}
