"""Intelligence graph mapper: validated source records → Graph Schema V2 objects."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.app.core.graph.edges import GraphEdge
from backend.app.core.graph.entities import IntelligenceReport, Organization, Person
from backend.app.core.graph.enums import DerivationClass, GraphRelationshipType
from synthetic_data.configs import stable_uuid

from ..contracts import (
    IngestionBundle,
    IngestionSummary,
    IssueSeverity,
    ParsedSourceBundle,
    SourceType,
)
from ..identifiers import make_phone_id, make_provisional_person_id, make_relationship_id
from ..normalization import normalize_name


def _edge(source_id: str, target_id: str, edge_type: GraphRelationshipType, source_record_id: str, timestamp: datetime, properties: dict[str, Any] | None = None) -> GraphEdge:
    edge_id = make_relationship_id(source_id, edge_type.value, target_id, source_record_id)
    return GraphEdge(id=edge_id, source_id=source_id, target_id=target_id, edge_type=edge_type, derivation_class=DerivationClass.FACT, source_record_id=source_record_id, created_at=timestamp, properties={"id": edge_id, "source_record_id": source_record_id, **(properties or {})})


def map_intelligence_bundle(
    parsed: ParsedSourceBundle,
    person_id_mapping: dict[str, str] | None = None,
) -> IngestionBundle:
    """Map validated intelligence source records to Graph Schema V2 nodes and edges."""
    id_map = person_id_mapping or {}
    nodes: dict[str, Any] = {}
    relationships: dict[str, GraphEdge] = {}
    subject_ids: dict[str, str] = {}
    report_ids: dict[str, str] = {}

    for row in parsed.rows:
        report_id_value = row["report_id"]
        report_date = row["report_date"]
        source_record_id = row["source_record_id"]
        phone = row["phone"]
        national_id = row["national_id"]
        organization = row["organization"]

        # Report node
        report_node_id = report_ids.setdefault(report_id_value, str(stable_uuid("intelligence_report", report_id_value)))
        if report_node_id not in nodes:
            nodes[report_node_id] = IntelligenceReport(id=report_node_id, report_id=report_id_value, title=f"Intelligence report {report_id_value}", source_agency=row["source_agency"], classification_level=row["classification"], published_date=report_date, summary=row["summary"], created_at=report_date, updated_at=report_date)

        # Subject person node
        if national_id:
            subject_key = f"national:{national_id}"
        elif phone:
            subject_key = f"phone:{phone}"
        else:
            subject_key = f"record:{row['record_id']}"
        provisional_id = subject_ids.get(subject_key)
        if provisional_id is None:
            provisional_id = make_provisional_person_id(row["record_id"], SourceType.INTEL_REPORT.value)
            subject_ids[subject_key] = provisional_id
            person_id = id_map.get(provisional_id, provisional_id)
            claims = [{"record_id": row["record_id"], "name": row["subject_name"], "normalized_name": row["normalized_name"], "source_record_id": source_record_id}]
            if row["alias"]:
                claims[0]["alias"] = row["alias"]
            if phone:
                claims[0]["phone_number"] = phone
            if national_id:
                claims[0]["national_id"] = national_id
            nodes[person_id] = Person(id=person_id, full_name=row["subject_name"], aliases=[row["raw_alias"]] if row["raw_alias"] else [], phone_numbers=[phone] if phone else [], national_id=national_id or None, created_at=report_date, updated_at=report_date, attributes={"identity_claims": claims})
        else:
            person_id = id_map.get(provisional_id, provisional_id)
            claims = list(nodes[person_id].attributes.get("identity_claims", []))
            claims.append({"record_id": row["record_id"], "name": row["subject_name"], "normalized_name": row["normalized_name"], "alias": row["alias"] or None, "phone_number": phone or None, "source_record_id": source_record_id})
            nodes[person_id].attributes["identity_claims"] = claims
            nodes[person_id].properties = dict(nodes[person_id].attributes)

        # MENTIONED_IN edge
        mention = _edge(person_id, report_node_id, GraphRelationshipType.MENTIONED_IN, source_record_id, report_date, {"mention_type": "reported_subject"})
        relationships[mention.id or ""] = mention
        report = nodes[report_node_id]
        if person_id not in report.mentioned_person_ids:
            report.mentioned_person_ids.append(person_id)
            report.properties = dict(report.attributes)

        # Organization node and edge
        if organization:
            organization_id = str(stable_uuid("organization", normalize_name(organization)))
            nodes.setdefault(organization_id, Organization(id=organization_id, name=organization, created_at=report_date, updated_at=report_date))
            associated = _edge(person_id, organization_id, GraphRelationshipType.ASSOCIATED_WITH, source_record_id, report_date, {"explicit_from_field": "organization"})
            relationships[associated.id or ""] = associated

    summary = parsed.summary.model_copy(update={
        "node_created_count": len(nodes),
        "relationship_created_count": len(relationships),
    })
    return IngestionBundle(
        batch_id=parsed.batch_id,
        source_type=SourceType.INTEL_REPORT,
        file_name=parsed.file_name,
        source_records=parsed.source_records,
        nodes=list(nodes.values()),
        relationships=list(relationships.values()),
        issues=parsed.issues,
        summary=summary,
    )


__all__ = ["map_intelligence_bundle"]
