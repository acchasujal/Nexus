import pytest
import asyncio
from unittest.mock import MagicMock

from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.db.ingestion.contracts import UploadedSource, SourceType
from backend.app.db.ingestion.pipeline import CsvIngestionPipeline
from backend.app.services.audit_service import AuditService
from backend.app.services.ingestion_service import IngestionService
from shared.contracts.api import BatchStatus

@pytest.fixture
def repo():
    return InMemoryBackendRepository()

@pytest.fixture
def graph_repo(repo):
    return GraphRepository(repo.to_graph_store())

@pytest.fixture
def audit_service(repo):
    return AuditService(repo)

@pytest.fixture
def pipeline():
    return CsvIngestionPipeline()

@pytest.fixture
def ingestion_service(repo, graph_repo, audit_service, pipeline):
    return IngestionService(repo, graph_repo, audit_service, pipeline)


@pytest.mark.anyio
async def test_validation_empty_files(ingestion_service):
    with pytest.raises(ValueError, match="At least one file must be uploaded"):
        await ingestion_service.ingest_files("u1", "r1", [])


@pytest.mark.anyio
async def test_validation_too_many_files(ingestion_service):
    sources = [UploadedSource(source_type=SourceType.FIR, file_name=f"f{i}.csv", data=b"data") for i in range(5)]
    with pytest.raises(ValueError, match="Maximum four files can be uploaded"):
        await ingestion_service.ingest_files("u1", "r1", sources)


@pytest.mark.anyio
async def test_validation_not_csv(ingestion_service):
    s = UploadedSource(source_type=SourceType.FIR, file_name="file.txt", data=b"data")
    with pytest.raises(ValueError, match="not a .csv file"):
        await ingestion_service.ingest_files("u1", "r1", [s])


@pytest.mark.anyio
async def test_validation_empty_content(ingestion_service):
    s = UploadedSource(source_type=SourceType.FIR, file_name="file.csv", data=b"")
    with pytest.raises(ValueError, match="is empty"):
        await ingestion_service.ingest_files("u1", "r1", [s])


@pytest.mark.anyio
async def test_validation_size_limit(ingestion_service):
    s = UploadedSource(source_type=SourceType.FIR, file_name="file.csv", data=b"a" * (5 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="exceeds 5 MB limit"):
        await ingestion_service.ingest_files("u1", "r1", [s])


@pytest.mark.anyio
async def test_full_success_path(ingestion_service, repo, audit_service):
    FIR_HEADER = "record_id,fir_number,fir_year,station_name,district,incident_time,offence_category,section,person_name,person_role,phone_number,national_id\n"
    data = (FIR_HEADER + "r1,F1,2026,S1,D1,2026-01-01T10:00:00Z,Theft,379,Alice Smith,ACCUSED,9999999999,NID1\n").encode("utf-8")
    s = UploadedSource(source_type=SourceType.FIR, file_name="valid.csv", data=data)
    
    resp = await ingestion_service.ingest_files("user1", "ADMIN", [s])
    
    assert resp.status == BatchStatus.COMPLETED
    assert resp.summary.accepted == 1
    assert resp.summary.nodes_created > 0
    assert resp.summary.relationships_created > 0
    assert resp.graph_updated is True
    
    events = repo.audit_events
    assert any(e["event_type"] == "ingestion_started" for e in events)
    assert any(e["event_type"] == "ingestion_completed" for e in events)
    # Ensure no PII in audit
    started_event = next(e for e in events if e["event_type"] == "ingestion_started")
    assert started_event["details"]["files"] == ["valid.csv"]
    assert "Alice" not in str(started_event["details"])


@pytest.mark.anyio
async def test_partial_success_warnings(ingestion_service):
    FIR_HEADER = "record_id,fir_number,fir_year,station_name,district,incident_time,offence_category,section,person_name,person_role,phone_number,national_id\n"
    # Row 2 is missing mandatory name for ACCUSED -> generates WARNING
    data = (FIR_HEADER + "r1,F1,2026,S1,D1,2026-01-01T10:00:00Z,Theft,379,Alice Smith,ACCUSED,9999999999,NID1\n" +
                         "r2,F1,2026,S1,D1,2026-01-01T10:00:00Z,Theft,379,,ACCUSED,,NID2\n").encode("utf-8")
    s = UploadedSource(source_type=SourceType.FIR, file_name="warn.csv", data=data)
    
    resp = await ingestion_service.ingest_files("user1", "ADMIN", [s])
    
    assert resp.status == BatchStatus.COMPLETED_WITH_WARNINGS
    assert resp.summary.accepted == 1
    assert resp.summary.rejected == 1


@pytest.mark.anyio
async def test_fatal_parse_errors(ingestion_service, repo):
    # Invalid header -> FATAL
    data = b"wrong_header\nfoo"
    s = UploadedSource(source_type=SourceType.FIR, file_name="fatal.csv", data=data)
    
    resp = await ingestion_service.ingest_files("user1", "ADMIN", [s])
    
    assert resp.status == BatchStatus.FAILED
    assert resp.graph_updated is False
    
    events = repo.audit_events
    assert any(e["event_type"] == "ingestion_failed" for e in events)
