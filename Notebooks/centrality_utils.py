"""Exact unweighted centralities, validated caches and monadic permutation tests."""

from collections import deque
import hashlib
import json
import math
from numbers import Integral, Real
import os
from pathlib import Path
import tempfile

import networkx as nx
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import scipy
from scipy.sparse.csgraph import shortest_path
from scipy.stats import rankdata


SCHEMA_VERSION = 1
CACHE_METADATA_KEY = b"centrality_metadata"


def _node_id(node):
    """Use typed identifiers so, for example, integer 1 is not string '1'."""
    if isinstance(node, str):
        value = ["str", node]
    elif isinstance(node, bool):
        value = ["bool", node]
    elif isinstance(node, Integral):
        value = ["int", str(int(node))]
    elif isinstance(node, Real) and math.isfinite(node):
        value = ["float", float(node).hex()]
    elif isinstance(node, tuple):
        value = ["tuple", [_node_id(item) for item in node]]
    else:
        raise TypeError(f"Unsupported node identifier: {node!r}")
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _node_hash(graph):
    identifiers = sorted(_node_id(node) for node in graph)
    encoded = json.dumps(identifiers, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load_work_graph(path, threshold=2):
    """Read and hash one GEXF stream; retain all nodes and edges above threshold.

    Source weights must be finite positive integer interaction counts. The
    resulting graph preserves node and edge attributes, but no full graph copy
    is written to disk. Centrality calculations later ignore these weights.
    """
    if isinstance(threshold, bool) or not isinstance(threshold, Integral) or threshold < 1:
        raise ValueError("threshold must be a positive integer")
    digest = hashlib.sha256()

    class HashingReader:
        def __init__(self, stream):
            self.stream = stream

        def read(self, size=-1):
            chunk = self.stream.read(size)
            digest.update(chunk)
            return chunk

    with Path(path).open("rb") as stream:
        reader = HashingReader(stream)
        source = nx.read_gexf(reader)
        while reader.read(1024 * 1024):
            pass
    if source.is_directed() or source.is_multigraph():
        raise ValueError("The source must be a simple undirected graph")
    work = nx.Graph()
    work.graph.update(source.graph)
    work.add_nodes_from(source.nodes(data=True))
    for u, v, attributes in source.edges(data=True):
        weight = attributes.get("weight")
        if u == v:
            raise ValueError("Self-loops are not allowed")
        if (isinstance(weight, bool) or not isinstance(weight, Real)
                or not math.isfinite(weight) or weight <= 0 or int(weight) != weight):
            raise ValueError(f"Edge {(u, v)!r} needs a finite positive integer weight")
        if weight >= threshold:
            work.add_edge(u, v, **attributes)
    del source
    return work, digest.hexdigest()


def graph_metadata(graph, source_sha256, threshold=2, population="giant_component"):
    """Fingerprint a source-derived graph and its chosen node population."""
    return {
        "schema_version": SCHEMA_VERSION,
        "source_sha256": str(source_sha256),
        "threshold": int(threshold),
        "population": str(population),
        "node_sha256": _node_hash(graph),
        "n_nodes": graph.number_of_nodes(),
        "n_edges": graph.number_of_edges(),
    }


def _cache_metadata(graph, metric, metadata):
    if metric not in {"harmonic", "betweenness"}:
        raise ValueError("metric must be 'harmonic' or 'betweenness'")
    if graph.is_directed() or graph.is_multigraph() or nx.number_of_selfloops(graph):
        raise ValueError("Centrality requires a simple undirected graph without loops")
    actual = graph_metadata(graph, metadata["source_sha256"], metadata["threshold"],
                            metadata.get("population", "giant_component"))
    if any(metadata.get(key) != value for key, value in actual.items()):
        raise ValueError("metadata does not describe the supplied graph")
    return {
        "cache_schema_version": SCHEMA_VERSION,
        "graph": metadata,
        "metric": metric,
        "method": ("scipy.sparse.csgraph.shortest_path:exact,unweighted,undirected"
                   if metric == "harmonic" else
                   "networkx.betweenness_centrality:k=None,weight=None,endpoints=False"),
        "normalization": ("sum_inverse_distance/(n-1);unreachable=0"
                          if metric == "harmonic" else "normalized=True;undirected"),
        "versions": {"networkx": nx.__version__, "numpy": np.__version__,
                     "pandas": pd.__version__, "scipy": scipy.__version__,
                     "pyarrow": pa.__version__},
    }


def _read_cache(path, expected, graph, metric):
    table = pq.read_table(path)
    stored = (table.schema.metadata or {}).get(CACHE_METADATA_KEY)
    if stored is None or json.loads(stored) != expected:
        raise ValueError("Cache metadata differs from graph, source, method or versions")
    if table.column_names != ["node_id", "value"]:
        raise ValueError("Cache columns must be node_id and value")
    cached = table.to_pandas()
    identifiers = [_node_id(node) for node in graph]
    if (cached["node_id"].isna().any() or cached["node_id"].duplicated().any()
            or len(cached) != len(graph) or set(cached["node_id"]) != set(identifiers)):
        raise ValueError("Cache must contain every exact node ID once")
    if not pd.api.types.is_numeric_dtype(cached["value"]):
        raise ValueError("Cache values must be numeric")
    values = cached["value"].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any() or (values > 1).any():
        raise ValueError("Cache values must be finite and in [0, 1]")
    ordered = cached.set_index("node_id")["value"].reindex(identifiers)
    return pd.Series(ordered.to_numpy(dtype=float), index=list(graph), name=metric)


def _harmonic(graph, batch_size):
    nodes = list(graph)
    n = len(nodes)
    result = np.zeros(n, dtype=float)
    if n > 1:
        adjacency = nx.to_scipy_sparse_array(graph, nodelist=nodes, weight=None,
                                             dtype=float, format="csr")
        # SciPy's graph routines also accept platforms using 32-bit CSR indices.
        if adjacency.indices.size <= np.iinfo(np.int32).max:
            adjacency.indices = adjacency.indices.astype(np.int32, copy=False)
            adjacency.indptr = adjacency.indptr.astype(np.int32, copy=False)
        for start in range(0, n, batch_size):
            distances = shortest_path(adjacency, directed=False, unweighted=True,
                                      indices=np.arange(start, min(start + batch_size, n)),
                                      method="D")
            positive = np.isfinite(distances) & (distances > 0)
            np.divide(1.0, distances, out=distances, where=positive)
            distances[~positive] = 0.0
            result[start:start + len(distances)] = distances.sum(axis=1) / (n - 1)
    return pd.Series(result, index=nodes, name="harmonic")


def expensive_centrality(graph, metric, cache_path, metadata, recompute=False, batch_size=64):
    """Load a validated exact cache, or compute only after explicit opt-in.

    ``recompute=True`` always computes again, including when a valid cache exists.
    The status dictionary has ``status`` and ``reason``. Without opt-in a missing
    or invalid cache returns ``None``; no approximate result is substituted.
    """
    if isinstance(batch_size, bool) or not isinstance(batch_size, Integral) or batch_size < 1:
        raise ValueError("batch_size must be a positive integer")
    expected = _cache_metadata(graph, metric, metadata)
    path = Path(cache_path)
    if not recompute:
        if not path.exists():
            return None, {"status": "missing", "reason":
                          "Exact cache missing; set recompute=True to opt in to computation."}
        try:
            values = _read_cache(path, expected, graph, metric)
            return values, {"status": "loaded", "reason": "Validated exact cache loaded."}
        except Exception as error:
            return None, {"status": "invalid", "reason":
                          f"Cache rejected: {error}. Set recompute=True to opt in to recomputation."}
    if metric == "harmonic":
        values = _harmonic(graph, batch_size)
    else:
        values = pd.Series(nx.betweenness_centrality(graph, k=None, normalized=True,
                                                    weight=None, endpoints=False),
                           dtype=float, name=metric)
    array = values.to_numpy(dtype=float)
    if not np.isfinite(array).all() or (array < 0).any() or (array > 1).any():
        raise ValueError("Computed centrality values must be finite and in [0, 1]")
    table = pa.table({"node_id": [_node_id(node) for node in values.index], "value": array})
    table = table.replace_schema_metadata({CACHE_METADATA_KEY:
                                          json.dumps(expected, sort_keys=True).encode("utf-8")})
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    try:
        pq.write_table(table, temporary)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return values, {"status": "computed", "reason":
                    "Exact centrality computed after opt-in; cache atomically replaced."}


def load_analysis_result(cache_path, expected_graph_metadata, community_sha256=None,
                         required_columns=()):
    """Reuse a saved result only when its graph and requested inputs still match.

    This checks the embedded analysis metadata and the table's structure, without
    calculating any centrality. Callers must additionally validate the values and
    population appropriate to their result (actors and groups use different rows).
    ``community_sha256=None`` leaves the optional community fingerprint unchecked.
    """
    path = Path(cache_path)
    if not path.exists():
        return None, {"status": "missing", "reason": "Saved analysis result missing."}, None
    try:
        table = pq.read_table(path)
        stored = (table.schema.metadata or {}).get(b"athletes_network_analysis")
        if stored is None:
            raise ValueError("Embedded analysis metadata missing")
        metadata = json.loads(stored)
        if not isinstance(metadata, dict) or metadata.get("graph") != expected_graph_metadata:
            raise ValueError("Graph fingerprint differs from current source or population")
        if community_sha256 is not None and metadata.get("community_sha256") != community_sha256:
            raise ValueError("Community fingerprint differs from current chapter 5 export")
        frame = table.to_pandas()
        if not frame.columns.is_unique:
            raise ValueError("Result columns must be unique")
        if (isinstance(frame.index, pd.MultiIndex) or not frame.index.is_unique
                or frame.index.isna().any()):
            raise ValueError("Result needs a unique, nonmissing one-dimensional index")
        missing = set(required_columns).difference(frame.columns)
        if missing:
            raise ValueError(f"Required result columns missing: {sorted(missing)}")
    except Exception as error:
        return None, {"status": "invalid", "reason": f"Saved analysis result rejected: {error}."}, None
    return frame, {"status": "loaded", "reason": "Validated saved analysis result loaded."}, metadata


def group_centrality(graph, members):
    """Compute normalized group degree and harmonic group closeness by one BFS.

    Every outside node belongs in both denominators. An unreachable outside
    node contributes zero inverse distance. Distances and edges are unweighted.
    """
    members = set(members)
    if not members or not members.issubset(graph) or len(members) == len(graph):
        raise ValueError("members must be a nonempty proper subset of graph nodes")
    if graph.is_directed() or graph.is_multigraph():
        raise ValueError("Group centrality requires a simple undirected graph")
    distance = dict.fromkeys(members, 0)
    queue = deque(members)
    while queue:
        node = queue.popleft()
        for neighbor in graph[node]:
            if neighbor not in distance:
                distance[neighbor] = distance[node] + 1
                queue.append(neighbor)
    outside = len(graph) - len(members)
    direct = sum(value == 1 for value in distance.values())
    reached = len(distance) - len(members)
    # fsum avoids order-dependent rounding from the set of starting members.
    inverse_sum = math.fsum(1.0 / value for value in distance.values() if value > 0)
    return {"size": len(members), "outside": outside, "reached_direct": direct,
            "reached_any": reached, "group_degree": direct / outside,
            "group_closeness": inverse_sum / outside}


def monadic_permutation_tests(frame, score_column, metric_columns, n_permutations=9999,
                              seed=42, alpha=0.05):
    """One-sided positive Spearman tests on a common complete-case population.

    Permute score ranks and keep metric ranks fixed. The effect size is rho;
    Monte Carlo p=(exceedances+1)/(B+1). Holm adjusts all defined tests in this
    call. Constants and fewer than three complete rows remain explicitly untested.
    """
    metrics = list(metric_columns)
    if not metrics or len(set(metrics)) != len(metrics) or score_column in metrics:
        raise ValueError("metric_columns must be nonempty, distinct and exclude score_column")
    if (isinstance(n_permutations, bool) or not isinstance(n_permutations, Integral)
            or n_permutations < 1):
        raise ValueError("n_permutations must be a positive integer")
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1")
    numeric = frame[[score_column, *metrics]].apply(pd.to_numeric, errors="coerce")
    numeric = numeric.replace([np.inf, -np.inf], np.nan).dropna()
    n = len(numeric)
    result = pd.DataFrame(index=pd.Index(metrics, name="metric"))
    result["rho"] = np.nan
    result["n"] = n
    result["B"] = n_permutations
    result["seed"] = seed
    result["p"] = np.nan
    result["p_holm"] = np.nan
    result["reject_holm"] = False
    result["status"] = "insufficient_data"
    if n < 3:
        return result
    scores = rankdata(numeric[score_column].to_numpy(dtype=float), method="average")
    scores -= scores.mean()
    score_norm = np.linalg.norm(scores)
    if score_norm == 0:
        result["status"] = "constant_score"
        return result
    ranks = np.column_stack([rankdata(numeric[column].to_numpy(dtype=float), method="average")
                             for column in metrics])
    ranks -= ranks.mean(axis=0)
    norms = np.linalg.norm(ranks, axis=0)
    valid = norms > 0
    result["status"] = np.where(valid, "ok", "constant_metric")
    if not valid.any():
        return result
    unit_metrics = ranks[:, valid] / norms[valid]
    observed = np.clip(scores @ unit_metrics / score_norm, -1.0, 1.0)
    exceedances = np.zeros(valid.sum(), dtype=np.int64)
    rng = np.random.default_rng(seed)
    for _ in range(n_permutations):
        permuted = rng.permutation(scores) @ unit_metrics / score_norm
        exceedances += permuted >= observed - 1e-12
    p_values = (exceedances + 1) / (n_permutations + 1)
    order = np.argsort(p_values)
    adjusted = np.empty_like(p_values)
    adjusted[order] = np.minimum(1.0, np.maximum.accumulate(
        p_values[order] * np.arange(len(p_values), 0, -1)))
    result.loc[valid, "rho"] = observed
    result.loc[valid, "p"] = p_values
    result.loc[valid, "p_holm"] = adjusted
    result.loc[valid, "reject_holm"] = adjusted <= alpha
    return result
