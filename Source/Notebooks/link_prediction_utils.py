"""Hilfsfunktionen für 08_link_prediction.ipynb."""

import networkx as nx
import numpy as np
import pandas as pd
from scipy import sparse


def _clean(events):
    """Eine Zeile pro Athlet und Veranstaltungstag, Datum ohne Uhrzeit."""
    clean = events[['athlete_node', 'event_id', 'best_date']].copy()
    clean['best_date'] = pd.to_datetime(clean['best_date']).dt.normalize()
    return (clean.drop_duplicates(['athlete_node', 'event_id'])
            .sort_values(['best_date', 'event_id', 'athlete_node']).reset_index(drop=True))


def temporal_split(events):
    """Training 2016 bis 2019, Test 2021 bis 2025, 2020 fällt weg."""
    clean = _clean(events)
    years = clean['best_date'].dt.year
    train = clean[years.between(2016, 2019)].reset_index(drop=True)
    test = clean[years.between(2021, 2025)].reset_index(drop=True)
    audit = {
        'input_rows': len(events), 'excluded_2020_rows': int(years.eq(2020).sum()),
        'train_rows': len(train), 'test_rows': len(test),
        'train_athletes': train['athlete_node'].nunique(), 'test_athletes': test['athlete_node'].nunique(),
        'train_event_days': train['event_id'].nunique(), 'test_event_days': test['event_id'].nunique(),
    }
    return train, test, audit


def core_nodes(train, test=None, min_events=3):
    """Athleten mit mindestens `min_events` Veranstaltungstagen im Training und, falls angegeben, im Test."""
    selected = None
    for frame in [train] if test is None else [train, test]:
        counts = _clean(frame).groupby('athlete_node')['event_id'].nunique()
        active = set(counts.index[counts.ge(min_events)])
        selected = active if selected is None else selected & active
    return np.asarray(sorted(selected), dtype=str)


def project_events(events, nodes=None):
    """Athletenprojektion als Matrix: Gewicht = Anzahl gemeinsamer Veranstaltungstage."""
    clean = _clean(events)
    node_ids = np.asarray(sorted(clean['athlete_node'].unique()) if nodes is None else nodes, dtype=str)
    rows = pd.Index(node_ids).get_indexer(clean['athlete_node'])
    columns, event_ids = pd.factorize(clean['event_id'], sort=True)
    incidence = sparse.csr_matrix((np.ones(len(clean), dtype=np.int32), (rows, columns)),
                                  shape=(len(node_ids), len(event_ids)))
    projection = (incidence @ incidence.T).tocsr()
    projection.setdiag(0)
    projection.eliminate_zeros()
    # Sortierte Indizes: Louvain hängt von der Reihenfolge der Nachbarn ab
    projection.sort_indices()
    return node_ids, projection


def candidate_pairs(adjacency, core_indices):
    """Alle im Training unverbundenen Paare (i < j) von Kernathleten."""
    connected = adjacency[core_indices][:, core_indices].toarray() > 0
    i, j = np.triu_indices(len(core_indices), k=1)
    free = ~connected[i, j]
    return i[free], j[free]


def _common_neighbours(graph, pairs):
    return ((a, b, len(list(nx.common_neighbors(graph, a, b)))) for a, b in pairs)


def network_scores(graph, u, v, chunk=1_000_000):
    """Die vier Netzwerkverfahren mit NetworkX für die Paare (u[k], v[k]).

    `graph` ist das ungewichtete Trainingsnetz mit dem Knotenattribut `community`.
    Die Paare werden in Blöcken übergeben, damit bei 15 Millionen Paaren der Speicher reicht.
    """
    methods = {'common_neighbours': _common_neighbours, 'adamic_adar': nx.adamic_adar_index,
               'preferential_attachment': nx.preferential_attachment,
               'soundarajan_hopcroft': nx.cn_soundarajan_hopcroft}
    scores = {name: [] for name in methods}
    for start in range(0, len(u), chunk):
        pairs = list(zip(u[start:start + chunk].tolist(), v[start:start + chunk].tolist()))
        for name, method in methods.items():
            scores[name].append(np.fromiter((s for *_, s in method(graph, pairs)), dtype=float, count=len(pairs)))
    return {name: np.concatenate(parts) for name, parts in scores.items()}


def attribute_scores(attributes, pairs):
    """Faustregeln: gleiche Nation, ähnlicher Jahrgang und beides kombiniert.

    Bei der Kombination zählt zuerst die gleiche Nation, dann die kleinere Jahrgangsdifferenz.
    Fehlende Jahrgänge kommen ans Ende.
    """
    i, j = pairs
    codes, _ = pd.factorize(attributes['nation'])
    same = codes[i] == codes[j]
    years = pd.to_numeric(attributes['birth_year'], errors='coerce').to_numpy(dtype=float, na_value=np.nan)
    missing_gap = np.nanmax(years) - np.nanmin(years) + 1
    gap = np.abs(years[i] - years[j])
    gap[np.isnan(gap)] = missing_gap
    return {'same_nation': same.astype(float), 'birth_year': -gap,
            'nation_birth_year': same * (missing_gap + 1) - gap}


def rank_candidates(scores, seed=42):
    """Kandidaten absteigend nach Score, Gleichstände in einer zufälligen, festen Reihenfolge."""
    priorities = np.random.default_rng(seed).permutation(len(scores))
    return np.lexsort((priorities, -np.asarray(scores, dtype=float)))


def evaluate_scores(scores, labels, seed=42):
    """Precision@K mit K = Anzahl neuer Kanten, für alle Verfahren mit denselben Gleichstandsregeln."""
    labels = np.asarray(labels, dtype=bool)
    n, k = len(labels), int(labels.sum())
    rows = []
    for method, values in scores.items():
        hits = int(labels[rank_candidates(values, seed)[:k]].sum())
        rows.append({'method': method, 'n_candidates': n, 'k': k, 'true_positives': hits,
                     'precision_at_k': hits / k, 'random_precision': k / n,
                     'lift': (hits / k) / (k / n), 'seed': seed})
    return pd.DataFrame(rows)


def tie_sensitivity(scores, labels, seeds=range(10)):
    """evaluate_scores für mehrere Seeds: Wie stark hängt das Ergebnis von den Gleichständen ab?"""
    return pd.concat([evaluate_scores(scores, labels, seed) for seed in seeds], ignore_index=True)
