"""Independent toy-data checks for the retrospective link-prediction experiment.

NetworkX supplies reference scores only on small graphs. No test opens project
data or recomputes any of the existing centrality analyses.
"""

from __future__ import annotations

from pathlib import Path
import sys

import networkx as nx
import numpy as np
import pandas as pd
import pytest
from scipy import sparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from link_prediction_utils import (  # noqa: E402
    attribute_scores,
    candidate_pairs,
    core_nodes,
    evaluate_scores,
    network_scores,
    prepare_events,
    project_events,
    rank_candidates,
    temporal_split,
    tie_sensitivity,
)


def events(rows):
    return pd.DataFrame(rows, columns=["athlete_node", "event_id", "best_date"])


def test_temporal_split_uses_inclusive_years_and_excludes_2020():
    dates = ["2015-12-31", "2016-01-01", "2019-12-31", "2020-01-01",
             "2020-12-31", "2021-01-01", "2025-12-31", "2026-01-01"]
    source = events([("a", f"e{i}", date) for i, date in enumerate(dates)])

    train, test, audit = temporal_split(source)

    assert train["event_id"].tolist() == ["e1", "e2"]
    assert test["event_id"].tolist() == ["e5", "e6"]
    assert set(train["event_id"]).isdisjoint(test["event_id"])
    assert isinstance(audit, dict)
    assert source["best_date"].tolist() == dates  # Input remains unchanged.


def test_prepare_events_deduplicates_participations_not_distinct_meets():
    source = events([
        ("a", "e1", "2018-01-01"), ("a", "e1", "2018-01-01"),
        ("b", "e1", "2018-01-01"), ("a", "e2", "2018-01-01"),
    ])
    clean = prepare_events(source)
    assert len(clean) == 3
    assert not clean.duplicated(["athlete_node", "event_id"]).any()
    assert clean.loc[clean["athlete_node"].eq("a"), "event_id"].nunique() == 2


def test_prepare_events_normalizes_clock_times_within_the_same_day():
    clean = prepare_events(events([
        ("a", "e1", "2018-01-01 08:30"),
        ("b", "e1", "2018-01-01 15:00"),
    ]))
    assert clean["best_date"].nunique() == 1
    assert clean["best_date"].iloc[0] == pd.Timestamp("2018-01-01")


def test_one_event_id_cannot_describe_different_days():
    with pytest.raises(ValueError):
        prepare_events(events([
            ("a", "e1", "2018-01-01"), ("b", "e1", "2021-01-01"),
        ]))


@pytest.mark.parametrize("column,value", [
    ("athlete_node", None), ("athlete_node", ""),
    ("athlete_node", " a"), ("athlete_node", 123),
    ("event_id", None), ("event_id", ""),
    ("best_date", None), ("best_date", "not-a-date"),
])
def test_prepare_events_rejects_unusable_keys_and_dates(column, value):
    source = events([("a", "e1", "2018-01-01")])
    source[column] = source[column].astype(object)
    source.loc[0, column] = value
    with pytest.raises(ValueError):
        prepare_events(source)


def test_core_counts_unique_event_ids_and_requires_both_periods():
    train = events([
        ("a", "t1", "2018-01-01"), ("a", "t2", "2018-01-01"),
        ("a", "t3", "2018-01-02"), ("a", "t3", "2018-01-02"),
        ("b", "t1", "2018-01-01"), ("b", "t2", "2018-01-01"),
        ("b", "t3", "2018-01-02"),
        ("c", "t1", "2018-01-01"), ("c", "t1", "2018-01-01"),
    ])
    test = events([
        ("a", "q1", "2022-01-01"), ("a", "q2", "2022-01-02"),
        ("a", "q3", "2022-01-03"),
        ("b", "q1", "2022-01-01"), ("b", "q2", "2022-01-02"),
    ])
    assert core_nodes(train, test).tolist() == ["a"]
    assert core_nodes(train, training_only=True).tolist() == ["a", "b"]
    assert core_nodes(train, test.iloc[:0], training_only=True).tolist() == ["a", "b"]
    assert core_nodes(train, object(), training_only=True).tolist() == ["a", "b"]


def test_projection_counts_shared_event_days_once_and_preserves_isolates():
    source = events([
        ("a", "e1", "2018-01-01"), ("a", "e1", "2018-01-01"),
        ("b", "e1", "2018-01-01"),
        ("a", "e2", "2018-01-02"), ("b", "e2", "2018-01-02"),
        ("c", "e2", "2018-01-02"), ("d", "e3", "2018-01-03"),
    ])
    nodes, weights = project_events(source, nodes=["d", "c", "b", "a", "extra"])
    assert sparse.issparse(weights)
    index = dict(zip(nodes, range(len(nodes))))
    assert weights[index["a"], index["b"]] == 2
    assert weights[index["a"], index["c"]] == 1
    assert weights[index["b"], index["c"]] == 1
    assert weights.getrow(index["d"]).nnz == 0
    assert weights.getrow(index["extra"]).nnz == 0
    assert not weights.diagonal().any()
    assert (weights != weights.T).nnz == 0


