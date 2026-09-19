"""Surveillance graph mapper: validated surveillance source records → Graph Schema V2 objects."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.app.core.graph.edges import EvidenceProvenance, GraphEdge
from backend.app.core.graph.entities import Location, Organization, Person, Phone, Vehicle
from backend.app.core.graph.enums import DerivationClass, GraphRelationshipType
from synthetic_data.configs import stable_uuid

from ..contracts import (
    IngestionBundle,
    ParsedSourceBundle,
    SourceType,
)
from ..identifiers import (
    make_phone_id,
    make_provisional_person_id,
    make_relationship_id,
    make_vehicle_id,
)
from ..normalization import normalize_name


def _edge(
    source_id: str,
    target_id: str,
    edge_type: GraphRelationshipType,
    source_record_id: str,
    timestamp: datetime,
    fact: str,
    report_id: str,
    record_id: str = "",
    properties: dict[str, Any] | None = None,
) -> GraphEdge:
    edge_id = make_relationship_id(source_id, edge_type.value, target_id, source_record_id)
    props = {
        "id": edge_id,
        "source_record_id": source_record_id,
        "report_id": report_id,
        "observation_id": record_id,
        **(properties or {}),
    }
    provenance = EvidenceProvenance(
        source_type="SURVEILLANCE_REPORT",
        source_id=report_id,
        source_record_id=source_record_id,
        timestamp=timestamp,
        extracted_fact=fact,
        derivation_method="SURVEILLANCE_OBSERVATION",
        derivation_class=DerivationClass.FACT,
        confidence=1.0,
    )
    return GraphEdge(
        id=edge_id,
        source_id=source_id,
        target_id=target_id,
        edge_type=edge_type,
        start_time=timestamp,
        derivation_class=DerivationClass.FACT,
        source_record_id=source_record_id,
        created_at=timestamp,
        provenance=provenance,
        properties=props,
    )


def map_surveillance_bundle(
    parsed: ParsedSourceBundle,
    person_id_mapping: dict[str, str] | None = None,
) -> IngestionBundle:
    """Map validated surveillance source records to Graph Schema V2 nodes and edges."""
    id_map = person_id_mapping or {}
    nodes: dict[str, Any] = {}
    relationships: dict[str, GraphEdge] = {}
    subject_ids: dict[str, str] = {}

    for row in parsed.rows:
        record_id = row["record_id"]
        report_id = row["report_id"]
        case_id = row["case_id"]
        observed_at = row["observed_at"]
        subject_name = row["subject_name"]
        normalized_name = row["normalized_name"]
        observation_type = row["observation_type"]
        location_str = row["location"]
        summary = row["summary"]
        phone = row.get("phone_number", "")
        vehicle = row.get("vehicle_registration", "")
        national_id = row.get("national_id", "")
        organization = row.get("organization", "")
        source_record_id = row["source_record_id"]
        officer_badge = row.get("officer_badge", "")
        source_agency = row.get("source_agency", "")
        source_reference = row.get("source_reference", "")

        # 1. Subject Person Node
        if national_id:
            subject_key = f"national:{national_id}"
        elif phone:
            subject_key = f"phone:{phone}"
        elif vehicle:
            subject_key = f"vehicle:{vehicle}"
        else:
            subject_key = f"record:{record_id}"

        provisional_id = subject_ids.get(subject_key)
        if provisional_id is None:
            provisional_id = make_provisional_person_id(record_id, SourceType.SURVEILLANCE_REPORT.value)
            subject_ids[subject_key] = provisional_id
            person_id = id_map.get(provisional_id, provisional_id)
            claims = [{
                "record_id": record_id,
                "name": subject_name,
                "normalized_name": normalized_name,
                "source_record_id": source_record_id,
            }]
            if phone:
                claims[0]["phone_number"] = phone
            if vehicle:
                claims[0]["vehicle_number"] = vehicle
            if national_id:
                claims[0]["national_id"] = national_id

            attrs = {
                "identity_claims": claims,
                "name": subject_name,
                "full_name": subject_name,
            }
            person_node = Person(
                id=person_id,
                full_name=subject_name,
                phone_numbers=[phone] if phone else [],
                vehicles=[vehicle] if vehicle else [],
                addresses=[location_str] if location_str else [],
                national_id=national_id or None,
                case_ids=[case_id] if case_id else [],
                created_at=observed_at,
                updated_at=observed_at,
                attributes=attrs,
                properties=dict(attrs),
            )
            nodes[person_id] = person_node
        else:
            person_id = id_map.get(provisional_id, provisional_id)
            person_node = nodes[person_id]
            claims = list(person_node.attributes.get("identity_claims", []))
            claims.append({
                "record_id": record_id,
                "name": subject_name,
                "normalized_name": normalized_name,
                "phone_number": phone or None,
                "vehicle_number": vehicle or None,
                "national_id": national_id or None,
                "source_record_id": source_record_id,
            })
            person_node.attributes["identity_claims"] = claims
            if phone and phone not in person_node.phone_numbers:
                person_node.phone_numbers.append(phone)
            if vehicle and vehicle not in person_node.vehicles:
                person_node.vehicles.append(vehicle)
            if location_str and location_str not in person_node.addresses:
                person_node.addresses.append(location_str)
            if case_id and case_id not in person_node.case_ids:
                person_node.case_ids.append(case_id)
            person_node.properties = dict(person_node.attributes)

        # 2. Location Node & SEEN_AT Edge
        if location_str:
            location_id = str(stable_uuid("location", normalize_name(location_str)))
            if location_id not in nodes:
                nodes[location_id] = Location(
                    id=location_id,
                    name=location_str,
                    address=location_str,
                    created_at=observed_at,
                    updated_at=observed_at,
                )

            seen_edge = _edge(
                source_id=person_id,
                target_id=location_id,
                edge_type=GraphRelationshipType.SEEN_AT,
                source_record_id=source_record_id,
                timestamp=observed_at,
                fact=f"Subject {subject_name} observed at {location_str} in surveillance report {report_id}",
                report_id=report_id,
                record_id=record_id,
                properties={
                    "case_id": case_id,
                    "observation_type": observation_type,
                    "summary": summary,
                    "officer_badge": officer_badge,
                    "source_agency": source_agency,
                    "source_reference": source_reference,
                },
            )
            relationships[seen_edge.id or ""] = seen_edge

        # 3. Vehicle Node & USED_VEHICLE Edge
        if vehicle:
            vehicle_id = make_vehicle_id(vehicle)
            if vehicle_id not in nodes:
                nodes[vehicle_id] = Vehicle(
                    id=vehicle_id,
                    registration_number=vehicle,
                    created_at=observed_at,
                    updated_at=observed_at,
                )

            used_vehicle_edge = _edge(
                source_id=person_id,
                target_id=vehicle_id,
                edge_type=GraphRelationshipType.USED_VEHICLE,
                source_record_id=source_record_id,
                timestamp=observed_at,
                fact=f"Subject {subject_name} observed with vehicle {vehicle} in surveillance report {report_id}",
                report_id=report_id,
                record_id=record_id,
                properties={
                    "case_id": case_id,
                    "observation_type": observation_type,
                    "summary": summary,
                    "source_reference": source_reference,
                },
            )
            relationships[used_vehicle_edge.id or ""] = used_vehicle_edge

        # 4. Phone Node & USED_PHONE Edge
        if phone:
            phone_id = make_phone_id(phone)
            if phone_id not in nodes:
                nodes[phone_id] = Phone(
                    id=phone_id,
                    phone_number=phone,
                    created_at=observed_at,
                    updated_at=observed_at,
                )

            used_phone_edge = _edge(
                source_id=person_id,
                target_id=phone_id,
                edge_type=GraphRelationshipType.USED_PHONE,
                source_record_id=source_record_id,
                timestamp=observed_at,
                fact=f"Subject {subject_name} observed using phone {phone} in surveillance report {report_id}",
                report_id=report_id,
                record_id=record_id,
                properties={
                    "case_id": case_id,
                    "observation_type": observation_type,
                    "summary": summary,
                    "source_reference": source_reference,
                },
            )
            relationships[used_phone_edge.id or ""] = used_phone_edge

        # 5. Organization Node & ASSOCIATED_WITH Edge
        if organization:
            org_id = str(stable_uuid("organization", normalize_name(organization)))
            if org_id not in nodes:
                nodes[org_id] = Organization(
                    id=org_id,
                    name=organization,
                    created_at=observed_at,
                    updated_at=observed_at,
                )

            assoc_edge = _edge(
                source_id=person_id,
                target_id=org_id,
                edge_type=GraphRelationshipType.ASSOCIATED_WITH,
                source_record_id=source_record_id,
                timestamp=observed_at,
                fact=f"Subject {subject_name} observed in connection with {organization} in surveillance report {report_id}",
                report_id=report_id,
                record_id=record_id,
                properties={
                    "case_id": case_id,
                    "observation_type": observation_type,
                    "summary": summary,
                },
            )
            relationships[assoc_edge.id or ""] = assoc_edge

    summary_stats = parsed.summary.model_copy(update={
        "node_created_count": len(nodes),
        "relationship_created_count": len(relationships),
    })

    return IngestionBundle(
        batch_id=parsed.batch_id,
        source_type=SourceType.SURVEILLANCE_REPORT,
        file_name=parsed.file_name,
        source_records=parsed.source_records,
        nodes=list(nodes.values()),
        relationships=list(relationships.values()),
        review_candidates=[],
        issues=parsed.issues,
        summary=summary_stats,
    )
