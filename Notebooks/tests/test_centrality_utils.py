"""Small, exact checks for the chapter 6 analysis helpers.

These tests intentionally use toy networks: running them must never start the
expensive calculations on the project's complete athlete network.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys

import networkx as nx
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from scipy.stats import rankdata, spearmanr


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from centrality_utils import (  # noqa: E402
    expensive_centrality,
    graph_metadata,
    group_centrality,
    load_work_graph,
    monadic_permutation_tests,
)


@pytest.fixture
def graph():
    """Unequal weights ensure weighted paths would produce different results."""
    result = nx.Graph()
    result.add_weighted_edges_from(
        [("a", "b", 20), ("b", "c", 2), ("c", "d", 3),
         ("b", "d", 30), ("d", "e", 8)]
    )
    return result


def cache_call(graph, path, metric="harmonic", **kwargs):
    metadata = graph_metadata(graph, "a" * 64, threshold=2)
    return expensive_centrality(graph, metric, path, metadata, **kwargs)


def test_load_graph_filters_edges_and_preserves_isolated_nodes(tmp_path):
    original = nx.Graph()
    original.add_nodes_from(["a", "b", "c", "isolated"])
    original.add_edge("a", "b", weight=1)
    original.add_edge("b", "c", weight=2)
    source = tmp_path / "athletes.gexf"
    nx.write_gexf(original, source)
    source_bytes = source.read_bytes()

    filtered, source_sha = load_work_graph(source, threshold=2)

    assert set(filtered) == set(original)
    assert set(map(frozenset, filtered.edges)) == {frozenset({"b", "c"})}
    assert nx.number_of_isolates(filtered) == 2
    assert source_sha == hashlib.sha256(source_bytes).hexdigest()
    assert source.read_bytes() == source_bytes


@pytest.mark.parametrize("metric", ["harmonic", "betweenness"])
def test_expensive_measures_are_exact_and_ignore_edge_weights(graph, tmp_path, metric):
    values, status = cache_call(
        graph, tmp_path / f"{metric}.parquet", metric,
        recompute=True, batch_size=2,
    )

    assert status["status"] == "computed"
    assert values is not None
    if metric == "harmonic":
        reference = nx.harmonic_centrality(graph, distance=None)
        reference = {node: value / (len(graph) - 1) for node, value in reference.items()}
        weighted = nx.harmonic_centrality(graph, distance="weight")
        assert any(not np.isclose(reference[n], weighted[n] / (len(graph) - 1)) for n in graph)
    else:
        reference = nx.betweenness_centrality(graph, normalized=True, weight=None)
        weighted = nx.betweenness_centrality(graph, normalized=True, weight="weight")
        assert any(not np.isclose(reference[n], weighted[n]) for n in graph)
    pd.testing.assert_series_equal(
        values.sort_index(), pd.Series(reference, name=metric).sort_index(),
        check_index_type=False, check_names=False, atol=1e-12, rtol=1e-12,
    )


def test_missing_cache_does_not_start_expensive_computation(graph, tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("A missing cache must not trigger calculation by default")

    for name in ("harmonic_centrality", "betweenness_centrality", "all_pairs_shortest_path_length"):
        monkeypatch.setattr(nx, name, forbidden)
    path = tmp_path / "missing.parquet"

    for metric in ("harmonic", "betweenness"):
        values, status = cache_call(graph, path, metric)
        assert values is None
        assert status["status"] == "missing"
    assert not path.exists()


def test_valid_cache_roundtrip_preserves_values_and_embedded_metadata(graph, tmp_path, monkeypatch):
    path = tmp_path / "harmonic.parquet"
    original, _ = cache_call(graph, path, recompute=True)
    arrow_table = pq.read_table(path)
    assert b"centrality_metadata" in arrow_table.schema.metadata

    def forbidden(*args, **kwargs):
        pytest.fail("Loading a valid cache must not recalculate centrality")

    monkeypatch.setattr(nx, "all_pairs_shortest_path_length", forbidden)
    loaded, status = cache_call(graph, path)

    assert status["status"] == "loaded"
    pd.testing.assert_series_equal(original, loaded)


@pytest.mark.parametrize("change", ["source", "threshold", "population", "nodes"])
def test_cache_rejects_changed_graph_metadata(graph, tmp_path, change):
    path = tmp_path / "harmonic.parquet"
    cache_call(graph, path, recompute=True)
    changed = nx.relabel_nodes(graph, {"a": "different"}) if change == "nodes" else graph
    metadata = graph_metadata(
        changed,
        "b" * 64 if change == "source" else "a" * 64,
        threshold=3 if change == "threshold" else 2,
        population="full_graph" if change == "population" else "giant_component",
    )

    values, status = expensive_centrality(changed, "harmonic", path, metadata)

    assert values is None
    assert status["status"] == "invalid"
    assert status["reason"]


def test_cache_rejects_wrong_metric(graph, tmp_path):
    path = tmp_path / "centrality.parquet"
    cache_call(graph, path, "harmonic", recompute=True)

    values, status = cache_call(graph, path, "betweenness")

    assert values is None
    assert status["status"] == "invalid"


def test_corrupt_parquet_is_skipped_without_calculation(graph, tmp_path):
    path = tmp_path / "harmonic.parquet"
    path.write_bytes(b"not a parquet file")

    values, status = cache_call(graph, path)

    assert values is None
    assert status["status"] == "invalid"
    assert status["reason"]


@pytest.mark.parametrize("bad_value", [np.nan, np.inf, -0.01, 1.01])
def test_cache_rejects_nonfinite_or_out_of_range_normalized_values(graph, tmp_path, bad_value):
    path = tmp_path / "harmonic.parquet"
    cache_call(graph, path, recompute=True)
    table = pq.read_table(path)
    invalid = table["value"].to_pylist()
    invalid[0] = bad_value
    table = table.set_column(table.schema.get_field_index("value"), "value", pa.array(invalid))
    pq.write_table(table, path)

    values, status = cache_call(graph, path)

    assert values is None
    assert status["status"] == "invalid"


def test_cache_rejects_node_rows_that_do_not_match_graph(graph, tmp_path):
    path = tmp_path / "harmonic.parquet"
    cache_call(graph, path, recompute=True)
    table = pq.read_table(path)
    node_ids = table["node_id"].to_pylist()
    node_ids[0] = node_ids[1]  # Duplicate one node and remove another.
    table = table.set_column(table.schema.get_field_index("node_id"), "node_id", pa.array(node_ids))
    pq.write_table(table, path)

    values, status = cache_call(graph, path)

    assert values is None
    assert status["status"] == "invalid"


def brute_group_reference(graph, members):
    members = set(members)
    outside = set(graph) - members
    shortest = {
        node: min(
            (nx.shortest_path_length(graph, member, node)
             for member in members if nx.has_path(graph, member, node)),
            default=np.inf,
        )
        for node in outside
    }
    return {
        "size": len(members),
        "outside": len(outside),
        "reached_direct": sum(distance == 1 for distance in shortest.values()),
        "reached_any": sum(np.isfinite(distance) for distance in shortest.values()),
        "group_degree": sum(distance == 1 for distance in shortest.values()) / len(outside),
        "group_closeness": sum(1 / distance for distance in shortest.values()) / len(outside),
    }


@pytest.mark.parametrize("members", [["a"], ["a", "c"], ["a", "a", "c"]])
def test_group_measures_use_nearest_member_and_all_outside_nodes(members):
    graph = nx.Graph()
    graph.add_edges_from([("a", "b"), ("b", "c"), ("c", "d"), ("d", "e")])
    graph.add_edge("unreachable1", "unreachable2")
    graph.add_node("isolated")

    result = group_centrality(graph, members)
    reference = brute_group_reference(graph, members)

    for key, expected in reference.items():
        assert result[key] == pytest.approx(expected), key
    # Disconnected outsiders contribute zero, but remain in the denominator.
    assert result["outside"] > result["reached_any"]


@pytest.mark.parametrize("members", [[], ["unknown"], ["a", "b", "c", "d", "e"]])
def test_group_measures_reject_invalid_or_undefined_groups(graph, members):
    with pytest.raises(ValueError):
        group_centrality(graph, members)


def permutation_reference(frame, score, metrics, permutations, seed):
    """Independent one-sided Spearman test, including the +1 correction."""
    complete = frame[[score, *metrics]].replace([np.inf, -np.inf], np.nan).dropna()
    score_ranks = rankdata(complete[score])
    centered = score_ranks - score_ranks.mean()
    score_unit = centered / np.linalg.norm(centered)
    metric_ranks = np.column_stack([rankdata(complete[metric]) for metric in metrics])
    metric_ranks -= metric_ranks.mean(axis=0)
    metric_unit = metric_ranks / np.linalg.norm(metric_ranks, axis=0)
    observed = score_unit @ metric_unit
    exceedances = np.zeros(len(metrics), dtype=int)
    rng = np.random.default_rng(seed)
    for _ in range(permutations):
        simulated = rng.permutation(score_unit) @ metric_unit
        exceedances += simulated >= observed - 1e-12
    return complete, observed, (exceedances + 1) / (permutations + 1)


def test_monadic_permutation_matches_one_sided_reference_with_ties_and_missing_values():
    frame = pd.DataFrame({
        "points": [1, 1, 2, 4, 5, np.nan, 6, np.inf],
        "positive": [10, 20, 20, 40, 40, 50, 60, 70],
        "negative": [9, 8, 8, 2, 1, 2, np.nan, 1],
    })
    metrics = ["positive", "negative"]
    permutations, seed = 199, 321
    complete, observed, p_values = permutation_reference(frame, "points", metrics, permutations, seed)

    result = monadic_permutation_tests(
        frame, "points", metrics, n_permutations=permutations, seed=seed, alpha=0.05,
    )

    np.testing.assert_allclose(result.loc[metrics, "rho"], observed, atol=1e-12)
    np.testing.assert_allclose(result.loc[metrics, "p"], p_values)
    assert (result["n"] == len(complete)).all()
    assert (result["B"] == permutations).all()
    assert (result["seed"] == seed).all()
    assert result.loc["negative", "p"] == 1.0
    assert (result["p"] >= 1 / (permutations + 1)).all()
    for metric in metrics:
        assert result.loc[metric, "rho"] == pytest.approx(spearmanr(complete["points"], complete[metric]).statistic)
    # Two-test Holm correction, in the original metric order.
    ordered = np.argsort(p_values)
    adjusted = np.empty(2)
    adjusted[ordered] = np.minimum(1, np.maximum.accumulate(p_values[ordered] * [2, 1]))
    np.testing.assert_allclose(result.loc[metrics, "p_holm"], adjusted)
    assert result.loc[metrics, "reject_holm"].tolist() == (adjusted <= 0.05).tolist()


def test_monadic_permutations_are_reproducible():
    frame = pd.DataFrame({"points": [1, 3, 2, 5, 4], "centrality": [1, 2, 3, 4, 5]})
    first = monadic_permutation_tests(frame, "points", ["centrality"], n_permutations=99, seed=42)
    second = monadic_permutation_tests(frame, "points", ["centrality"], n_permutations=99, seed=42)
    pd.testing.assert_frame_equal(first, second)


def test_constant_scores_have_no_defined_correlation_or_significance():
    frame = pd.DataFrame({"points": [100, 100, 100], "centrality": [0.1, 0.2, 0.3]})

    result = monadic_permutation_tests(frame, "points", ["centrality"], n_permutations=9, seed=42)

    assert pd.isna(result.loc["centrality", "rho"])
    assert pd.isna(result.loc["centrality", "p"])
    assert not result.loc["centrality", "reject_holm"]
    assert result.loc["centrality", "status"]