def test_projection_rejects_node_list_that_silently_drops_training_athletes():
    source = events([("a", "e1", "2018-01-01"), ("b", "e1", "2018-01-01")])
    with pytest.raises(ValueError):
        project_events(source, nodes=["a"])


def test_candidates_use_core_order_and_exclude_all_observed_edges():
    graph = nx.Graph()
    graph.add_nodes_from(range(5))
    graph.add_weighted_edges_from([(0, 2, 1), (2, 3, 7), (1, 4, 1)])
    adjacency = nx.to_scipy_sparse_array(graph, nodelist=range(5), format="csr")
    core = np.array([3, 0, 2, 4])
    pairs = candidate_pairs(adjacency, core)

    assert list(zip(*pairs)) == [(0, 1), (0, 3), (1, 3), (2, 3)]
    assert all(i < j for i, j in zip(*pairs))
    assert all(not graph.has_edge(core[i], core[j]) for i, j in zip(*pairs))


@pytest.fixture
def reference_graph():
    graph = nx.Graph()
    graph.add_nodes_from(["a", "b", "c", "d", "e", "f", "g", "isolated"])
    graph.add_weighted_edges_from([
        ("a", "c", 11), ("a", "d", 1), ("a", "e", 5),
        ("b", "c", 2), ("b", "d", 15), ("b", "f", 3),
        ("c", "d", 8), ("e", "g", 1), ("f", "g", 4),
    ])
    nx.set_node_attributes(graph, {
        "a": 0, "b": 0, "c": 0, "d": 1,
        "e": 2, "f": 0, "g": 1, "isolated": 1,
    }, "community")
    return graph


@pytest.mark.parametrize("block_size", [1, 2, 256])
def test_sparse_scores_match_networkx_using_all_training_neighbors(reference_graph, block_size):
    graph = reference_graph
    nodes = list(graph)
    adjacency = nx.to_scipy_sparse_array(graph, nodelist=nodes, format="csr")
    core_nodes_ordered = ["b", "a", "g", "isolated"]
    core = np.array([nodes.index(node) for node in core_nodes_ordered])
    pairs = candidate_pairs(adjacency, core)
    node_pairs = [(core_nodes_ordered[i], core_nodes_ordered[j]) for i, j in zip(*pairs)]
    communities = np.array([graph.nodes[node]["community"] for node in nodes])
    scores = network_scores(adjacency, core, pairs, communities, block_size=block_size)
    expected = {
        "common_neighbours": [len(list(nx.common_neighbors(graph, u, v))) for u, v in node_pairs],
        "adamic_adar": [s for _, _, s in nx.adamic_adar_index(graph, node_pairs)],
        "preferential_attachment": [s for _, _, s in nx.preferential_attachment(graph, node_pairs)],
        "soundarajan_hopcroft": [s for _, _, s in nx.cn_soundarajan_hopcroft(graph, node_pairs)],
    }
    assert set(scores) == set(expected)
    for name, expected_values in expected.items():
        np.testing.assert_allclose(scores[name], expected_values, rtol=1e-12, atol=1e-12)
    ab = node_pairs.index(("b", "a"))
    assert scores["common_neighbours"][ab] == 2  # Both neighbors lie outside the core.
    assert scores["soundarajan_hopcroft"][ab] == 3  # Only c shares all three labels.


def test_soundarajan_bonus_requires_both_endpoints_and_neighbor_in_same_community():
    graph = nx.path_graph(3)
    adjacency = nx.to_scipy_sparse_array(graph, format="csr")
    core = np.array([0, 2])
    pairs = candidate_pairs(adjacency, core)
    for communities, expected in [([0, 0, 0], 2), ([0, 1, 0], 1), ([0, 0, 1], 1)]:
        scores = network_scores(adjacency, core, pairs, np.array(communities))
        assert scores["soundarajan_hopcroft"].tolist() == [expected]


