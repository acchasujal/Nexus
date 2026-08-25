"""backend/app/core/graph/algorithms/snapshot_diff.py

Deterministic Temporal Graph Snapshot Diff Engine for NEXUS (Schema V2).

Given two investigation graph states (snapshot_before, snapshot_after), this engine
performs a pure, non-mutating $O(N + E)$ structural and metadata comparison to identify
what changed between them.

Key Principles & Contract Non-Negotiables:
1. PURE COMPARISON: Does NOT mutate before_store or after_store.
2. IDENTITY: Node identity is strictly Node.id / node_id. Relationship identity is
   Relationship.id / (source_id, edge_type, target_id). Does NOT perform entity resolution.
3. SEMANTIC EQUALITY: Ignores dictionary key insertion order and alias ordering to prevent
   false-positive change signals.
4. PROVENANCE: Preserves real source_record_id attributes without fabricating evidence.
5. SAFETY: Pure structural natural descriptions. Zero predictive guilt / criminality / risk inferencing.
6. DETERMINISTIC: All returned lists and field changes are deterministically sorted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from backend.app.core.graph.algorithms.utils import GraphStore

# ── Diff Result Data Models ───────────────────────────────────────────────────

@dataclass
class NodeFieldChange:
    """Individual field change for a modified node."""
    field: str
    before: Any
    after: Any


@dataclass
class NodeDiffRecord:
    """Modification detail for a single node."""
    node_id: str
    entity_type: str
    changed_fields: list[str]
    changes: list[NodeFieldChange] = field(default_factory=list)


@dataclass
class RelationshipFieldChange:
    """Individual field change for a modified relationship."""
    field: str
    before: Any
    after: Any


@dataclass
class RelationshipDiffRecord:
    """Modification detail for a single relationship."""
    relationship_id: str
    edge_type: str
    source_id: str
    target_id: str
    source_record_id: str | None
    changed_fields: list[str]
    changes: list[RelationshipFieldChange] = field(default_factory=list)


@dataclass
class DiffSummaryMetrics:
    """Summary counts of graph changes."""
    added_node_count: int = 0
    removed_node_count: int = 0
    modified_node_count: int = 0
    added_relationship_count: int = 0
    removed_relationship_count: int = 0
    modified_relationship_count: int = 0
    added_nodes_by_type: dict[str, int] = field(default_factory=dict)
    removed_nodes_by_type: dict[str, int] = field(default_factory=dict)


@dataclass
class GraphSnapshotDiff:
    """
    Complete structural and metadata diff between two graph snapshots.
    """
    added_nodes: list[str] = field(default_factory=list)
    removed_nodes: list[str] = field(default_factory=list)
    modified_nodes: list[NodeDiffRecord] = field(default_factory=list)
    added_relationships: list[str] = field(default_factory=list)
    removed_relationships: list[str] = field(default_factory=list)
    modified_relationships: list[RelationshipDiffRecord] = field(default_factory=list)
    summary: DiffSummaryMetrics = field(default_factory=DiffSummaryMetrics)


# ── Helpers for Semantic Comparison ─────────────────────────────────────────

def _normalize_val(val: Any) -> Any:
    """Recursively normalize values for semantic equality comparison."""
    if isinstance(val, dict):
        return {k: _normalize_val(v) for k, v in sorted(val.items())}
    if isinstance(val, (list, tuple, set)):
        # Treat lists of strings (e.g. aliases) as unordered sets where appropriate
        if all(isinstance(x, str) for x in val):
            return sorted(set(val))
        return [_normalize_val(x) for x in val]
    if isinstance(val, datetime):
        return val.isoformat()
    return val


def _are_values_equal(val1: Any, val2: Any) -> bool:
    """Compare two field values for semantic equality."""
    return _normalize_val(val1) == _normalize_val(val2)


def _get_edge_id(edge: Any) -> str:
    """Extract stable relationship ID."""
    props = getattr(edge, "properties", {}) or {}
    if "properties" in props and isinstance(props["properties"], dict):
        props = {**props, **props["properties"]}
    return (
        props.get("id")
        or getattr(edge, "id", None)
        or f"rel_{edge.source_id}_{edge.edge_type}_{edge.target_id}"
    )


def _get_edge_source_record_id(edge: Any) -> str | None:
    """Extract optional source_record_id from relationship."""
    if hasattr(edge, "source_record_id") and edge.source_record_id:
        return str(edge.source_record_id)
    props = getattr(edge, "properties", {}) or {}
    if "properties" in props and isinstance(props["properties"], dict):
        props = {**props, **props["properties"]}
    if props.get("source_record_id"):
        return str(props["source_record_id"])
    prov = props.get("provenance")
    if isinstance(prov, dict) and prov.get("source_record_id"):
        return str(prov["source_record_id"])
    return None


def _get_all_edges_by_id(store: GraphStore) -> dict[str, Any]:
    """Build O(E) dictionary of all unique edges in GraphStore keyed by stable edge ID."""
    edge_map: dict[str, Any] = {}
    for etype in sorted(store.edge_index.keys()):
        for edge in store.edge_index[etype]:
            eid = _get_edge_id(edge)
            if eid not in edge_map:
                edge_map[eid] = edge
    return edge_map


# ── Main Snapshot Diff Engine ─────────────────────────────────────────────────

def diff_graph_snapshots(
    before_store: GraphStore,
    after_store: GraphStore,
) -> GraphSnapshotDiff:
    """
    Compare two GraphStore instances (snapshot_before, snapshot_after) and return
    a deterministic GraphSnapshotDiff detailing node and relationship additions,
    removals, and field modifications.

    Parameters
    ----------
    before_store : GraphStore
        Graph state before changes.
    after_store : GraphStore
        Graph state after changes.

    Returns
    -------
    GraphSnapshotDiff
        Typed, deterministic diff result.
    """
    diff = GraphSnapshotDiff()

    # 1. NODE COMPARISON — O(N)
    before_node_ids = set(before_store.nodes.keys())
    after_node_ids = set(after_store.nodes.keys())

    added_node_ids = sorted(after_node_ids - before_node_ids)
    removed_node_ids = sorted(before_node_ids - after_node_ids)
    common_node_ids = sorted(before_node_ids & after_node_ids)

    diff.added_nodes = added_node_ids
    diff.removed_nodes = removed_node_ids

    # Track added/removed nodes by entity_type
    added_types: dict[str, int] = {}
    for nid in added_node_ids:
        etype = before_store.nodes[nid].entity_type if nid in before_store.nodes else after_store.nodes[nid].entity_type
        if hasattr(etype, "value"):
            etype = etype.value
        added_types[etype] = added_types.get(etype, 0) + 1

    removed_types: dict[str, int] = {}
    for nid in removed_node_ids:
        etype = before_store.nodes[nid].entity_type if nid in before_store.nodes else after_store.nodes[nid].entity_type
        if hasattr(etype, "value"):
            etype = etype.value
        removed_types[etype] = removed_types.get(etype, 0) + 1

    # Check common nodes for field modifications
    modified_node_records: list[NodeDiffRecord] = []

    for nid in common_node_ids:
        n_before = before_store.nodes[nid]
        n_after = after_store.nodes[nid]

        p_before = getattr(n_before, "properties", {}) or {}
        p_after = getattr(n_after, "properties", {}) or {}

        if "properties" in p_before and isinstance(p_before["properties"], dict):
            p_before = {**p_before, **p_before["properties"]}
        if "properties" in p_after and isinstance(p_after["properties"], dict):
            p_after = {**p_after, **p_after["properties"]}

        # Compare top-level attributes and properties
        all_keys = sorted(set(list(p_before.keys()) + list(p_after.keys())))

        changed_fields: list[str] = []
        changes: list[NodeFieldChange] = []

        # Check entity_type
        et_b = n_before.entity_type.value if hasattr(n_before.entity_type, "value") else str(n_before.entity_type)
        et_a = n_after.entity_type.value if hasattr(n_after.entity_type, "value") else str(n_after.entity_type)
        if et_b != et_a:
            changed_fields.append("entity_type")
            changes.append(NodeFieldChange("entity_type", et_b, et_a))

        # Check property keys
        for key in all_keys:
            val_b = p_before.get(key)
            val_a = p_after.get(key)

            if not _are_values_equal(val_b, val_a):
                changed_fields.append(key)
                changes.append(NodeFieldChange(key, val_b, val_a))

        if changed_fields:
            etype = et_a
            modified_node_records.append(
                NodeDiffRecord(
                    node_id=nid,
                    entity_type=etype,
                    changed_fields=sorted(changed_fields),
                    changes=changes,
                )
            )

    modified_node_records.sort(key=lambda r: r.node_id)
    diff.modified_nodes = modified_node_records

    # 2. RELATIONSHIP COMPARISON — O(E)
    before_edges_map = _get_all_edges_by_id(before_store)
    after_edges_map = _get_all_edges_by_id(after_store)

    before_edge_ids = set(before_edges_map.keys())
    after_edge_ids = set(after_edges_map.keys())

    added_edge_ids = sorted(after_edge_ids - before_edge_ids)
    removed_edge_ids = sorted(before_edge_ids - after_edge_ids)
    common_edge_ids = sorted(before_edge_ids & after_edge_ids)

    diff.added_relationships = added_edge_ids
    diff.removed_relationships = removed_edge_ids

    modified_rel_records: list[RelationshipDiffRecord] = []

    for eid in common_edge_ids:
        e_before = before_edges_map[eid]
        e_after = after_edges_map[eid]

        p_b = getattr(e_before, "properties", {}) or {}
        p_a = getattr(e_after, "properties", {}) or {}

        if "properties" in p_b and isinstance(p_b["properties"], dict):
            p_b = {**p_b, **p_b["properties"]}
        if "properties" in p_a and isinstance(p_a["properties"], dict):
            p_a = {**p_a, **p_a["properties"]}

        rel_changed_fields: list[str] = []
        rel_changes: list[RelationshipFieldChange] = []

        # Check endpoints and type
        if e_before.source_id != e_after.source_id:
            rel_changed_fields.append("source_id")
            rel_changes.append(RelationshipFieldChange("source_id", e_before.source_id, e_after.source_id))

        if e_before.target_id != e_after.target_id:
            rel_changed_fields.append("target_id")
            rel_changes.append(RelationshipFieldChange("target_id", e_before.target_id, e_after.target_id))

        et_b = e_before.edge_type.value if hasattr(e_before.edge_type, "value") else str(e_before.edge_type)
        et_a = e_after.edge_type.value if hasattr(e_after.edge_type, "value") else str(e_after.edge_type)
        if et_b != et_a:
            rel_changed_fields.append("edge_type")
            rel_changes.append(RelationshipFieldChange("edge_type", et_b, et_a))

        # Check source_record_id
        src_rec_b = _get_edge_source_record_id(e_before)
        src_rec_a = _get_edge_source_record_id(e_after)
        if src_rec_b != src_rec_a:
            rel_changed_fields.append("source_record_id")
            rel_changes.append(RelationshipFieldChange("source_record_id", src_rec_b, src_rec_a))

        # Check properties
        all_rel_keys = sorted(set(list(p_b.keys()) + list(p_a.keys())))
        for key in all_rel_keys:
            if key in ("id", "source_record_id"):
                continue
            val_b = p_b.get(key)
            val_a = p_a.get(key)
            if not _are_values_equal(val_b, val_a):
                rel_changed_fields.append(key)
                rel_changes.append(RelationshipFieldChange(key, val_b, val_a))

        if rel_changed_fields:
            modified_rel_records.append(
                RelationshipDiffRecord(
                    relationship_id=eid,
                    edge_type=et_a,
                    source_id=e_after.source_id,
                    target_id=e_after.target_id,
                    source_record_id=src_rec_a,
                    changed_fields=sorted(rel_changed_fields),
                    changes=rel_changes,
                )
            )

    modified_rel_records.sort(key=lambda r: r.relationship_id)
    diff.modified_relationships = modified_rel_records

    # 3. METRICS SUMMARY
    diff.summary = DiffSummaryMetrics(
        added_node_count=len(added_node_ids),
        removed_node_count=len(removed_node_ids),
        modified_node_count=len(modified_node_records),
        added_relationship_count=len(added_edge_ids),
        removed_relationship_count=len(removed_edge_ids),
        modified_relationship_count=len(modified_rel_records),
        added_nodes_by_type=added_types,
        removed_nodes_by_type=removed_types,
    )

    return diff
