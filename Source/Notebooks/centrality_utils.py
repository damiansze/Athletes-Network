"""Hilfsfunktionen für 05_zentralitaet.ipynb."""

import math
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import rankdata


def load_work_graph(path, threshold=2):
    """Athletennetz laden und nur Kanten mit mindestens `threshold` gemeinsamen Tagen behalten."""
    graph = nx.read_gexf(path)
    graph.remove_edges_from([(u, v) for u, v, w in graph.edges(data='weight') if w < threshold])
    return graph


def cached_centrality(graph, metric, path, recompute=False):
    """Harmonic Closeness oder Betweenness aus dem Cache laden oder mit NetworkX berechnen."""
    path = Path(path)
    if path.exists() and not recompute:
        return pd.read_parquet(path).set_index('node')['value']
    if metric == 'harmonic':
        values = pd.Series(nx.harmonic_centrality(graph)) / (len(graph) - 1)
    else:
        values = pd.Series(nx.betweenness_centrality(graph))
    pd.DataFrame({'node': values.index, 'value': values.to_numpy()}).to_parquet(path, index=False)
    return values


def group_centrality(graph, members):
    """Group Degree und Group Closeness: Distanz jedes Aussenstehenden zum nächsten Mitglied."""
    members = set(members)
    distance = nx.multi_source_dijkstra_path_length(graph, members, weight=lambda u, v, d: 1)
    outside = len(graph) - len(members)
    direct = sum(d == 1 for d in distance.values())
    return {'size': len(members), 'outside': outside, 'reached_direct': direct,
            'reached_any': len(distance) - len(members), 'group_degree': direct / outside,
            'group_closeness': math.fsum(1 / d for d in distance.values() if d > 0) / outside}


def monadic_permutation_tests(frame, score_column, metric_columns, n_permutations=9999,
                              seed=42, alpha=0.05):
    """Einseitige Spearman-Permutationstests mit Holm-Korrektur.

    Die Ränge der Punkte werden permutiert, die Zentralitäten bleiben fest.
    p = (Anzahl permutierter ρ >= beobachtetes ρ + 1) / (B + 1).
    """
    metrics = list(metric_columns)
    data = frame[[score_column, *metrics]].replace([np.inf, -np.inf], np.nan).dropna()
    scores = rankdata(data[score_column])
    scores -= scores.mean()
    score_norm = np.linalg.norm(scores)
    ranks = np.column_stack([rankdata(data[m]) for m in metrics])
    ranks -= ranks.mean(axis=0)
    unit_metrics = ranks / np.linalg.norm(ranks, axis=0)
    observed = np.clip(scores @ unit_metrics / score_norm, -1.0, 1.0)

    rng = np.random.default_rng(seed)
    exceedances = np.zeros(len(metrics), dtype=np.int64)
    for _ in range(n_permutations):
        exceedances += rng.permutation(scores) @ unit_metrics / score_norm >= observed - 1e-12
    p = (exceedances + 1) / (n_permutations + 1)

    order = np.argsort(p)
    p_holm = np.empty_like(p)
    p_holm[order] = np.minimum(1.0, np.maximum.accumulate(p[order] * np.arange(len(p), 0, -1)))
    return pd.DataFrame({'rho': observed, 'n': len(data), 'p': p, 'p_holm': p_holm,
                         'reject_holm': p_holm <= alpha}, index=pd.Index(metrics, name='metric'))
