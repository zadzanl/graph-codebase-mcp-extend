import asyncio
import os

import pytest
from unittest.mock import MagicMock, patch

from src.mcp.server import CodebaseKnowledgeGraphMCP
from src.neo4j_storage.graph_db import Neo4jDatabase

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.verify_connection.return_value = True
    return db

@pytest.fixture
def mcp_server(mock_db):
    with patch('src.mcp.server.Neo4jDatabase', return_value=mock_db), \
         patch('src.mcp.server.get_embedding_provider'), \
         patch('src.mcp.server.CodeEmbedder') as mock_code_embedder:
        provider = MagicMock()
        mock_code_embedder.return_value.provider = provider
        server = CodebaseKnowledgeGraphMCP(
            neo4j_uri="bolt://mock",
            neo4j_user="neo4j",
            neo4j_password="password",
        )
        server.db = mock_db
        server.code_embedder.provider = provider
        return server


def make_db_with_driver(driver):
    db = Neo4jDatabase.__new__(Neo4jDatabase)
    db.driver = driver
    db.database = "neo4j"
    return db


def make_node(node_id="node_id", name="node_name", labels=None, file_path="node_path.py"):
    node = MagicMock()
    node.labels = labels or ["Base", "Function"]
    values = {
        "id": node_id,
        "name": name,
        "file_path": file_path,
        "path": file_path,
    }
    node.get.side_effect = lambda key: values.get(key)
    return node


def test_calculate_cosine_similarity_handles_edge_cases(mcp_server):
    assert mcp_server._calculate_cosine_similarity([1, 0, 0], [1, 0, 0]) == pytest.approx(1.0)
    assert mcp_server._calculate_cosine_similarity([1, 0, 0], [0, 1, 0]) == pytest.approx(0.0)
    assert mcp_server._calculate_cosine_similarity([0, 0], [1, 1]) == 0.0
    assert mcp_server._calculate_cosine_similarity([1], [1, 2]) == 0.0
    assert mcp_server._calculate_cosine_similarity(["bad"], [1]) == 0.0


def test_resolve_group_threshold_clamps_and_uses_env(mcp_server):
    assert mcp_server._resolve_group_threshold(0.5) == pytest.approx(0.5)
    assert mcp_server._resolve_group_threshold(2.5) == pytest.approx(1.0)
    assert mcp_server._resolve_group_threshold(-0.3) == pytest.approx(0.0)
    assert mcp_server._resolve_group_threshold("bad") == pytest.approx(0.0)

    with patch.dict(os.environ, {"GROUP_THRESHOLD": "0.8"}):
        assert mcp_server._resolve_group_threshold(None) == pytest.approx(0.8)

    with patch.dict(os.environ, {"GROUP_THRESHOLD": "bad"}):
        assert mcp_server._resolve_group_threshold(None) == pytest.approx(0.7)

    with patch.dict(os.environ, {}, clear=True):
        assert mcp_server._resolve_group_threshold(None) == pytest.approx(0.7)


def test_get_group_max_groups_handles_invalid_values(mcp_server):
    with patch.dict(os.environ, {"GROUP_MAX_GROUPS": "3"}):
        assert mcp_server._get_group_max_groups() == 3

    for invalid_value in ["0", "-1", "bad"]:
        with patch.dict(os.environ, {"GROUP_MAX_GROUPS": invalid_value}):
            assert mcp_server._get_group_max_groups() == 10


def test_group_results_by_similarity_returns_required_shape(mcp_server):
    results = [
        {"node": {"name": "a", "embedding": [1, 0, 0]}, "score": 0.9},
        {"node": {"name": "b", "embedding": [0.99, 0, 0]}, "score": 0.8},
        {"node": {"name": "c", "embedding": [0, 1, 0]}, "score": 0.7},
        {"node": {"name": "missing"}, "score": 0.6},
    ]

    grouped = mcp_server._group_results_by_similarity(results, 0.9, max_groups=1)

    assert grouped["total_groups"] == 1
    assert grouped["total_ungrouped"] == 2
    assert set(grouped["groups"][0]) == {"id", "representative", "items", "similarity_score"}
    assert grouped["groups"][0]["id"] == "group_1"
    assert grouped["groups"][0]["similarity_score"] >= 0.9
    assert [item["node"]["name"] for item in grouped["groups"][0]["items"]] == ["a", "b"]
    assert [item["node"]["name"] for item in grouped["ungrouped"]] == ["c", "missing"]


