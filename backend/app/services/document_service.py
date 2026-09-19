"""backend/app/services/document_service.py

Unstructured document ingestion, extraction, and provenance service for NEXUS.
Phase P1A: Unstructured Document Ingestion Foundation.

Provides:
  - DocumentService: Orchestrates document intake, cryptographic fingerprinting,
    deterministic machine-readable text extraction, provenance recording, and audit.
  - Strict Phase Boundary: Ingestion and text extraction only. No graph mutations,
    no relationship generation, and no LLM execution in this phase.
"""

from __future__ import annotations

import hashlib
import io
import logging
import mimetypes
from datetime import datetime, timezone
from typing import Any

import pypdf

from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import (
    DocumentExtractionMetadata,
    DocumentResponse,
    DocumentSourceType,
    DocumentTextResponse,
    EvidenceProvenanceContract,
    ExtractionStatus,
)

logger = logging.getLogger(__name__)

MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str) and val:
        try:
            cleaned = val.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(cleaned)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return _utcnow()


class DocumentService:
    """Orchestrates unstructured document ingestion, deterministic text extraction,
    cryptographic fingerprinting, and audit logging.
    """

    def __init__(self, repository: Any, audit_service: AuditService) -> None:
        self._repo = repository
        self._audit = audit_service

    # ── Upload & Ingestion ───────────────────────────────────────────────────

    def ingest_document(
        self,
        filename: str,
        data: bytes,
        source_type: str | DocumentSourceType,
        uploader_id: str,
        case_id: str | None = None,
        request_id: str | None = None,
    ) -> DocumentResponse:
        """Validate, fingerprint, extract text from, and persist an unstructured document."""
        # 1. Validation: filename & extension
        if not filename or not filename.strip():
            raise ValueError("Document filename cannot be empty.")

        clean_filename = filename.strip()
        lower_name = clean_filename.lower()

        if not (lower_name.endswith(".pdf") or lower_name.endswith(".txt")):
            raise ValueError(f"Unsupported file format for '{clean_filename}'. Only .pdf and .txt documents are supported.")

        # 2. Validation: size
        if len(data) == 0:
            raise ValueError(f"Document '{clean_filename}' is empty (0 bytes).")

        if len(data) > MAX_DOCUMENT_SIZE_BYTES:
            raise ValueError(
                f"Document '{clean_filename}' exceeds maximum allowed size of {MAX_DOCUMENT_SIZE_BYTES // (1024 * 1024)} MB."
            )

        # 3. Source Type resolution
        st_val = source_type.value if hasattr(source_type, "value") else str(source_type)
        valid_st_values = {t.value for t in DocumentSourceType}
        if st_val not in valid_st_values:
            st_val = DocumentSourceType.OTHER_DOCUMENT.value

        # 4. Cryptographic document integrity fingerprint (SHA-256)
        content_hash = hashlib.sha256(data).hexdigest()

        # 5. Check for existing identical document (Deduplication)
        existing = None
        if hasattr(self._repo, "get_document_by_hash"):
            existing = self._repo.get_document_by_hash(content_hash)

        if existing:
            logger.info("Document with identical content hash %s already exists. Returning existing record.", content_hash)
            return self._record_to_response(existing)

        # 6. Mime Type determination
        mime_type = "application/pdf" if lower_name.endswith(".pdf") else "text/plain"
        guess, _ = mimetypes.guess_type(clean_filename)
        if guess:
            mime_type = guess

        # 7. Deterministic Text Extraction
        extracted_text, metadata, status = self._extract_text(data, lower_name)

        # 8. Document Identity and Timestamp
        doc_id = f"doc-{content_hash[:16]}"
        now_dt = _utcnow()

        # 9. Provenance Metadata
        excerpt = (extracted_text[:200] + "...") if len(extracted_text) > 200 else extracted_text
        provenance = EvidenceProvenanceContract(
            source_type=st_val,
            source_id=doc_id,
            timestamp=now_dt,
            extracted_fact=excerpt or f"Uploaded document: {clean_filename}",
            derivation_method="DOCUMENT_EXTRACTION",
            confidence=1.0 if status == ExtractionStatus.SUCCESS else 0.0,
        )

        doc_record = {
            "document_id": doc_id,
            "original_filename": clean_filename,
            "source_type": st_val,
            "mime_type": mime_type,
            "content_hash": content_hash,
            "uploaded_by": uploader_id,
            "uploaded_at": now_dt.isoformat(),
            "case_id": case_id,
            "extraction_status": status.value,
            "extraction_metadata": metadata.model_dump(),
            "provenance": provenance.model_dump(),
            "extracted_text": extracted_text,
        }

        # 10. Persist in repository
        if hasattr(self._repo, "store_document"):
            self._repo.store_document(doc_record)

        # 11. Emit Audit Event (no duplicate events)
        audit_event_type = (
            AuditEventType.DOCUMENT_EXTRACTION_FAILED
            if status == ExtractionStatus.FAILED
            else AuditEventType.DOCUMENT_UPLOADED
        )

        self._audit.record(
            event_type=audit_event_type,
            actor_id=uploader_id,
            case_id=case_id,
            entity_id=doc_id,
            entity_type="Document",
            request_id=request_id,
            details={
                "document_id": doc_id,
                "filename": clean_filename,
                "content_hash": content_hash,
                "source_type": st_val,
                "mime_type": mime_type,
                "case_id": case_id,
                "extraction_status": status.value,
                "page_count": metadata.page_count,
                "character_count": metadata.character_count,
                "word_count": metadata.word_count,
                "extraction_method": metadata.extraction_method,
                "error_message": metadata.error_message,
            },
        )

        return self._record_to_response(doc_record)

    # ── Retrieval & View ─────────────────────────────────────────────────────

    def get_document_metadata(
        self,
        document_id: str,
        actor_id: str,
        request_id: str | None = None,
        suppress_audit: bool = False,
    ) -> DocumentResponse | None:
        """Retrieve document metadata by document ID, emitting DOCUMENT_VIEWED if authorized."""
        record = None
        if hasattr(self._repo, "get_document"):
            record = self._repo.get_document(document_id)

        if not record:
            return None

        if not suppress_audit:
            self._audit.record(
                event_type=AuditEventType.DOCUMENT_VIEWED,
                actor_id=actor_id,
                case_id=record.get("case_id"),
                entity_id=document_id,
                entity_type="Document",
                request_id=request_id,
                details={
                    "document_id": document_id,
                    "action": "VIEW_METADATA",
                    "content_hash": record.get("content_hash"),
                    "case_id": record.get("case_id"),
                },
            )

        return self._record_to_response(record)

    def get_document_text(
        self,
        document_id: str,
        actor_id: str,
        request_id: str | None = None,
        suppress_audit: bool = False,
    ) -> DocumentTextResponse | None:
        """Retrieve extracted document text by document ID, emitting DOCUMENT_VIEWED if authorized."""
        record = None
        if hasattr(self._repo, "get_document"):
            record = self._repo.get_document(document_id)

        if not record:
            return None

        if not suppress_audit:
            self._audit.record(
                event_type=AuditEventType.DOCUMENT_VIEWED,
                actor_id=actor_id,
                case_id=record.get("case_id"),
                entity_id=document_id,
                entity_type="Document",
                request_id=request_id,
                details={
                    "document_id": document_id,
                    "action": "VIEW_TEXT",
                    "content_hash": record.get("content_hash"),
                    "case_id": record.get("case_id"),
                },
            )

        return DocumentTextResponse(
            document_id=record["document_id"],
            content_hash=record["content_hash"],
            extracted_text=record.get("extracted_text", ""),
            extraction_status=ExtractionStatus(record["extraction_status"]),
            extraction_metadata=DocumentExtractionMetadata(**record.get("extraction_metadata", {})),
        )

    def list_documents(
        self,
        case_id: str | None = None,
    ) -> list[DocumentResponse]:
        """List documents from repository, optionally filtered by case_id."""
        records: list[dict[str, Any]] = []
        if hasattr(self._repo, "list_documents"):
            records = self._repo.list_documents(case_id=case_id)
        elif hasattr(self._repo, "documents"):
            docs = list(self._repo.documents.values())
            if case_id is not None:
                docs = [d for d in docs if d.get("case_id") == case_id]
            records = sorted(docs, key=lambda d: str(d.get("uploaded_at", "")), reverse=True)

        return [self._record_to_response(r) for r in records]

    # ── Text Extraction Internal Methods ─────────────────────────────────────

    def _extract_text(
        self,
        data: bytes,
        lower_filename: str,
    ) -> tuple[str, DocumentExtractionMetadata, ExtractionStatus]:
        """Deterministic text extraction for machine-readable .pdf and .txt files."""
        if lower_filename.endswith(".pdf"):
            return self._extract_pdf_text(data)
        return self._extract_txt_text(data)

    def _extract_pdf_text(
        self,
        data: bytes,
    ) -> tuple[str, DocumentExtractionMetadata, ExtractionStatus]:
        """Extract text from machine-readable PDF bytes using pypdf."""
        try:
            stream = io.BytesIO(data)
            reader = pypdf.PdfReader(stream)

            if reader.is_encrypted:
                meta = DocumentExtractionMetadata(
                    page_count=len(reader.pages) if reader.pages else 0,
                    character_count=0,
                    word_count=0,
                    extraction_method="pypdf",
                    error_message="PDF is encrypted/password-protected; text extraction refused.",
                )
                return "", meta, ExtractionStatus.FAILED

            pages_text: list[str] = []
            page_count = len(reader.pages)

            for page_idx, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ""
                    pages_text.append(text)
                except Exception as page_err:
                    logger.warning("Error extracting text from PDF page %d: %s", page_idx, page_err)
                    pages_text.append("")

            combined = "\n\n".join(pages_text).strip()

            if not combined:
                meta = DocumentExtractionMetadata(
                    page_count=page_count,
                    character_count=0,
                    word_count=0,
                    extraction_method="pypdf",
                    error_message="No machine-readable text found in PDF document.",
                )
                return "", meta, ExtractionStatus.EMPTY

            words = combined.split()
            meta = DocumentExtractionMetadata(
                page_count=page_count,
                character_count=len(combined),
                word_count=len(words),
                extraction_method="pypdf",
                error_message=None,
            )
            return combined, meta, ExtractionStatus.SUCCESS

        except Exception as exc:
            logger.warning("PDF extraction failed: %s", exc)
            meta = DocumentExtractionMetadata(
                page_count=0,
                character_count=0,
                word_count=0,
                extraction_method="pypdf",
                error_message=f"Malformed PDF or read error: {exc}",
            )
            return "", meta, ExtractionStatus.FAILED

    def _extract_txt_text(
        self,
        data: bytes,
    ) -> tuple[str, DocumentExtractionMetadata, ExtractionStatus]:
        """Extract text from plain-text bytes using safe encodings."""
        decoded = ""
        encoding_used = "utf-8"

        try:
            decoded = data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                decoded = data.decode("latin-1")
                encoding_used = "latin-1"
            except Exception as exc:
                meta = DocumentExtractionMetadata(
                    page_count=1,
                    character_count=0,
                    word_count=0,
                    extraction_method="decode",
                    error_message=f"Failed to decode text document: {exc}",
                )
                return "", meta, ExtractionStatus.FAILED

        clean_text = decoded.strip()
        if not clean_text:
            meta = DocumentExtractionMetadata(
                page_count=1,
                character_count=0,
                word_count=0,
                extraction_method=f"text/{encoding_used}",
                error_message="Document is empty plain text.",
            )
            return "", meta, ExtractionStatus.EMPTY

        words = clean_text.split()
        meta = DocumentExtractionMetadata(
            page_count=1,
            character_count=len(clean_text),
            word_count=len(words),
            extraction_method=f"text/{encoding_used}",
            error_message=None,
        )
        return clean_text, meta, ExtractionStatus.SUCCESS

    # ── Conversion Helpers ───────────────────────────────────────────────────

    def _record_to_response(self, record: dict[str, Any]) -> DocumentResponse:
        meta_dict = record.get("extraction_metadata", {})
        prov_dict = record.get("provenance", {})

        return DocumentResponse(
            document_id=record["document_id"],
            original_filename=record["original_filename"],
            source_type=record["source_type"],
            mime_type=record["mime_type"],
            content_hash=record["content_hash"],
            uploaded_by=record["uploaded_by"],
            uploaded_at=_parse_datetime(record["uploaded_at"]),
            case_id=record.get("case_id"),
            extraction_status=ExtractionStatus(record["extraction_status"]),
            extraction_metadata=DocumentExtractionMetadata(**meta_dict),
            provenance=EvidenceProvenanceContract(**prov_dict),
        )
