from backend.app.core.graph.graph_loader import GraphLoader
from backend.app.core.graph.algorithms.utils import NodeRecord, AdjEdge


def test_load_graph_valid():
    loader = GraphLoader()
    nodes = [
        NodeRecord(node_id="case1", entity_type="Case", properties={"fir_number": "123"}),
        NodeRecord(node_id="person1", entity_type="Person", properties={"full_name": "John Doe"}),
    ]
    edges = [
        AdjEdge(edge_type="ACCUSED_IN", source_id="person1", target_id="case1", properties={}),
    ]
    
    store = loader.load_graph(nodes, edges)
    
    assert len(store.nodes) == 2
    assert "case1" in store.nodes
    assert "person1" in store.nodes
    assert len(store.adj["person1"]) == 1
    assert store.adj["person1"][0].target_id == "case1"
    
    validation = loader.validate_graph(store)
    assert validation["is_valid"] is True
    assert validation["node_count"] == 2
    assert validation["edge_count"] == 1
    assert len(validation["errors"]) == 0
    assert len(validation["warnings"]) == 0


def test_validate_graph_missing_nodes():
    loader = GraphLoader()
    nodes = [
        NodeRecord(node_id="person1", entity_type="Person", properties={}),
    ]
    edges = [
        AdjEdge(edge_type="ACCUSED_IN", source_id="person1", target_id="case1", properties={}),
    ]
    
    store = loader.load_graph(nodes, edges)
    validation = loader.validate_graph(store)
    
    assert validation["is_valid"] is False
    assert any("Missing target node ID: case1" in err for err in validation["errors"])
    assert any("Orphan edge detected" in err for err in validation["errors"])


def test_validate_graph_duplicate_nodes():
    loader = GraphLoader()
    nodes = [
        NodeRecord(node_id="node1", entity_type="Person", properties={}),
        NodeRecord(node_id="node1", entity_type="Person", properties={"other": "data"}),
    ]
    store = loader.load_graph(nodes, [])
    validation = loader.validate_graph(store)
    
    assert validation["is_valid"] is False
    assert any("Duplicate node ID detected: node1" in err for err in validation["errors"])


def test_validate_graph_duplicate_edges():
    loader = GraphLoader()
    nodes = [
        NodeRecord(node_id="n1", entity_type="Person", properties={}),
        NodeRecord(node_id="n2", entity_type="Case", properties={}),
    ]
    edges = [
        AdjEdge(edge_type="E1", source_id="n1", target_id="n2"),
        AdjEdge(edge_type="E1", source_id="n1", target_id="n2"),
    ]
    store = loader.load_graph(nodes, edges)
    validation = loader.validate_graph(store)
    
    assert validation["is_valid"] is False
    assert any("Duplicate edge detected" in err for err in validation["errors"])


def test_validate_graph_self_loop():
    loader = GraphLoader()
    nodes = [
        NodeRecord(node_id="n1", entity_type="Person", properties={}),
    ]
    edges = [
        AdjEdge(edge_type="SELF", source_id="n1", target_id="n1"),
    ]
    store = loader.load_graph(nodes, edges)
    validation = loader.validate_graph(store)
    
    # Self-loops are warnings only, so graph is still valid
    assert validation["is_valid"] is True
    assert len(validation["warnings"]) == 1
    assert any("Self-loop detected on node: n1" in warn for warn in validation["warnings"])


def test_validate_graph_empty_and_invalid_ids():
    loader = GraphLoader()
    nodes = [
        NodeRecord(node_id="", entity_type="Person", properties={}),
        NodeRecord(node_id=123, entity_type="Case", properties={}),  # Invalid type (int instead of str)
    ]
    store = loader.load_graph(nodes, [])
    validation = loader.validate_graph(store)
    
    assert validation["is_valid"] is False
    assert any("Empty node ID found" in err for err in validation["errors"])
    assert any("Invalid node ID type" in err for err in validation["errors"])
