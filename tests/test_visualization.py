"""Tests for the mind-map visualization layer."""

from __future__ import annotations

from src.visualization import (
    EdgeType,
    MapNode,
    NodeType,
    build_map_from_db,
    build_sample_map,
)


def test_sample_map_serializes():
    graph = build_sample_map().to_graph_data()
    assert graph["metadata"]["total_nodes"] > 0
    assert graph["metadata"]["total_edges"] > 0
    assert "bucket_summary" in graph["metadata"]


def test_node_color_and_size():
    node = MapNode("n", "Big", NodeType.ACCOUNT, "BUCKET_TAX", amount=50000)
    d = node.to_dict()
    assert d["color"] == "#4A90D9"  # tax bucket blue
    assert d["size"] == 70  # largest bucket


def test_build_map_from_db_reflects_seed(seeded_conn):
    fmap = build_map_from_db(seeded_conn)
    graph = fmap.to_graph_data()

    node_types = [n["type"] for n in graph["nodes"]]
    assert node_types.count(NodeType.HOUSEHOLD_MEMBER.value) == 2
    assert node_types.count(NodeType.ACCOUNT.value) == 4
    assert node_types.count(NodeType.BILL.value) == 4
    assert NodeType.INCOME.value in node_types

    # Bucket summary should aggregate account balances by bucket.
    buckets = graph["metadata"]["bucket_summary"]
    assert buckets.get("BUCKET_TAX") == 45000.0
    assert buckets.get("BUCKET_FREE") == 12000.0

    # Accounts are linked to their owning members.
    edge_types = {e["type"] for e in graph["edges"]}
    assert EdgeType.OWNED_BY.value in edge_types
    assert EdgeType.PAYS_FOR.value in edge_types
