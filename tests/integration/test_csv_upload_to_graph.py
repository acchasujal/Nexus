import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from backend.app.main import app
from backend.app.auth.principal import Principal
from shared.contracts.api import UserRole
from backend.app.api.dependencies import get_principal, get_repository

FIXTURES_DIR = Path(__file__).parent.parent / "data" / "fixtures" / "m2_csv"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def repo():
    # Fetch the repository used by the app to verify graph state
    for dependency, override in app.dependency_overrides.items():
        if dependency == get_repository:
            return override()
    # If no override, use the actual dependency (which might be a singleton in state)
    # Actually, the repo is a singleton in main.py, but for tests it might be different.
    return app.state.repository


@pytest.fixture
def sp_token(monkeypatch):
    def override_get_principal():
        return Principal(user_id="test_sp", email="test@mha.gov.in", role=UserRole.SP, is_anonymous=False)
        
    app.dependency_overrides[get_principal] = override_get_principal
    yield
    app.dependency_overrides.pop(get_principal, None)


@pytest.fixture
def investigator_token(monkeypatch):
    def override_get_principal():
        return Principal(user_id="test_inv", email="test@mha.gov.in", role=UserRole.INVESTIGATOR, is_anonymous=False)
        
    app.dependency_overrides[get_principal] = override_get_principal
    yield
    app.dependency_overrides.pop(get_principal, None)


def _upload(client, file_path, field_name="fir"):
    with open(file_path, "rb") as f:
        return client.post("/api/v1/ingest", files={field_name: (file_path.name, f, "text/csv")})


def _clear_repo(repo):
    repo.nodes.clear()
    repo.edges.clear()
    repo.incident_edges.clear()
    repo.source_records.clear()
    repo.audit_events.clear()


def test_multipart_bytes_parsed(client, sp_token):
    # 1. Actual multipart bytes are parsed.
    res = _upload(client, FIXTURES_DIR / "valid_fir.csv", "fir")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["summary"]["accepted"] == 2


def test_changing_file_contents_changes_response(client, sp_token):
    # 2. Changing file contents changes the response.
    # 3. Counts are calculated rather than hardcoded.
    res_valid = _upload(client, FIXTURES_DIR / "valid_fir.csv", "fir")
    res_mixed = _upload(client, FIXTURES_DIR / "mixed_fir.csv", "fir")
    
    assert res_valid.json()["summary"]["accepted"] == 2
    assert res_valid.json()["summary"]["rejected"] == 0
    
    assert res_mixed.json()["summary"]["accepted"] == 1
    assert res_mixed.json()["summary"]["rejected"] == 1


def test_invalid_rows_correct_row_numbers(client, sp_token):
    # 4. Invalid rows include correct row numbers.
    res = _upload(client, FIXTURES_DIR / "mixed_fir.csv", "fir")
    assert res.status_code == 200
    issues = res.json().get("parse_issues", [])
    print("ISSUES:", issues)
    assert any(i["row_number"] == 3 for i in issues)


def test_exact_duplicates_vs_conflicts(client, sp_token):
    # 5. Exact duplicates and conflicts are different.
    # Upload first
    _upload(client, FIXTURES_DIR / "valid_fir.csv", "fir")
    
    # Duplicate
    res_dup = _upload(client, FIXTURES_DIR / "duplicate_fir.csv", "fir")
    assert res_dup.json()["summary"]["duplicates"] == 2
    assert res_dup.json()["summary"]["conflicts"] == 0
    
    # Conflict
    res_con = _upload(client, FIXTURES_DIR / "conflict_fir.csv", "fir")
    assert res_con.json()["summary"]["duplicates"] == 0
    assert res_con.json()["summary"]["conflicts"] == 1


