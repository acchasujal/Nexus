from __future__ import annotations

from backend.app.db.in_memory import InMemoryBackendRepository


def test_incident_edge_index_matches_full_edge_scan() -> None:
    repo = InMemoryBackendRepository()
    case_id = repo.case_ids[0]

    expected = [
        edge
        for edge in repo.edges
        if edge.get("source_id") == case_id or edge.get("target_id") == case_id
    ]

    assert repo.incident_edges[case_id] == expected
