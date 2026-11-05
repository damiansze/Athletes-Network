"""Temporal link prediction with sparse, unweighted training-neighbour scores.

Only the evaluation functions accept test-edge labels.  All node orders and
candidate orders are explicit, and ties use one seeded random total order that
is shared by all methods.  No full dense node-by-node matrix is constructed.
"""

from numbers import Integral

import numpy as np
import pandas as pd
from scipy import sparse


NETWORK_METHODS = (
    "common_neighbours", "adamic_adar", "preferential_attachment",
    "soundarajan_hopcroft",
)
ATTRIBUTE_METHODS = ("same_nation", "birth_year", "nation_birth_year")
METHODS = NETWORK_METHODS + ATTRIBUTE_METHODS
MISSING_NATIONS = {"", "unknown", "nan", "none", "null", "na", "n/a", "<na>"}


def prepare_events(events):
    """Validate event-day identities and remove duplicate athlete/event rows.

    An event day is the existing ``event_id`` (meeting, location, date and pool
    length), rather than a calendar date shared by unrelated meetings.  IDs
    must be nonempty strings.  Dates are normalised to midnight; a single
    event ID assigned to different calendar dates is rejected.
    """
    required = ["athlete_node", "event_id", "best_date"]
    if not set(required).issubset(events.columns):
        raise ValueError(f"Events require columns {required}")
    result = events[required].copy()
    for column in required[:2]:
        if result[column].isna().any():
            raise ValueError(f"Missing {column}")
        if not result[column].map(lambda value: isinstance(value, str)).all():
            raise ValueError(f"{column} must contain string IDs")
        # Refuse rather than silently merge inconsistent identifiers.
        if result[column].str.strip().ne(result[column]).any() or result[column].eq("").any():
            raise ValueError(f"Blank or surrounding whitespace in {column}")
    try:
        dates = pd.to_datetime(result["best_date"], errors="raise", format="mixed")
        if dates.dt.tz is not None:
            raise ValueError("Event dates must be timezone-naive local calendar dates")
        result["best_date"] = dates.dt.normalize()
    except (TypeError, AttributeError, ValueError) as exc:
        raise ValueError("Invalid event date") from exc
    if result["best_date"].isna().any():
        raise ValueError("Missing event date")
    if result.groupby("event_id", sort=False)["best_date"].nunique().gt(1).any():
        raise ValueError("An event_id has conflicting calendar dates")
    return (result.drop_duplicates(["athlete_node", "event_id"])
            .sort_values(["best_date", "event_id", "athlete_node"])
            .reset_index(drop=True))


def temporal_split(events):
    """Return 2016--2019 training, 2021--2025 test, and a count audit.

    Both endpoints are inclusive by year.  All of 2020 and all dates outside
    the stated windows are excluded, before projecting either graph.
    """
    clean = prepare_events(events)
    years = clean["best_date"].dt.year
    train_mask = years.between(2016, 2019)
    test_mask = years.between(2021, 2025)
    train = clean.loc[train_mask].reset_index(drop=True)
    test = clean.loc[test_mask].reset_index(drop=True)
    audit = {
        "input_rows": int(len(events)),
        "unique_rows": int(len(clean)),
        "duplicates_removed": int(len(events) - len(clean)),
        "excluded_2020_rows": int(years.eq(2020).sum()),
        "outside_windows_rows": int((~(train_mask | test_mask | years.eq(2020))).sum()),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_athletes": int(train["athlete_node"].nunique()),
        "test_athletes": int(test["athlete_node"].nunique()),
        "train_event_days": int(train["event_id"].nunique()),
        "test_event_days": int(test["event_id"].nunique()),
    }
    return train, test, audit


def core_nodes(train, test=None, min_events=3, training_only=False):
    """Sorted athletes with enough distinct event IDs in the required periods.

    The default uses both periods and is explicitly retrospective.  With
    ``training_only=True``, the test frame is never read.
    """
    if isinstance(min_events, bool) or not isinstance(min_events, Integral) or min_events < 1:
        raise ValueError("min_events must be a positive integer")
    train_count = prepare_events(train).groupby("athlete_node")["event_id"].nunique()
    selected = train_count.index[train_count.ge(min_events)]
    if not training_only:
        if test is None:
            raise ValueError("The retrospective core requires test event days")
        test_count = prepare_events(test).groupby("athlete_node")["event_id"].nunique()
        selected = selected.intersection(test_count.index[test_count.ge(min_events)])
    return np.asarray(sorted(selected), dtype=str)


