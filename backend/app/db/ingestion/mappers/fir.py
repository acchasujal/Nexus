"""FIR graph mapper: validated source records → Graph Schema V2 objects."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.app.core.graph.edges import GraphEdge
from backend.app.core.graph.entities import Case, Person, Phone, Vehicle
from backend.app.core.graph.enums import DerivationClass, GraphRelationshipType

from ..contracts import (
    IngestionBundle,
    IngestionSummary,
    IssueSeverity,
    ParsedSourceBundle,
    SourceType,
)
from ..identifiers import (
    make_case_id,
    make_phone_id,
    make_provisional_person_id,
    make_relationship_id,
    make_vehicle_id,
)

ROLE_RELATIONSHIPS = {
    "ACCUSED": GraphRelationshipType.ACCUSED_IN,
    "VICTIM": GraphRelationshipType.VICTIM_IN,
    "COMPLAINANT": GraphRelationshipType.COMPLAINANT_IN,
    "WITNESS": GraphRelationshipType.WITNESS_IN,
}


def _fact_edge(
    source_id: str,
    target_id: str,
    edge_type: GraphRelationshipType,
    source_record_id: str,
    created_at: datetime,
    properties: dict[str, Any] | None = None,
) -> GraphEdge:
    return GraphEdge(
        id=make_relationship_id(source_id, edge_type.value, target_id, source_record_id),
        source_id=source_id,
        target_id=target_id,
        edge_type=edge_type,
        derivation_class=DerivationClass.FACT,
        source_record_id=source_record_id,
        created_at=created_at,
        properties=properties or {},
    )


def map_fir_bundle(
    parsed: ParsedSourceBundle,
    person_id_mapping: dict[str, str] | None = None,
) -> IngestionBundle:
    """Map validated FIR source records to Graph Schema V2 nodes and edges.

    Parameters
    ----------
    parsed:
        The output of the FIR parser containing validated rows and source records.
    person_id_mapping:
        Optional ``provisional_person_id → canonical_person_id`` mapping.
        When ``None``, provisional IDs are used directly.
    """
    id_map = person_id_mapping or {}
    nodes: dict[str, Any] = {}
    relationships: dict[str, GraphEdge] = {}
    person_keys: dict[str, str] = {}
    case_keys: dict[str, str] = {}

    for row in parsed.rows:
        role = row["role"]
        incident_time = row["incident_time"]
        phone = row["phone"]
        vehicle = row["vehicle"]
        national_id = row["national_id"]
        source_record_id = row["source_record_id"]

        # Case node
        case_key = (row["station_name"].upper(), row["fir_number"].upper(), row["fir_year"])
        case_id = case_keys.setdefault("|".join(case_key), make_case_id("|".join(case_key)))
        if case_id not in nodes:
            nodes[case_id] = Case(
                id=case_id,
                fir_number=row["fir_number"],
                title=f"FIR {row['fir_number']}",
                station_name=row["station_name"],
                district=row["district"],
                offence_category=row["offence_category"],
                incident_date=incident_time,
                created_at=incident_time,
                updated_at=incident_time,
                sections=[row["section"]] if row["section"] else [],
            )

        # Person node with provisional ID
        identity_key = f"national:{national_id}" if national_id else f"phone:{phone}" if phone else f"provisional:{row['record_id']}"
        provisional_id = person_keys.get(identity_key)
        if provisional_id is None:
            provisional_id = make_provisional_person_id(row["record_id"], SourceType.FIR.value)
            person_keys[identity_key] = provisional_id
            person_id = id_map.get(provisional_id, provisional_id)
            nodes[person_id] = Person(
                id=person_id,
                full_name=row["raw_person_name"],
                phone_numbers=[phone] if phone else [],
                addresses=[row["raw_address"]] if row["raw_address"] else [],
                national_id=national_id or None,
                role_in_case=role,
                created_at=incident_time,
                updated_at=incident_time,
                attributes={"identity_claims": [{"record_id": row["record_id"], "name": row["raw_person_name"], "source_record_id": source_record_id}]},
            )
        else:
            person_id = id_map.get(provisional_id, provisional_id)
            claims = list(nodes[person_id].attributes.get("identity_claims", []))
            claims.append({"record_id": row["record_id"], "name": row["raw_person_name"], "source_record_id": source_record_id})
            nodes[person_id].attributes["identity_claims"] = claims
            nodes[person_id].properties = dict(nodes[person_id].attributes)

        person_id = id_map.get(provisional_id, provisional_id)

        # Person → Case relationship
        relationships.setdefault(
            make_relationship_id(person_id, ROLE_RELATIONSHIPS[role].value, case_id, source_record_id),
            _fact_edge(person_id, case_id, ROLE_RELATIONSHIPS[role], source_record_id, incident_time, {"role": role}),
        )

        # Phone node and edge
        if phone:
            phone_id = make_phone_id(phone)
            nodes.setdefault(phone_id, Phone(id=phone_id, phone_number=phone, created_at=incident_time, updated_at=incident_time))
            relationships.setdefault(make_relationship_id(person_id, GraphRelationshipType.USED_PHONE.value, phone_id, source_record_id), _fact_edge(person_id, phone_id, GraphRelationshipType.USED_PHONE, source_record_id, incident_time))

        # Vehicle node and edge
        if vehicle:
            vehicle_id = make_vehicle_id(vehicle)
            nodes.setdefault(vehicle_id, Vehicle(id=vehicle_id, registration_number=vehicle, created_at=incident_time, updated_at=incident_time))
            relationships.setdefault(make_relationship_id(person_id, GraphRelationshipType.USED_VEHICLE.value, vehicle_id, source_record_id), _fact_edge(person_id, vehicle_id, GraphRelationshipType.USED_VEHICLE, source_record_id, incident_time))

    summary = parsed.summary.model_copy(update={
        "node_created_count": len(nodes),
        "relationship_created_count": len(relationships),
    })
    return IngestionBundle(
        batch_id=parsed.batch_id,
        source_type=SourceType.FIR,
        file_name=parsed.file_name,
        source_records=parsed.source_records,
        nodes=list(nodes.values()),
        relationships=list(relationships.values()),
        issues=parsed.issues,
        summary=summary,
    )


__all__ = ["map_fir_bundle"]