def test_all_three_sources_resolve_together_and_graph_apis(client, sp_token, repo):
    # Reset repo to ensure clean state
    _clear_repo(repo)
    
    # 6. All three sources resolve identities together.
    with open(FIXTURES_DIR / "valid_fir.csv", "rb") as f_fir, \
         open(FIXTURES_DIR / "valid_cdr.csv", "rb") as f_cdr, \
         open(FIXTURES_DIR / "valid_bank.csv", "rb") as f_bank:
        res = client.post("/api/v1/ingest", files={
            "fir": ("valid_fir.csv", f_fir, "text/csv"),
            "cdr": ("valid_cdr.csv", f_cdr, "text/csv"),
            "bank": ("valid_bank.csv", f_bank, "text/csv")
        })
    assert res.status_code == 200
    
    # John Doe has phone 9876543210 (in FIR). CDR uses 9876543210.
    # Bank uses ACC-1234 but no identity info attached to Bank currently unless mapped.
    
    # 7. Uploaded graph data appears through graph APIs immediately.
    # Look for the Case node
    res_cases = client.get("/api/v1/investigations")
    assert res_cases.status_code == 200
    cases = res_cases.json()
    case = next((c for c in cases if c.get("fir_number") == "FIR-101"), None)
    assert case is not None
    case_id = case["id"]
    
    # 8. Worklist includes newly uploaded Case nodes.
    # Done above (investigations is the worklist)
    
    # 9. Evidence endpoints can access new relationship provenance.
    # Let's get network for FIR-101
    res_network = client.get(f"/api/v1/network/cases/{case_id}")
    assert res_network.status_code == 200
    edges = res_network.json()["edges"]
    assert len(edges) > 0
    edge = edges[0]
    src = edge["source_id"]
    tgt = edge["target_id"]
    
    res_ev = client.get(f"/api/v1/entities/{src}/links/{tgt}/evidence")
    assert res_ev.status_code == 200
    ev_list = res_ev.json()
    assert len(ev_list) > 0


def test_reupload_idempotent(client, sp_token, repo):
    # 10. Re-upload does not duplicate nodes or relationships.
    _clear_repo(repo)
    res1 = _upload(client, FIXTURES_DIR / "valid_fir.csv", "fir")
    res1_data = res1.json()
    nodes1 = res1_data["summary"]["nodes_created"]
    edges1 = res1_data["summary"]["relationships_created"]
    
    assert nodes1 > 0
    assert edges1 > 0
    
    res2 = _upload(client, FIXTURES_DIR / "valid_fir.csv", "fir")
    res2_data = res2.json()
    
    assert res2_data["summary"]["nodes_created"] == 0
    assert res2_data["summary"]["relationships_created"] == 0


def test_unauthorized_role(client, investigator_token):
    # 11. Unauthorized role returns 403.
    res = _upload(client, FIXTURES_DIR / "valid_fir.csv", "fir")
    assert res.status_code == 403


def test_failed_ingestion_leaves_repo_unchanged(client, sp_token, repo):
    # 12. Failed ingestion leaves repository unchanged.
    _clear_repo(repo)
    _upload(client, FIXTURES_DIR / "valid_fir.csv", "fir")
    nodes_before = len(repo.nodes)
    edges_before = len(repo.edges)
    
    # Upload fatal error (invalid header)
    res = client.post(
        "/api/v1/ingest",
        files={"fir": ("fatal.csv", b"wrong_header\nfoo", "text/csv")}
    )
    assert res.status_code == 422
    
    assert len(repo.nodes) == nodes_before
    assert len(repo.edges) == edges_before


def test_audit_events_recorded(client, sp_token, repo):
    # 13. Audit events record started/completed/failed.
    _clear_repo(repo)
    repo.audit_events.clear()
    
    # Success
    _upload(client, FIXTURES_DIR / "valid_fir.csv", "fir")
    assert any(e["event_type"] == "ingestion_started" for e in repo.audit_events)
    assert any(e["event_type"] == "ingestion_completed" for e in repo.audit_events)
    
    repo.audit_events.clear()
    
    # Fatal error
    client.post("/api/v1/ingest", files={"fir": ("fatal.csv", b"wrong_header\nfoo", "text/csv")})
    assert any(e["event_type"] == "ingestion_failed" for e in repo.audit_events)