def project_events(events, nodes=None):
    """Return node IDs and a weighted CSR athlete projection B @ B.T.

    Each distinct event day contributes at most one to a pair's weight.  All
    observed athletes are retained, including isolates.  An explicit node
    order may additionally contain isolates, but must contain every observed
    athlete.  Self-connections are removed.
    """
    clean = prepare_events(events)
    if nodes is None:
        node_ids = np.asarray(sorted(clean["athlete_node"].unique()), dtype=str)
    else:
        node_ids = np.asarray(nodes)
        if node_ids.ndim != 1 or pd.Index(node_ids).has_duplicates or pd.isna(node_ids).any():
            raise ValueError("nodes must be a unique one-dimensional ID sequence")
        if not all(isinstance(node, str) and node and node.strip() == node for node in node_ids):
            raise ValueError("nodes must contain nonempty string IDs")
    node_index = pd.Index(node_ids)
    rows = node_index.get_indexer(clean["athlete_node"])
    if (rows < 0).any():
        raise ValueError("Explicit nodes omit observed athletes")
    columns, event_ids = pd.factorize(clean["event_id"], sort=True)
    incidence = sparse.csr_matrix(
        (np.ones(len(clean), dtype=np.int32), (rows, columns)),
        shape=(len(node_ids), len(event_ids)), dtype=np.int32,
    )
    projection = (incidence @ incidence.T).tocsr()
    projection.setdiag(0)
    projection.eliminate_zeros()
    projection.sort_indices()
    return node_ids, projection


def _binary_adjacency(adjacency):
    matrix = sparse.csr_matrix(adjacency, copy=True)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("adjacency must be square")
    matrix.sum_duplicates()
    matrix.eliminate_zeros()
    if not np.isfinite(matrix.data).all() or (matrix.data <= 0).any():
        raise ValueError("Edge weights must be finite and positive")
    if np.any(matrix.diagonal()) or (matrix != matrix.T).nnz:
        raise ValueError("adjacency must be undirected without self-loops")
    matrix = matrix.astype(np.int32)
    matrix.data[:] = 1
    matrix.sort_indices()
    return matrix


def _core_indices(core_indices, n):
    indices = np.asarray(core_indices)
    if indices.ndim != 1 or not np.issubdtype(indices.dtype, np.integer):
        raise ValueError("core_indices must be a one-dimensional integer sequence")
    if len(np.unique(indices)) != len(indices) or ((indices < 0) | (indices >= n)).any():
        raise ValueError("core_indices must be unique valid training-node positions")
    return indices


def _pairs(pairs, n):
    if len(pairs) != 2:
        raise ValueError("pairs must be a tuple of two index arrays")
    i, j = (np.asarray(values) for values in pairs)
    if (i.ndim != 1 or j.ndim != 1 or len(i) != len(j)
            or not np.issubdtype(i.dtype, np.integer)
            or not np.issubdtype(j.dtype, np.integer)):
        raise ValueError("Pair indices must be equal-length integer vectors")
    if ((i < 0) | (j >= n) | (i >= j)).any():
        raise ValueError("Pairs must satisfy 0 <= i < j < number of core nodes")
    return i, j


def candidate_pairs(adjacency, core_indices):
    """Enumerate each unconnected unordered core pair once, in row order.

    The returned int32 arrays refer to the *local core order*.  Construction
    uses one O(core size) row at a time instead of a dense square mask.
    """
    matrix = _binary_adjacency(adjacency)
    core = _core_indices(core_indices, matrix.shape[0])
    induced = matrix[core][:, core].tocsr()
    n = len(core)
    total = n * (n - 1) // 2 - induced.nnz // 2
    i = np.empty(total, dtype=np.int32)
    j = np.empty(total, dtype=np.int32)
    position = 0
    for row in range(n - 1):
        neighbours = induced.indices[induced.indptr[row]:induced.indptr[row + 1]]
        available = np.ones(n - row - 1, dtype=bool)
        upper = neighbours[neighbours > row]
        available[upper - row - 1] = False
        columns = np.flatnonzero(available).astype(np.int32) + row + 1
        stop = position + len(columns)
        i[position:stop] = row
        j[position:stop] = columns
        position = stop
    assert position == total
    return i, j


