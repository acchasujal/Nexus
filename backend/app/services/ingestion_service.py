from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.db.ingestion.contracts import SourceType, UploadedSource
from backend.app.db.ingestion.pipeline import CsvIngestionPipeline
from backend.app.services.audit_service import AuditService, AuditEventType
from shared.contracts.api import (
    BatchStatus,
    IngestionBatchResponse,
    IngestionFileResult,
    IngestionFileSummary,
    IngestionParseIssue,
)


class IngestionService:
    """Orchestrates CSV ingestion, bridging the raw pipeline with repositories and audit."""

    def __init__(
        self,
        repository: InMemoryBackendRepository,
        graph_repo: GraphRepository,
        audit_service: AuditService,
        pipeline: CsvIngestionPipeline,
        neo4j_conn: Any = None,
        intelligence_event_service: Any | None = None,
    ):
        self._repo = repository
        self._graph_repo = graph_repo
        self._audit = audit_service
        self._pipeline = pipeline
        self._neo4j = neo4j_conn
        self._event_service = intelligence_event_service
        self._lock = asyncio.Lock()

    async def ingest_files(
        self,
        user_id: str,
        user_role: str,
        sources: list[UploadedSource],
        case_id: str | None = None,
    ) -> IngestionBatchResponse:
        """
        Validate, parse, resolve, and apply a batch of CSV uploads.
        Enforces business limits and records audit events.
        """
        if not sources:
            raise ValueError("At least one file must be uploaded.")
        max_files = 5 if any(s.source_type == SourceType.SURVEILLANCE_REPORT for s in sources) else 4
        if len(sources) > max_files:
            msg = "Maximum five files can be uploaded at once." if max_files == 5 else "Maximum four files can be uploaded at once."
            raise ValueError(msg)

        for s in sources:
            if not s.file_name.lower().endswith(".csv"):
                raise ValueError(f"File {s.file_name} is not a .csv file.")
            if not s.data:
                raise ValueError(f"File {s.file_name} is empty.")
            if len(s.data) > 5 * 1024 * 1024:
                raise ValueError(f"File {s.file_name} exceeds 5 MB limit.")

        has_surveillance = any(s.source_type == SourceType.SURVEILLANCE_REPORT for s in sources)

        async with self._lock:
            # Audit start (do not log raw data)
            file_names = [s.file_name for s in sources]
            self._audit.record(
                event_type=AuditEventType.INGESTION_STARTED,
                actor_id=user_id,
                details={"files": file_names},
            )
            if has_surveillance:
                surv_files = [s.file_name for s in sources if s.source_type == SourceType.SURVEILLANCE_REPORT]
                self._audit.record(
                    event_type=AuditEventType.SURVEILLANCE_REPORT_UPLOADED,
                    actor_id=user_id,
                    details={"files": surv_files},
                )

            try:
                bundle = self._pipeline.ingest_batch(sources)

                # Check for fatal header/file errors
                fatal_codes = {"MISSING_HEADER", "INVALID_HEADER", "DUPLICATE_HEADER", "MISSING_REQUIRED_COLUMN", "INVALID_TEXT"}
                has_fatal = any(i.code in fatal_codes for i in bundle.issues)
                if has_fatal:
                    self._audit.record(
                        event_type=AuditEventType.INGESTION_FAILED,
                        actor_id=user_id,
                        details={"batch_id": bundle.batch_id, "reason": "Fatal parse errors encountered"},
                    )
                    if has_surveillance:
                        self._audit.record(
                            event_type=AuditEventType.SURVEILLANCE_REPORT_INGESTION_FAILED,
                            actor_id=user_id,
                            details={"batch_id": bundle.batch_id, "reason": "Fatal parse errors encountered"},
                        )
                    return self._build_response(bundle, BatchStatus.FAILED, sources, 0, 0, 0, 0)

                existing_source_ids = set(self._repo.source_records)
                existing_source_hashes = {
                    (record.get("source_type"), str(record.get("locator", "")).split(":", 1)[-1]): record.get("content_hash")
                    for record in self._repo.source_records.values()
                    if record.get("locator")
                }
                duplicate_count = sum(1 for record in bundle.source_records if record.id in existing_source_ids)
                conflict_count = sum(
                    1
                    for record in bundle.source_records
                    if (record.source_type, record.locator.split(":", 1)[-1]) in existing_source_hashes
                    and existing_source_hashes[(record.source_type, record.locator.split(":", 1)[-1])] != record.content_hash
                )

                # Apply to in-memory repository (Atomic operation)
                created_n, reused_n, created_e, reused_e = self._repo.apply_bundle(bundle)

                # Tag source records with case_id if provided
                if case_id:
                    for record in bundle.source_records:
                        srid = str(record.id)
                        if srid in self._repo.source_records:
                            cids = self._repo.source_records[srid].setdefault("case_ids", [])
                            if case_id not in cids:
                                cids.append(case_id)
                
                # Store review candidates
                if bundle.review_candidates:
                    self._repo.store_review_candidates(bundle.review_candidates)

                # Refresh the analytical graph store
                self._graph_repo.replace_store(self._repo.to_graph_store())

                # If Neo4j is active and operational, sync projection
                if self._neo4j is not None and getattr(self._neo4j, "is_operational", False):
                    try:
                        nodes = [self._repo.nodes[nid] for nid in self._repo.batches[bundle.batch_id]["nodes"] if isinstance(nid, str)] if bundle.batch_id in self._repo.batches else list(self._repo.nodes.values())
                        edges = self._repo.batches[bundle.batch_id]["edges"] if bundle.batch_id in self._repo.batches else self._repo.edges
                        await self._neo4j.sync_nodes(list(self._repo.nodes.values()))
                        await self._neo4j.sync_edges(self._repo.edges)
                    except Exception as err:
                        logger.warning("Neo4j projection sync during ingestion encountered an issue: %s", err)

                # Determine warnings
                has_warnings = any(i.severity.name == "WARNING" for i in bundle.issues)
                has_rejections = bundle.summary.rejected_count > 0
                status = BatchStatus.COMPLETED_WITH_WARNINGS if (has_warnings or has_rejections) else BatchStatus.COMPLETED

                self._audit.record(
                    event_type=AuditEventType.INGESTION_COMPLETED,
                    actor_id=user_id,
                    details={
                        "batch_id": bundle.batch_id,
                        "status": status.value,
                        "nodes_created": created_n,
                        "edges_created": created_e,
                    },
                )
                if has_surveillance:
                    self._audit.record(
                        event_type=AuditEventType.SURVEILLANCE_REPORT_INGESTED,
                        actor_id=user_id,
                        details={
                            "batch_id": bundle.batch_id,
                            "status": status.value,
                            "nodes_created": created_n,
                            "edges_created": created_e,
                        },
                    )

                # Emit A3 IntelligenceEvent (DOCUMENT_INGESTED) for each source file if case-associated
                if case_id and self._event_service is not None:
                    import hashlib
                    for s in sources:
                        f_hash = hashlib.sha256(s.data).hexdigest()
                        try:
                            from shared.contracts.api import CreateIntelligenceEventRequest, IntelligenceEventType
                            self._event_service.record_event(
                                CreateIntelligenceEventRequest(
                                    event_type=IntelligenceEventType.DOCUMENT_INGESTED,
                                    case_id=case_id,
                                    source_id=f"src-{f_hash[:16]}",
                                    evidence_refs=[f"src-{f_hash[:16]}"],
                                    source_type=s.source_type.value,
                                    actor_id=user_id,
                                    title=f"CSV Ingested: {s.file_name}",
                                    description=f"Ingested {s.file_name} ({s.source_type.value}) for case {case_id}",
                                    payload={
                                        "batch_id": bundle.batch_id,
                                        "filename": s.file_name,
                                        "source_type": s.source_type.value,
                                        "content_hash": f_hash,
                                        "case_id": case_id,
                                    },
                                )
                            )
                        except Exception as ev_err:
                            logger.warning("Failed to emit DOCUMENT_INGESTED for %s: %s", s.file_name, ev_err)

                return self._build_response(
                    bundle, status, sources, created_n, reused_n, created_e, reused_e,
                    duplicate_count=duplicate_count, conflict_count=conflict_count,
                )

            except Exception as e:
                self._audit.record(
                    event_type=AuditEventType.INGESTION_FAILED,
                    actor_id=user_id,
                    details={"reason": str(e)},
                )
                if has_surveillance:
                    self._audit.record(
                        event_type=AuditEventType.SURVEILLANCE_REPORT_INGESTION_FAILED,
                        actor_id=user_id,
                        details={"reason": str(e)},
                    )
                raise

    def _build_response(
        self, bundle: Any, status: BatchStatus, sources: list[UploadedSource],
        created_n: int, reused_n: int, created_e: int, reused_e: int,
        duplicate_count: int = 0, conflict_count: int = 0,
    ) -> IngestionBatchResponse:
        """Translate internal IngestionBundle into the public API contract."""
        
        # Build combined summary
        summary = IngestionFileSummary(
            received=bundle.summary.received_count,
            accepted=bundle.summary.accepted_count,
            rejected=bundle.summary.rejected_count,
            duplicates=bundle.summary.duplicate_count + duplicate_count,
            conflicts=getattr(bundle.summary, "conflict_count", 0) + conflict_count,
            warnings=sum(1 for i in bundle.issues if i.severity.name == "WARNING"),
            source_records=len(bundle.source_records),
            nodes_created=created_n,
            nodes_reused=reused_n,
            relationships_created=created_e,
            review_required=len(bundle.review_candidates),
        )

        # Build file-level info (approximate mapping since bundle aggregates them)
        files_processed = []
        for s in sources:
            # We don't have per-file internal summaries mapped to the bundle yet,
            # so we provide the base sizes and metadata to fulfill the contract.
            files_processed.append(
                IngestionFileResult(
                    source_type=s.source_type.value,
                    file_name=s.file_name,
                    size_bytes=len(s.data),
                    summary=summary if len(sources) == 1 else IngestionFileSummary()
                )
            )

        # Map Parse Issues
        parse_issues = []
        for i in bundle.issues:
            parse_issues.append(
                IngestionParseIssue(
                    source_type=bundle.source_type.value,
                    file_name=bundle.file_name,
                    row_number=i.row_number,
                    record_id=i.record_id,
                    field=i.field_name,
                    code=i.code,
                    message=i.message,
                    severity=i.severity.name,
                )
            )

        # Map Review Candidates
        # Serialize candidates for JSON
        review_candidates = []
        for c in bundle.review_candidates:
            review_candidates.append({
                "incoming_record_id": c.incoming_record_id,
                "candidate_node_id": c.candidate_node_id,
                "status": c.status.name,
                "confidence": c.confidence,
                "matched_fields": c.matched_fields,
                "conflicting_fields": c.conflicting_fields,
                "reason": c.reason,
                "source_record_ids": c.source_record_ids,
                "auto_link_allowed": c.auto_link_allowed,
                "requires_human_review": c.requires_human_review,
            })

        return IngestionBatchResponse(
            batch_id=bundle.batch_id,
            status=status,
            files_processed=files_processed,
            summary=summary,
            parse_issues=parse_issues,
            review_candidates=review_candidates,
            graph_updated=(status in (BatchStatus.COMPLETED, BatchStatus.COMPLETED_WITH_WARNINGS)),
        )
