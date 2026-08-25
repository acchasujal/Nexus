"""Bank graph mapper: validated source records → Graph Schema V2 objects."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.app.core.graph.edges import GraphEdge
from backend.app.core.graph.entities import Account, Person
from backend.app.core.graph.enums import DerivationClass, GraphRelationshipType

from ..contracts import (
    IngestionBundle,
    ParsedSourceBundle,
    SourceType,
)
from ..identifiers import (
    make_account_id,
    make_provisional_person_id,
    make_relationship_id,
)


def _fact_edge(source_id: str, target_id: str, source_record_id: str, timestamp: datetime, properties: dict[str, Any]) -> GraphEdge:
    edge_id = make_relationship_id(source_id, GraphRelationshipType.TRANSFERRED_FUNDS.value, target_id, source_record_id)
    return GraphEdge(
        id=edge_id,
        source_id=source_id,
        target_id=target_id,
        edge_type=GraphRelationshipType.TRANSFERRED_FUNDS,
        start_time=timestamp,
        derivation_class=DerivationClass.FACT,
        source_record_id=source_record_id,
        created_at=timestamp,
        properties={"id": edge_id, "source_record_id": source_record_id, **properties},
    )


def map_bank_bundle(
    parsed: ParsedSourceBundle,
    person_id_mapping: dict[str, str] | None = None,
) -> IngestionBundle:
    """Map validated bank source records to Graph Schema V2 nodes and edges."""
    id_map = person_id_mapping or {}
    nodes: dict[str, Any] = {}
    relationships: dict[str, GraphEdge] = {}
    kyc_persons: dict[str, str] = {}

    for row in parsed.rows:
        timestamp = row["timestamp"]
        source_record_id = row["source_record_id"]
        from_id = make_account_id(row["from_account"])
        to_id = make_account_id(row["to_account"])

        nodes.setdefault(from_id, Account(id=from_id, account_number=row["from_account"], bank_name=row["from_bank"], ifsc_code=row["from_ifsc"] or None, created_at=timestamp, updated_at=timestamp))
        nodes.setdefault(to_id, Account(id=to_id, account_number=row["to_account"], bank_name=row["to_bank"], ifsc_code=row["to_ifsc"] or None, created_at=timestamp, updated_at=timestamp))

        relationship = _fact_edge(from_id, to_id, source_record_id, timestamp, {"utr": row["utr"], "amount": row["amount"], "currency": row["currency"], "timestamp": timestamp})
        relationships[relationship.id or ""] = relationship

        for side, account_id in (("from", from_id), ("to", to_id)):
            holder_name = row.get(f"{side}_holder_name", "")
            national_id = row.get(f"{side}_holder_national_id", "")
            if not national_id:
                continue
            person_key = f"national:{national_id}"
            provisional_id = kyc_persons.get(person_key)
            if provisional_id is None:
                provisional_id = make_provisional_person_id(f"{row['record_id']}:{side}", SourceType.BANK_TXN.value)
                kyc_persons[person_key] = provisional_id
                person_id = id_map.get(provisional_id, provisional_id)
                nodes[person_id] = Person(
                    id=person_id,
                    full_name=holder_name,
                    national_id=national_id,
                    created_at=timestamp,
                    updated_at=timestamp,
                    attributes={"identity_claims": [{"record_id": row["record_id"], "name": holder_name, "national_id": national_id, "verified": True, "source_record_id": source_record_id}]},
                )
            else:
                person_id = id_map.get(provisional_id, provisional_id)
            relationships.setdefault(
                make_relationship_id(person_id, GraphRelationshipType.OWNS_ACCOUNT.value, account_id, source_record_id),
                GraphEdge(
                    id=make_relationship_id(person_id, GraphRelationshipType.OWNS_ACCOUNT.value, account_id, source_record_id),
                    source_id=person_id,
                    target_id=account_id,
                    edge_type=GraphRelationshipType.OWNS_ACCOUNT,
                    derivation_class=DerivationClass.FACT,
                    source_record_id=source_record_id,
                    created_at=timestamp,
                    properties={"id": make_relationship_id(person_id, GraphRelationshipType.OWNS_ACCOUNT.value, account_id, source_record_id), "source_record_id": source_record_id, "kyc_verified": True},
                ),
            )

    summary = parsed.summary.model_copy(update={
        "node_created_count": len(nodes),
        "relationship_created_count": len(relationships),
    })
    return IngestionBundle(
        batch_id=parsed.batch_id,
        source_type=SourceType.BANK_TXN,
        file_name=parsed.file_name,
        source_records=parsed.source_records,
        nodes=list(nodes.values()),
        relationships=list(relationships.values()),
        issues=parsed.issues,
        summary=summary,
    )


__all__ = ["map_bank_bundle"]
