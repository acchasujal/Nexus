"""CDR graph mapper: validated source records → Graph Schema V2 objects."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.app.core.graph.edges import GraphEdge
from backend.app.core.graph.entities import Person, Phone
from backend.app.core.graph.enums import DerivationClass, GraphRelationshipType

from ..contracts import (
    IngestionBundle,
    ParsedSourceBundle,
    SourceType,
)
from ..identifiers import (
    make_phone_id,
    make_provisional_person_id,
    make_relationship_id,
)


def _edge(
    source_id: str,
    target_id: str,
    edge_type: GraphRelationshipType,
    source_record_id: str,
    occurred_at: datetime,
    properties: dict[str, Any],
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> GraphEdge:
    edge_id = make_relationship_id(source_id, edge_type.value, target_id, source_record_id)
    edge_properties = {
        "id": edge_id,
        "source_record_id": source_record_id,
        "start_time": start_time,
        "end_time": end_time,
        **properties,
    }
    return GraphEdge(
        id=edge_id,
        source_id=source_id,
        target_id=target_id,
        edge_type=edge_type,
        start_time=start_time,
        end_time=end_time,
        derivation_class=DerivationClass.FACT,
        source_record_id=source_record_id,
        created_at=occurred_at,
        properties=edge_properties,
    )


def map_cdr_bundle(
    parsed: ParsedSourceBundle,
    person_id_mapping: dict[str, str] | None = None,
) -> IngestionBundle:
    """Map validated CDR source records to Graph Schema V2 nodes and edges."""
    id_map = person_id_mapping or {}
    nodes: dict[str, Any] = {}
    relationships: dict[str, GraphEdge] = {}
    kyc_persons: dict[str, str] = {}

    for row in parsed.rows:
        start_time = row["start_time"]
        end_time = row["end_time"]
        caller_id = make_phone_id(row["caller"])
        callee_id = make_phone_id(row["callee"])
        source_record_id = row["source_record_id"]

        nodes.setdefault(caller_id, Phone(id=caller_id, phone_number=row["caller"], imei=row["caller_imei"] or None, created_at=start_time, updated_at=start_time))
        nodes.setdefault(callee_id, Phone(id=callee_id, phone_number=row["callee"], imei=row["callee_imei"] or None, created_at=start_time, updated_at=start_time))

        call_properties: dict[str, Any] = {
            "duration_seconds": row["duration"],
            "call_type": row["call_type"],
            "timestamp": start_time,
        }
        if row["caller_imei"]:
            call_properties["caller_imei"] = row["caller_imei"]
        if row["callee_imei"]:
            call_properties["callee_imei"] = row["callee_imei"]
        if row["cell_location"]:
            call_properties["cell_location"] = row["cell_location"]
        if end_time is not None:
            call_properties["end_time"] = end_time
        call = _edge(caller_id, callee_id, GraphRelationshipType.COMMUNICATED_WITH, source_record_id, start_time, call_properties, start_time=start_time, end_time=end_time)
        relationships[call.id or ""] = call

        for side, phone_id in (("caller", caller_id), ("callee", callee_id)):
            subscriber_name = row.get(f"{side}_subscriber_name", "")
            national_id = row.get(f"{side}_national_id", "")
            if not subscriber_name and not national_id:
                continue
            identity_key = f"national:{national_id}" if national_id else f"record:{row['record_id']}:{side}"
            provisional_id = kyc_persons.get(identity_key)
            if provisional_id is None:
                provisional_id = make_provisional_person_id(f"{row['record_id']}:{side}", SourceType.CDR.value)
                kyc_persons[identity_key] = provisional_id
                person_id = id_map.get(provisional_id, provisional_id)
                nodes[person_id] = Person(
                    id=person_id,
                    full_name=subscriber_name,
                    national_id=national_id or None,
                    created_at=start_time,
                    updated_at=start_time,
                    attributes={"identity_claims": [{"record_id": row["record_id"], "name": subscriber_name, "national_id": national_id or None, "source_record_id": source_record_id}]},
                )
            else:
                person_id = id_map.get(provisional_id, provisional_id)
            relationships.setdefault(
                make_relationship_id(person_id, GraphRelationshipType.USED_PHONE.value, phone_id, source_record_id),
                _edge(person_id, phone_id, GraphRelationshipType.USED_PHONE, source_record_id, start_time, {"identity_claim": True}),
            )

    summary = parsed.summary.model_copy(update={
        "node_created_count": len(nodes),
        "relationship_created_count": len(relationships),
    })
    return IngestionBundle(
        batch_id=parsed.batch_id,
        source_type=SourceType.CDR,
        file_name=parsed.file_name,
        source_records=parsed.source_records,
        nodes=list(nodes.values()),
        relationships=list(relationships.values()),
        issues=parsed.issues,
        summary=summary,
    )


__all__ = ["map_cdr_bundle"]