def test_blockwise_scores_preserve_an_arbitrary_candidate_order(reference_graph):
    graph = reference_graph
    adjacency = nx.to_scipy_sparse_array(graph, format="csr")
    core = np.arange(len(graph))
    pairs = candidate_pairs(adjacency, core)
    communities = np.array([graph.nodes[node]["community"] for node in graph])
    expected = network_scores(adjacency, core, pairs, communities, block_size=2)
    order = np.random.default_rng(16).permutation(len(pairs[0]))
    reordered = tuple(values[order] for values in pairs)
    actual = network_scores(adjacency, core, reordered, communities, block_size=2)
    for name in expected:
        np.testing.assert_allclose(actual[name], expected[name][order], rtol=1e-12, atol=1e-12)


def test_network_scores_reject_an_existing_training_edge():
    adjacency = nx.to_scipy_sparse_array(nx.path_graph(3), format="csr")
    with pytest.raises(ValueError):
        network_scores(adjacency, np.arange(3), (np.array([0]), np.array([1])), np.zeros(3))


def test_common_neighbor_counts_do_not_overflow_byte_dtype():
    graph = nx.complete_bipartite_graph(2, 300)
    adjacency = nx.to_scipy_sparse_array(graph, dtype=np.uint8, format="csr")
    core = np.array([0, 1])
    pairs = candidate_pairs(adjacency, core)
    scores = network_scores(adjacency, core, pairs, np.zeros(len(graph), dtype=int))
    assert scores["common_neighbours"].tolist() == [300]
    assert scores["soundarajan_hopcroft"].tolist() == [600]
    assert scores["preferential_attachment"].tolist() == [90000]
    np.testing.assert_allclose(scores["adamic_adar"], [300 / np.log(2)])


def test_test_events_cannot_enter_training_projection_or_scores():
    source = events([
        ("a", "train", "2019-12-31"), ("b", "train", "2019-12-31"),
        ("a", "future", "2021-01-01"), ("c", "future", "2021-01-01"),
    ])
    train, test, _ = temporal_split(source)
    nodes, adjacency = project_events(train, nodes=["a", "b", "c"])
    _, test_adjacency = project_events(test, nodes=nodes)
    lookup = dict(zip(nodes, range(len(nodes))))
    assert adjacency[lookup["a"], lookup["c"]] == 0
    assert test_adjacency[lookup["a"], lookup["c"]] == 1
    core = np.arange(len(nodes))
    pairs = candidate_pairs(adjacency, core)
    scores = network_scores(adjacency, core, pairs, np.zeros(len(nodes)))
    ac = list(zip(*pairs)).index(tuple(sorted([lookup["a"], lookup["c"]])))
    assert scores["common_neighbours"][ac] == 0
    assert scores["preferential_attachment"][ac] == 0


@pytest.mark.parametrize("missing", [None, np.nan, pd.NA, "", "Unknown", "nan"])
def test_two_missing_nations_never_count_as_same(missing):
    attrs = pd.DataFrame({"nation": [missing, missing, "Switzerland", "Switzerland"],
                          "birth_year": [2000, 2000, 2000, 2001]})
    pairs = (np.array([0, 0, 2]), np.array([1, 2, 3]))
    scores = attribute_scores(attrs, pairs)
    assert scores["same_nation"].tolist() == [0, 0, 1]


def test_attribute_combination_is_lexicographic_and_missing_birth_is_last_within_group():
    attrs = pd.DataFrame({
        "nation": ["A", "A", "B", "A", "B", "A"],
        "birth_year": [2000, 2002, 2000, np.nan, np.nan, 1950],
    })
    pairs = (np.zeros(5, dtype=int), np.arange(1, 6))
    scores = attribute_scores(attrs, pairs)
    # Nation A: gap 2, gap 50, missing. Nation B: gap 0, missing.
    assert rank_candidates(scores["nation_birth_year"], seed=42).tolist() == [0, 4, 2, 1, 3]
    assert scores["birth_year"][1] > scores["birth_year"][0] > scores["birth_year"][4]
    assert scores["birth_year"][4] > scores["birth_year"][2]
    assert scores["birth_year"][2] == scores["birth_year"][3]
    assert all(np.isfinite(values).all() for values in scores.values())


def test_future_performance_columns_are_irrelevant_to_attribute_scores():
    attrs = pd.DataFrame({"nation": ["A", "A", "B"], "birth_year": [2000, 2001, 2003],
                          "points": [900, 700, 100], "best_year": [2025, 2024, 2022]})
    pairs = (np.array([0, 0, 1]), np.array([1, 2, 2]))
    expected = attribute_scores(attrs, pairs)
    attrs["points"] = [0, 1000, 500]
    attrs["best_year"] = [1990, 1990, 1990]
    actual = attribute_scores(attrs, pairs)
    for key in expected:
        np.testing.assert_array_equal(actual[key], expected[key])


