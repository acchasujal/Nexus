import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.auth.principal import Principal
from shared.contracts.api import UserRole


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sp_token(monkeypatch):
    # Mock decode_jwt or override dependency directly
    from backend.app.api.dependencies import get_principal
    
    def override_get_principal():
        return Principal(user_id="test_sp", email="test@mha.gov.in", role=UserRole.SP, is_anonymous=False)
        
    app.dependency_overrides[get_principal] = override_get_principal
    yield
    app.dependency_overrides.pop(get_principal, None)


@pytest.fixture
def user_token(monkeypatch):
    from backend.app.api.dependencies import get_principal
    
    def override_get_principal():
        return Principal(user_id="test_user", email="test@mha.gov.in", role=UserRole.INVESTIGATOR, is_anonymous=False)
        
    app.dependency_overrides[get_principal] = override_get_principal
    yield
    app.dependency_overrides.pop(get_principal, None)


def test_ingest_no_files(client, sp_token):
    response = client.post("/api/v1/ingest")
    assert response.status_code == 400
    assert "At least one file must be provided" in response.json()["detail"]


def test_ingest_unauthorized(client, user_token):
    response = client.post(
        "/api/v1/ingest",
        files={"fir": ("test.csv", b"record_id\n1", "text/csv")}
    )
    assert response.status_code == 403


def test_ingest_unsupported_type(client, sp_token):
    response = client.post(
        "/api/v1/ingest",
        files={"fir": ("test.txt", b"record_id\n1", "text/plain")}
    )
    assert response.status_code == 415


def test_ingest_too_large(client, sp_token):
    large_content = b"a" * (5 * 1024 * 1024 + 1)
    response = client.post(
        "/api/v1/ingest",
        files={"fir": ("test.csv", large_content, "text/csv")}
    )
    assert response.status_code == 413


def test_ingest_success(client, sp_token):
    FIR_HEADER = "record_id,fir_number,fir_year,station_name,district,incident_time,offence_category,section,person_name,person_role,phone_number,national_id\n"
    data = (FIR_HEADER + "r1,F1,2026,S1,D1,2026-01-01T10:00:00Z,Theft,379,Alice Smith,ACCUSED,9999999999,NID1\n").encode("utf-8")
    
    response = client.post(
        "/api/v1/ingest",
        files={"fir": ("valid.csv", data, "text/csv")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["summary"]["accepted"] == 1
    assert data["summary"]["rejected"] == 0


def test_ingest_fatal_error(client, sp_token):
    data = b"wrong_header\nfoo"
    
    response = client.post(
        "/api/v1/ingest",
        files={"fir": ("fatal.csv", data, "text/csv")}
    )
    assert response.status_code == 422
    assert "Fatal validation error" in response.json()["detail"]