def network_scores(adjacency, core_indices, pairs, communities, block_size=256):
    """CN, AA, PA and Soundarajan--Hopcroft from the full training graph.

    ``communities`` has one label per training node and must be estimated on
    training edges only by the caller.  All weights are ignored.  Sparse
    products are limited to ``block_size`` core rows at a time.  SH uses a
    copy of A with only within-community edges, so a bonus requires matching
    communities for both endpoints *and* the common neighbour.
    """
    if isinstance(block_size, bool) or not isinstance(block_size, Integral) or block_size < 1:
        raise ValueError("block_size must be a positive integer")
    matrix = _binary_adjacency(adjacency)
    core = _core_indices(core_indices, matrix.shape[0])
    i, j = _pairs(pairs, len(core))
    if np.asarray(matrix[core[i], core[j]]).ravel().any():
        raise ValueError("Scores require absent training edges")
    labels = np.asarray(communities)
    if labels.ndim != 1 or len(labels) != matrix.shape[0] or pd.isna(labels).any():
        raise ValueError("One nonmissing community label is required per training node")
    degree = np.diff(matrix.indptr).astype(np.int64)
    weights = np.zeros(len(degree), dtype=np.float64)
    valid = degree > 1
    weights[valid] = 1.0 / np.log(degree[valid])
    core_matrix = matrix[core]
    core_transpose = core_matrix.T.tocsc()
    within = matrix.copy()
    rows = np.repeat(np.arange(matrix.shape[0]), np.diff(matrix.indptr))
    within.data[labels[rows] != labels[within.indices]] = 0
    del rows
    within.eliminate_zeros()
    within_core = within[core]
    within_transpose = within_core.T.tocsc()
    del within
    scores = {
        "common_neighbours": np.zeros(len(i), dtype=np.int32),
        "adamic_adar": np.zeros(len(i), dtype=np.float64),
        "preferential_attachment": degree[core[i]] * degree[core[j]],
        "soundarajan_hopcroft": np.zeros(len(i), dtype=np.int32),
    }
    # Own candidates are already ordered.  Arbitrary caller order is also
    # supported without repeatedly scanning the entire candidate population.
    ordered = bool(len(i) < 2 or np.all(i[:-1] <= i[1:]))
    order = None if ordered else np.argsort(i, kind="stable")
    sorted_i = i if ordered else i[order]
    for start in range(0, len(core), block_size):
        stop = min(start + block_size, len(core))
        left, right = np.searchsorted(sorted_i, [start, stop])
        if left == right:
            continue
        positions = slice(left, right) if ordered else order[left:right]
        local_i, local_j = i[positions] - start, j[positions]
        common = core_matrix[start:stop] @ core_transpose
        scores["common_neighbours"][positions] = np.asarray(common[local_i, local_j]).ravel()
        del common
        adamic = core_matrix[start:stop].multiply(weights) @ core_transpose
        scores["adamic_adar"][positions] = np.asarray(adamic.tocsr()[local_i, local_j]).ravel()
        del adamic
        bonus = within_core[start:stop] @ within_transpose
        scores["soundarajan_hopcroft"][positions] = (
            scores["common_neighbours"][positions]
            + np.asarray(bonus[local_i, local_j]).ravel()
        )
    return scores


def attribute_scores(attributes, pairs):
    """Three static-profile heuristics, with rows already in core-node order.

    Missing/placeholder nations never match.  Missing birth years are ranked
    after all known year gaps.  The combined integer score is exactly
    lexicographic: same nation first, then smaller birth-year difference.
    These attributes are from the observed profile snapshot, not historical
    national affiliations.  No other attribute columns are read.
    """
    if not {"nation", "birth_year"}.issubset(attributes.columns):
        raise ValueError("Attributes require nation and birth_year")
    i, j = _pairs(pairs, len(attributes))
    nation = attributes["nation"].astype("string").str.strip()
    known_nation = nation.notna() & ~nation.str.casefold().isin(MISSING_NATIONS)
    codes, _ = pd.factorize(nation.where(known_nation), sort=True)
    same = (codes[i] >= 0) & (codes[j] >= 0) & (codes[i] == codes[j])
    years = pd.to_numeric(attributes["birth_year"], errors="coerce").to_numpy(dtype=float, na_value=np.nan)
    invalid = attributes["birth_year"].notna().to_numpy() & ~np.isfinite(years)
    known_year = np.isfinite(years)
    if invalid.any() or np.any(known_year & ((years % 1 != 0) | (years < 1) | (years > 9999))):
        raise ValueError("Birth years must be missing or integral calendar years")
    max_gap = int(years[known_year].max() - years[known_year].min()) if known_year.any() else 0
    missing_gap = max_gap + 1
    gap = np.full(len(i), missing_gap, dtype=np.int32)
    both_known = known_year[i] & known_year[j]
    gap[both_known] = np.abs(years[i[both_known]] - years[j[both_known]]).astype(np.int32)
    return {
        "same_nation": same.astype(np.uint8),
        "birth_year": -gap,
        "nation_birth_year": same.astype(np.int32) * (missing_gap + 1) - gap,
    }


