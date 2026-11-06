"""Prüft die eigenen Teile der Link Prediction: Datensplit, Kandidaten und Evaluation."""

from pathlib import Path
import sys

import networkx as nx
import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from link_prediction_utils import candidate_pairs, evaluate_scores, temporal_split  # noqa: E402


def test_temporal_split_uses_inclusive_years_and_excludes_2020():
    dates = ["2015-12-31", "2016-01-01", "2019-12-31", "2020-01-01",
             "2020-12-31", "2021-01-01", "2025-12-31", "2026-01-01"]
    source = pd.DataFrame({"athlete_node": "a", "event_id": [f"e{i}" for i in range(8)],
                           "best_date": dates})

    train, test, _ = temporal_split(source)

    assert train["event_id"].tolist() == ["e1", "e2"]
    assert test["event_id"].tolist() == ["e5", "e6"]


def test_candidates_are_unconnected_core_pairs():
    adjacency = nx.to_scipy_sparse_array(nx.path_graph(4), format="csr")  # 0-1-2-3

    i, j = candidate_pairs(adjacency, np.array([0, 1, 3]))

    # Kernknoten 0 und 1 sind verbunden, die Paare mit Knoten 3 nicht.
    assert list(zip(i.tolist(), j.tolist())) == [(0, 2), (1, 2)]


def test_evaluation_uses_number_of_new_edges_and_correct_random_baseline():
    labels = np.array([True, False, True, False, False, False])
    result = evaluate_scores({"method": np.array([10, 9, 8, 7, 6, 5])}, labels, seed=42).iloc[0]
    assert result["k"] == 2
    assert result["n_candidates"] == 6
    assert result["true_positives"] == 1
    assert result["precision_at_k"] == pytest.approx(0.5)
    assert result["random_precision"] == pytest.approx(2 / 6)
    assert result["lift"] == pytest.approx(1.5)
