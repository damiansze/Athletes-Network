"""Prüft den Permutationstest aus centrality_utils gegen eine einfache Referenzrechnung."""

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest
from scipy.stats import rankdata, spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from centrality_utils import monadic_permutation_tests  # noqa: E402


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