def test_evaluation_uses_number_of_new_edges_and_correct_random_baseline():
    labels = np.array([True, False, True, False, False, False])
    result = evaluate_scores({"method": np.array([10, 9, 8, 7, 6, 5])}, labels, seed=42).iloc[0]
    assert result["k"] == 2
    assert result["n_candidates"] == 6
    assert result["true_positives"] == 1
    assert result["precision_at_k"] == pytest.approx(0.5)
    assert result["random_precision"] == pytest.approx(2 / 6)
    assert result["lift"] == pytest.approx(1.5)


def test_tie_breaking_is_a_reproducible_random_permutation_and_preserves_scores():
    scores = np.array([2, 1, 2, 0, 1, 2, 0, 1], dtype=float)
    original = scores.copy()
    order = rank_candidates(scores, seed=17)
    expected = np.lexsort((np.random.default_rng(17).permutation(len(scores)), -scores))
    np.testing.assert_array_equal(order, expected)
    np.testing.assert_array_equal(order, rank_candidates(scores, seed=17))
    np.testing.assert_array_equal(scores, original)
    assert np.all(np.diff(scores[order]) <= 0)
    assert sorted(order.tolist()) == list(range(len(scores)))


def test_tie_seed_changes_order_without_changing_untied_order():
    tied = np.zeros(50)
    assert not np.array_equal(rank_candidates(tied, seed=3), rank_candidates(tied, seed=4))
    untied = np.arange(50, dtype=float)
    np.testing.assert_array_equal(rank_candidates(untied, seed=3), rank_candidates(untied, seed=4))


def test_evaluation_and_fast_tie_sensitivity_equal_full_sort_for_each_seed():
    labels = np.array([True, False, True, False, False, True, False, True, False, False])
    scores = {"strong_ties": np.array([3, 2, 2, 2, 2, 2, 1, 1, 0, 0]),
              "all_tied": np.zeros(10), "no_ties": np.arange(10)}
    seeds = (0, 1, 17, 42)
    sensitivity = tie_sensitivity(scores, labels, seeds=seeds)
    for seed in seeds:
        evaluated = evaluate_scores(scores, labels, seed=seed).set_index("method")
        subset = sensitivity[sensitivity["seed"].eq(seed)].set_index("method")
        for method, values in scores.items():
            chosen = rank_candidates(values, seed=seed)[: labels.sum()]
            hits = int(labels[chosen].sum())
            assert evaluated.loc[method, "true_positives"] == hits
            assert subset.loc[method, "true_positives"] == hits
            assert subset.loc[method, "precision_at_k"] == pytest.approx(hits / labels.sum())
            assert subset.loc[method, "lift"] == pytest.approx((hits / labels.sum()) / labels.mean())


@pytest.mark.parametrize("labels", [np.array([], dtype=bool), np.zeros(4, dtype=bool)])
def test_evaluation_rejects_undefined_zero_positive_experiment(labels):
    with pytest.raises(ValueError):
        evaluate_scores({"method": np.zeros(len(labels))}, labels)


def test_evaluation_rejects_inconsistent_candidate_populations():
    with pytest.raises(ValueError):
        evaluate_scores({"method": np.arange(3)}, np.array([True, False]))


@pytest.mark.parametrize("invalid_scores", [np.array([0.0, np.nan]), np.array([0.0, np.inf])])
def test_missing_scores_cannot_silently_change_the_evaluation_population(invalid_scores):
    with pytest.raises(ValueError):
        evaluate_scores({"method": invalid_scores}, np.array([True, False]))


def test_stricter_test_definition_gets_its_own_k_and_random_baseline():
    scores = {"method": np.array([9, 8, 7, 6, 5, 4])}
    test_weight = np.array([1, 2, 0, 3, 0, 0])
    main = evaluate_scores(scores, test_weight >= 1).iloc[0]
    repeated = evaluate_scores(scores, test_weight >= 2).iloc[0]
    assert main["k"] == 3
    assert main["random_precision"] == pytest.approx(0.5)
    assert main["precision_at_k"] == pytest.approx(2 / 3)
    assert repeated["k"] == 2
    assert repeated["random_precision"] == pytest.approx(1 / 3)
    assert repeated["precision_at_k"] == pytest.approx(0.5)


def test_all_positive_population_has_well_defined_perfect_evaluation():
    scores = {"method": np.array([1, 0, 0, 1])}
    labels = np.ones(4, dtype=bool)
    result = evaluate_scores(scores, labels).iloc[0]
    sensitivity = tie_sensitivity(scores, labels)
    assert result["precision_at_k"] == result["random_precision"] == result["lift"] == 1
    assert sensitivity["precision_at_k"].eq(1).all()