def test_get_node_relationships_formats_aliases_and_limits():
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value = [{"m": make_node()}]
    db = make_db_with_driver(mock_driver)

    rels = db.get_node_relationships("source_id", relationship_types=["CALLS", "IMPORTS_FROM"], limit=5)

    assert len(rels["calls"]) == 1
    assert len(rels["imports"]) == 1
    assert rels["called_by"] == []
    assert rels["calls"][0] == {
        "id": "node_id",
        "name": "node_name",
        "type": "Function",
        "file_path": "node_path.py",
    }
    assert mock_session.run.call_count == 2


def test_get_node_relationships_returns_empty_on_connection_failure():
    db = make_db_with_driver(None)

    rels = db.get_node_relationships("missing")

    assert rels == {
        "calls": [],
        "called_by": [],
        "extends": [],
        "extended_by": [],
        "imports": [],
        "imported_by": [],
    }


def test_search_code_impl_default_includes_relationships(mcp_server, mock_db):
    mock_db.search_code_by_vector.side_effect = [
        [{"node": {"id": "n1", "name": "f1"}, "score": 0.9}],
        [],
        [],
        [],
    ]
    mock_db.get_node_relationships.return_value = mcp_server._empty_relationships()
    mcp_server.code_embedder.provider.embed_text.return_value = [0.1] * 1536

    response = asyncio.run(mcp_server._search_code_impl("test"))

    assert "results" in response
    assert "groups" not in response
    assert len(response["results"]) == 1
    assert response["results"][0]["relationships"] == mcp_server._empty_relationships()
    mock_db.get_node_relationships.assert_called_once_with("n1")


def test_search_code_impl_relationship_failure_falls_back(mcp_server, mock_db):
    mock_db.search_code_by_vector.side_effect = [
        [{"node": {"id": "n1", "name": "f1"}, "score": 0.9}],
        [],
        [],
        [],
    ]
    mock_db.get_node_relationships.side_effect = RuntimeError("relationship lookup failed")
    mcp_server.code_embedder.provider.embed_text.return_value = [0.1] * 1536

    response = asyncio.run(mcp_server._search_code_impl("test"))

    assert "error" not in response
    assert response["results"][0]["relationships"] == mcp_server._empty_relationships()


def test_search_code_impl_omits_relationships_when_disabled(mcp_server, mock_db):
    mock_db.search_code_by_vector.side_effect = [
        [{"node": {"id": "n1", "name": "f1"}, "score": 0.9}],
        [],
        [],
        [],
    ]
    mcp_server.code_embedder.provider.embed_text.return_value = [0.1] * 1536

    response = asyncio.run(mcp_server._search_code_impl("test", include_relationships=False))

    assert "results" in response
    assert "relationships" not in response["results"][0]
    mock_db.get_node_relationships.assert_not_called()


def test_search_code_impl_groups_with_explicit_threshold(mcp_server, mock_db):
    mock_db.search_code_by_vector.side_effect = [
        [
            {"node": {"id": "n1", "name": "a", "embedding": [1, 0]}, "score": 0.9},
            {"node": {"id": "n2", "name": "b", "embedding": [0.99, 0]}, "score": 0.8},
        ],
        [],
        [],
        [],
    ]
    mock_db.get_node_relationships.return_value = mcp_server._empty_relationships()
    mcp_server.code_embedder.provider.embed_text.return_value = [0.1] * 1536

    response = asyncio.run(mcp_server._search_code_impl("test", group_threshold=0.9))

    assert "groups" in response
    assert "results" not in response
    assert response["total_groups"] == 1


def test_search_code_impl_uses_env_threshold_when_none(mcp_server, mock_db):
    mock_db.search_code_by_vector.side_effect = [
        [{"node": {"id": "n1", "name": "a", "embedding": [1, 0]}, "score": 0.9}],
        [],
        [],
        [],
    ]
    mock_db.get_node_relationships.return_value = mcp_server._empty_relationships()
    mcp_server.code_embedder.provider.embed_text.return_value = [0.1] * 1536

    with patch.dict(os.environ, {"GROUP_THRESHOLD": "0.8"}):
        response = asyncio.run(mcp_server._search_code_impl("test", group_threshold=None))

    assert "groups" in response
    assert response["total_groups"] == 1


def test_search_code_impl_text_search_path(mcp_server, mock_db):
    mock_db.search_code_by_text.return_value = [
        {"node": {"id": "n1", "name": "text_match"}, "score": 0.7}
    ]

    response = asyncio.run(
        mcp_server._search_code_impl(
            "text",
            search_type="text",
            include_relationships=False,
        )
    )

    assert response == {"results": [{"node": {"id": "n1", "name": "text_match"}, "score": 0.7}]}
    mock_db.search_code_by_text.assert_called_once_with("text", 10)