def _score_vector(values, n=None):
    values = np.asarray(values)
    if (values.ndim != 1 or not np.issubdtype(values.dtype, np.number)
            or not np.isfinite(values).all() or (n is not None and len(values) != n)):
        raise ValueError("Scores must be equal-length finite numeric vectors")
    # Avoid unsigned negation and preserve exact integer scores in this graph.
    return values.astype(np.float64, copy=False)


def rank_candidates(scores, seed=42):
    """Sort all candidates by decreasing score, with a seeded random tie order.

    A random permutation supplies unique priorities.  The same seed and
    candidate order therefore resolve ties identically for every method.
    """
    values = _score_vector(scores)
    priorities = np.random.default_rng(seed).permutation(len(values))
    return np.lexsort((priorities, -values))


def _evaluation_input(scores, labels):
    observed = np.asarray(labels)
    if observed.ndim != 1 or not np.isin(observed, [0, 1]).all():
        raise ValueError("labels must be a one-dimensional binary vector")
    observed = observed.astype(bool)
    n = len(observed)
    k = int(observed.sum())
    if not n or not k:
        raise ValueError("Evaluation requires candidates and at least one new test edge")
    if not scores:
        raise ValueError("At least one scoring method is required")
    for values in scores.values():
        _score_vector(values, n)
    return observed, n, k


def _result_row(method, labels, n, k, seed, positives, cutoff, strict, boundary):
    boundary_size = len(boundary)
    selected = k - int(strict.sum())
    boundary_positives = int(labels[boundary].sum())
    strict_positives = int(labels[strict].sum())
    precision = positives / k
    baseline = k / n
    return {
        "method": method, "n_candidates": n, "k": k,
        "true_positives": int(positives), "precision_at_k": precision,
        "random_precision": baseline, "lift": precision / baseline,
        "seed": int(seed), "cutoff_score": float(cutoff),
        "cutoff_tie_size": boundary_size,
        "cutoff_tie_selected": selected,
        "cutoff_tie_positives": boundary_positives,
        "expected_precision_random_ties": (
            strict_positives + selected * boundary_positives / boundary_size
        ) / k,
    }


def evaluate_scores(scores, labels, seed=42):
    """Fully rank every method and evaluate the top K = number of new edges.

    All methods use the identical candidate set, labels and tie priorities.
    Random precision is K/N, so the improvement factor is Precision@K/(K/N).
    Boundary-tie counts quantify how much of the top-K result is randomised.
    """
    labels, n, k = _evaluation_input(scores, labels)
    priorities = np.random.default_rng(seed).permutation(n)
    rows = []
    for method, raw in scores.items():
        values = _score_vector(raw, n)
        ranking = np.lexsort((priorities, -values))
        positives = int(labels[ranking[:k]].sum())
        cutoff = values[ranking[k - 1]]
        strict = values > cutoff
        boundary = np.flatnonzero(values == cutoff)
        rows.append(_result_row(method, labels, n, k, seed, positives, cutoff, strict, boundary))
        del ranking
    return pd.DataFrame(rows)


def tie_sensitivity(scores, labels, seeds=(0, 1, 2, 3, 4)):
    """Repeat top-K evaluation with different random tie seeds, exactly.

    Only the cutoff tie can change membership in the first K.  After finding
    each cutoff with partition, select its needed random priorities.  This is
    exactly the same top-K set as ``evaluate_scores``, without repeatedly
    sorting scores whose relative order does not change across seeds.
    """
    labels, n, k = _evaluation_input(scores, labels)
    profiles = []
    for method, raw in scores.items():
        values = _score_vector(raw, n)
        cutoff = np.partition(values, n - k)[n - k]
        strict = values > cutoff
        boundary = np.flatnonzero(values == cutoff)
        profiles.append((method, cutoff, strict, boundary, int(labels[strict].sum()), k - int(strict.sum())))
    rows = []
    for seed in seeds:
        priorities = np.random.default_rng(seed).permutation(n)
        for method, cutoff, strict, boundary, strict_hits, take in profiles:
            if take == len(boundary):
                chosen = boundary
            else:
                chosen = boundary[np.argpartition(priorities[boundary], take - 1)[:take]]
            positives = strict_hits + int(labels[chosen].sum())
            rows.append(_result_row(method, labels, n, k, seed, positives, cutoff, strict, boundary))
    return pd.DataFrame(rows)
