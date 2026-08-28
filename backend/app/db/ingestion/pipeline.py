"""Repository-independent orchestration for synthetic CSV ingestion."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from backend.app.core.graph.edges import GraphEdge
from backend.app.core.graph.entities import GraphEntityBase, SourceRecord

from .contracts import (
    EntityReviewCandidate,
    IngestionBundle,
    IngestionSummary,
    IssueSeverity,
    ParsedSourceBundle,
    ParseIssue,
    SourceType,
    UploadedSource,
)
from .graph_adapter import build_m1_graph_store, validate_graph_references
from .identifiers import make_batch_id, make_provisional_person_id
from .mappers.bank import map_bank_bundle
from .mappers.cdr import map_cdr_bundle
from .mappers.fir import map_fir_bundle
from .mappers.intelligence import map_intelligence_bundle
from .parsers.bank import parse_bank_source_file
from .parsers.cdr import parse_cdr_source_file
from .parsers.fir import parse_fir_source_file
from .parsers.intelligence import parse_intelligence_source_file
from .resolution.matcher import IdentityClaim, decide_candidates
from .resolution.registry import IdentityRegistry


class CsvIngestionPipeline:
    """Ingest CSV sources into validated, in-memory graph bundles.

    Workflow: CSV reading → source parsing → normalization → IdentityClaim
    collection → entity resolution → canonical Person-ID mapping → graph
    mapping → provenance validation → GraphStore adapter.
    """

    def __init__(self) -> None:
        self.registry = IdentityRegistry()
        self.graph_store = build_m1_graph_store([], [])

    def ingest_batch(self, sources: Iterable[UploadedSource]) -> IngestionBundle:
        """Ingest multiple byte-oriented sources as a unified batch."""
        from .parsers.fir import parse_fir_source_bytes
        from .parsers.cdr import parse_cdr_source_bytes
        from .parsers.bank import parse_bank_source_bytes
        from .parsers.intelligence import parse_intelligence_source_bytes

        parsers_and_mappers = {
            SourceType.FIR: (parse_fir_source_bytes, map_fir_bundle),
            SourceType.CDR: (parse_cdr_source_bytes, map_cdr_bundle),
            SourceType.BANK_TXN: (parse_bank_source_bytes, map_bank_bundle),
            SourceType.INTEL_REPORT: (parse_intelligence_source_bytes, map_intelligence_bundle),
        }

        all_parsed: list[tuple[ParsedSourceBundle, Any]] = []
        source_list = list(sources)
        if not source_list:
            return self._finalize(
                IngestionBundle(
                    batch_id=make_batch_id("MIXED", "empty"),
                    source_type=SourceType.FIR,
                    file_name="empty",
                ),
                [],
            )

        names = sorted(s.file_name for s in source_list)
        batch_id = make_batch_id("MIXED", "|".join(names))

        for source in source_list:
            parser_fn, mapper_fn = parsers_and_mappers[source.source_type]
            source_batch_id = make_batch_id(source.source_type.value, source.file_name)
            parsed = parser_fn(source.data, batch_id=source_batch_id, file_name=source.file_name)
            all_parsed.append((parsed, mapper_fn))

        return self._resolve_and_map_bundles(all_parsed, batch_id)

    def _resolve_and_map_bundles(self, all_parsed: list[tuple[ParsedSourceBundle, Any]], batch_id: str) -> IngestionBundle:
        all_mappings: dict[str, str] = {}
        all_reviews: list[EntityReviewCandidate] = []
        for parsed, _ in all_parsed:
            mapping, reviews = self._resolve_parsed(parsed)
            all_mappings.update(mapping)
            all_reviews.extend(reviews)

        bundles: list[IngestionBundle] = []
        for parsed, mapper_fn in all_parsed:
            bundle = mapper_fn(parsed, person_id_mapping=all_mappings)
            bundles.append(bundle)

        if len(bundles) == 1:
            return self._finalize(bundles[0], all_reviews)

        combined = self._combine(bundles, batch_id)
        return self._finalize(combined, all_reviews)

    def ingest_fir_csv(self, path: str | Path) -> IngestionBundle:
        """Ingest one FIR CSV file."""
        path_obj = Path(path)
        source = UploadedSource(source_type=SourceType.FIR, file_name=path_obj.name, data=path_obj.read_bytes())
        return self.ingest_batch([source])

    def ingest_cdr_csv(self, path: str | Path) -> IngestionBundle:
        """Ingest one CDR CSV file."""
        path_obj = Path(path)
        source = UploadedSource(source_type=SourceType.CDR, file_name=path_obj.name, data=path_obj.read_bytes())
        return self.ingest_batch([source])

    def ingest_bank_csv(self, path: str | Path) -> IngestionBundle:
        """Ingest one bank transaction CSV file."""
        path_obj = Path(path)
        source = UploadedSource(source_type=SourceType.BANK_TXN, file_name=path_obj.name, data=path_obj.read_bytes())
        return self.ingest_batch([source])

    def ingest_intelligence_csv(self, path: str | Path) -> IngestionBundle:
        """Ingest one intelligence CSV file."""
        path_obj = Path(path)
        source = UploadedSource(source_type=SourceType.INTEL_REPORT, file_name=path_obj.name, data=path_obj.read_bytes())
        return self.ingest_batch([source])

    def ingest_directory(self, directory: str | Path) -> IngestionBundle:
        """Ingest recognized trial CSV files from a caller-selected directory."""
        root = Path(directory)
        mapping = {
            "fir_records.csv": SourceType.FIR,
            "cdr_records.csv": SourceType.CDR,
            "bank_transactions.csv": SourceType.BANK_TXN,
            "intelligence_records.csv": SourceType.INTEL_REPORT,
        }

        sources: list[UploadedSource] = []
        for filename, source_type in mapping.items():
            path = root / filename
            if path.exists() and path.is_file():
                sources.append(UploadedSource(source_type=source_type, file_name=filename, data=path.read_bytes()))

        if not sources:
            return self._finalize(
                IngestionBundle(
                    batch_id=make_batch_id("MIXED", root.name or "empty"),
                    source_type=SourceType.FIR,
                    file_name=root.name or str(root),
                ),
                [],
            )

        return self.ingest_batch(sources)

    @staticmethod
    def _batch_id(path: str | Path, source_type: SourceType) -> str:
        return make_batch_id(source_type.value, Path(path).name)

    def _extract_claims(self, parsed: ParsedSourceBundle) -> list[IdentityClaim]:
        """Extract IdentityClaims from parsed source rows."""
        claims: list[IdentityClaim] = []
        for row in parsed.rows:
            # FIR rows have 'raw_person_name', CDR rows have 'caller_subscriber_name'/'callee_subscriber_name',
            # bank rows have 'from_holder_name'/'to_holder_name', intelligence rows have 'subject_name'
            source_record_id = row.get("source_record_id", "")
            record_id = row.get("record_id", "")

            if parsed.source_type == SourceType.FIR:
                claims.append(IdentityClaim(
                    source_record_id=source_record_id,
                    record_id=record_id,
                    full_name=row.get("raw_person_name", ""),
                    phone_number=row.get("phone", ""),
                    vehicle_number=row.get("vehicle", ""),
                    address=row.get("raw_address", ""),
                    national_id=row.get("national_id", ""),
                    source_type=parsed.source_type,
                ))
            elif parsed.source_type == SourceType.CDR:
                for side in ("caller", "callee"):
                    subscriber_name = row.get(f"{side}_subscriber_name", "")
                    national_id = row.get(f"{side}_national_id", "")
                    if subscriber_name or national_id:
                        claims.append(IdentityClaim(
                            source_record_id=source_record_id,
                            record_id=f"{record_id}:{side}",
                            full_name=subscriber_name,
                            national_id=national_id,
                            source_type=parsed.source_type,
                        ))
            elif parsed.source_type == SourceType.BANK_TXN:
                for side in ("from", "to"):
                    national_id = row.get(f"{side}_holder_national_id", "")
                    if national_id:
                        claims.append(IdentityClaim(
                            source_record_id=source_record_id,
                            record_id=f"{record_id}:{side}",
                            full_name=row.get(f"{side}_holder_name", ""),
                            national_id=national_id,
                            source_type=parsed.source_type,
                        ))
            elif parsed.source_type == SourceType.INTEL_REPORT:
                claims.append(IdentityClaim(
                    source_record_id=source_record_id,
                    record_id=record_id,
                    full_name=row.get("subject_name", ""),
                    aliases=[row["raw_alias"]] if row.get("raw_alias") else [],
                    phone_number=row.get("phone", ""),
                    national_id=row.get("national_id", ""),
                    source_type=parsed.source_type,
                ))
        return claims

    def _resolve_parsed(self, parsed: ParsedSourceBundle) -> tuple[dict[str, str], list[EntityReviewCandidate]]:
        """Resolve identity claims from parsed data and return provisional→canonical mapping."""
        mapping: dict[str, str] = {}
        reviews: list[EntityReviewCandidate] = []
        claims = self._extract_claims(parsed)

        def claim_sort_key(c: IdentityClaim) -> tuple[int, str]:
            score = bool(c.national_id) * 3 + bool(c.phone_number) * 2 + bool(c.vehicle_number) * 2 + bool(c.address)
            return (-score, c.record_id)
        
        claims.sort(key=claim_sort_key)

        for claim in claims:
            decisions = decide_candidates(self.registry, claim)
            for decision in decisions:
                reviews.append(EntityReviewCandidate(
                    incoming_record_id=claim.record_id,
                    candidate_node_id=decision.candidate_person_id,
                    status=decision.status,
                    confidence=decision.confidence,
                    matched_fields=decision.matched_fields,
                    conflicting_fields=decision.conflicting_fields,
                    reason=decision.reason,
                    source_record_ids=decision.supporting_source_record_ids,
                    auto_link_allowed=decision.auto_link_allowed,
                    requires_human_review=decision.requires_human_review,
                ))
            approved = next((decision.candidate_person_id for decision in decisions if decision.auto_link_allowed), None)
            canonical_id = self.registry.register_claim(claim, person_id=approved)

            # Create provisional→canonical mapping for the mapper
            provisional_id = make_provisional_person_id(claim.record_id, claim.source_type.value)
            mapping[provisional_id] = canonical_id

        return mapping, reviews

    def _finalize(self, bundle: IngestionBundle, reviews: list[EntityReviewCandidate]) -> IngestionBundle:
        """Validate referential integrity and build the graph store."""
        nodes: dict[str, GraphEntityBase] = {}
        for node in bundle.nodes:
            nodes.setdefault(str(node.id), node)

        relationships: dict[str, GraphEdge] = {}
        for edge in bundle.relationships:
            relationships.setdefault(edge.id or "", edge)

        errors = validate_graph_references(nodes.values(), relationships.values(), bundle.source_records)
        issues = list(bundle.issues)
        issues.extend(ParseIssue(source_type=bundle.source_type, file_name=bundle.file_name, row_number=1, record_id="pipeline", field_name="graph", code="REFERENTIAL_INTEGRITY", message=error, severity=IssueSeverity.ERROR) for error in errors)

        summary = bundle.summary.model_copy(update={
            "node_created_count": len(nodes),
            "relationship_created_count": len(relationships),
            "review_required_count": sum(candidate.requires_human_review for candidate in reviews),
            "rejected_count": sum(issue.severity is IssueSeverity.ERROR for issue in issues),
        })
        finalized = bundle.model_copy(update={
            "nodes": list(nodes.values()),
            "relationships": list(relationships.values()),
            "review_candidates": reviews,
            "issues": issues,
            "summary": summary,
        })
        self.graph_store = build_m1_graph_store(finalized.nodes, finalized.relationships)
        return finalized

    def _combine(self, bundles: Iterable[IngestionBundle], batch_id: str) -> IngestionBundle:
        bundle_list = list(bundles)
        source_records: list[SourceRecord] = []
        nodes: list[GraphEntityBase] = []
        relationships: list[GraphEdge] = []
        issues: list[ParseIssue] = []
        summary = IngestionSummary()
        for bundle in bundle_list:
            source_records.extend(bundle.source_records)
            nodes.extend(bundle.nodes)
            relationships.extend(bundle.relationships)
            issues.extend(bundle.issues)
            summary = summary.model_copy(update={
                "received_count": summary.received_count + bundle.summary.received_count,
                "accepted_count": summary.accepted_count + bundle.summary.accepted_count,
                "duplicate_count": summary.duplicate_count + bundle.summary.duplicate_count,
                "conflict_count": summary.conflict_count + bundle.summary.conflict_count,
                "rejected_count": summary.rejected_count + bundle.summary.rejected_count,
                "warning_count": summary.warning_count + bundle.summary.warning_count,
                "source_record_count": summary.source_record_count + bundle.summary.source_record_count,
                "node_created_count": summary.node_created_count + bundle.summary.node_created_count,
                "relationship_created_count": summary.relationship_created_count + bundle.summary.relationship_created_count,
            })
        return IngestionBundle(batch_id=batch_id, source_type=SourceType.FIR, file_name="directory", source_records=source_records, nodes=nodes, relationships=relationships, issues=issues, summary=summary)


__all__ = ["CsvIngestionPipeline"]
