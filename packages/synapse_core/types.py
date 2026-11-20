"""Core graph representations, namespace keys, and signed weight mapping."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy.sparse import csr_matrix

DEFAULT_SIGN_MAP: dict[str, float] = {
    "ACH": 1.0,
    "GABA": -1.0,
    "GLUT": -1.0,
    "EXCITATORY_SIGN": 1.0,
    "INHIBITORY_SIGN": -1.0,
}


@dataclass(frozen=True, slots=True)
class NeuronNamespaceKey:
    """Lossless specimen-scoped neuron identifier preventing cross-specimen ID pooling."""

    dataset_id: str
    release: str
    specimen_id: str
    source_neuron_id: str

    def __post_init__(self) -> None:
        for field_name in ("dataset_id", "release", "specimen_id", "source_neuron_id"):
            val = getattr(self, field_name)
            if not isinstance(val, str) or not val:
                raise ValueError(f"{field_name} must be a non-empty string, got {val!r}")
            if "::" in val:
                raise ValueError(f"{field_name} must not contain '::', got {val!r}")

    def to_key(self) -> str:
        """Serialize composite key losslessly."""
        return f"{self.dataset_id}::{self.release}::{self.specimen_id}::{self.source_neuron_id}"

    @classmethod
    def from_key(cls, composite_key: str) -> NeuronNamespaceKey:
        """Parse a composite key back into its four namespace components."""
        parts = composite_key.split("::")
        if len(parts) != 4:
            raise ValueError(f"Expected 4 '::'-delimited components, got {composite_key!r}")
        return cls(
            dataset_id=parts[0],
            release=parts[1],
            specimen_id=parts[2],
            source_neuron_id=parts[3],
        )


@dataclass(frozen=True, slots=True)
class DirectedEdge:
    """Single directed structural connection from presynaptic to postsynaptic neuron."""

    pre_source_id: str
    post_source_id: str
    synapse_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.pre_source_id, str) or not self.pre_source_id:
            raise ValueError("pre_source_id must be a non-empty string")
        if not isinstance(self.post_source_id, str) or not self.post_source_id:
            raise ValueError("post_source_id must be a non-empty string")
        if isinstance(self.synapse_count, bool) or not isinstance(self.synapse_count, int):
            raise ValueError(f"synapse_count must be an integer, got {self.synapse_count!r}")
        if self.synapse_count <= 0:
            raise ValueError(f"synapse_count must be positive, got {self.synapse_count}")


class DirectedConnectomeGraph:
    """Immutable directed connectome graph with explicit postsynaptic-row, presynaptic-col matrix.

    Sparse orientation convention (AGENTS.md section 6.2):
    - ``adjacency_counts[post_idx, pre_idx]`` stores the positive synapse count for edge
      ``pre -> post``.
    - Therefore ``W @ pre_activity`` computes postsynaptic input vector indexed by ``post_idx``.
    """

    def __init__(
        self,
        *,
        dataset_id: str,
        release: str,
        specimen_id: str,
        is_synthetic_fixture: bool,
        neuron_ids: tuple[str, ...],
        neurotransmitters: tuple[str | None, ...],
        adjacency_counts: csr_matrix,
        aggregation_policy: str = "error",
    ) -> None:
        if not dataset_id or not release or not specimen_id:
            raise ValueError("dataset_id, release, and specimen_id must be non-empty")
        if len(neuron_ids) == 0:
            raise ValueError("Graph must contain at least one neuron")
        if len(set(neuron_ids)) != len(neuron_ids):
            raise ValueError("Duplicate neuron_ids are forbidden")
        if len(neurotransmitters) != len(neuron_ids):
            raise ValueError("neurotransmitters length must match neuron_ids length")
        n = len(neuron_ids)
        if adjacency_counts.shape != (n, n):
            raise ValueError(
                f"adjacency_counts shape {adjacency_counts.shape} does not match ({n}, {n})"
            )

        self._dataset_id = dataset_id
        self._release = release
        self._specimen_id = specimen_id
        self._is_synthetic_fixture = bool(is_synthetic_fixture)
        self._neuron_ids = neuron_ids
        self._id_to_index: dict[str, int] = {nid: idx for idx, nid in enumerate(neuron_ids)}
        self._neurotransmitters = tuple(
            nt.strip().upper() if isinstance(nt, str) and nt.strip() else None
            for nt in neurotransmitters
        )
        mat = adjacency_counts.tocsr(copy=True)
        mat.sum_duplicates()
        mat.sort_indices()
        if mat.nnz > 0:
            if not np.all(np.isfinite(mat.data)):
                raise ValueError("adjacency_counts contains non-finite values")
            if np.any(mat.data <= 0):
                raise ValueError("adjacency_counts must contain strictly positive weights")
        self._adjacency_counts = mat
        self._aggregation_policy = aggregation_policy

    @classmethod
    def from_edges(
        cls,
        *,
        dataset_id: str,
        release: str,
        specimen_id: str,
        is_synthetic_fixture: bool,
        neuron_ids: Iterable[str],
        edges: Iterable[DirectedEdge],
        neurotransmitters: Mapping[str, str | None] | None = None,
        aggregation_policy: Literal["error", "sum"] = "error",
    ) -> DirectedConnectomeGraph:
        """Build an immutable DirectedConnectomeGraph from validated neuron IDs and directed edges.

        Preserves self-loops and reciprocal edges. Rejects duplicate ``(pre, post)`` edges when
        ``aggregation_policy == 'error'``; sums them when ``aggregation_policy == 'sum'``.
        """
        ordered_ids = tuple(neuron_ids)
        if not ordered_ids:
            raise ValueError("neuron_ids must not be empty")
        if len(set(ordered_ids)) != len(ordered_ids):
            raise ValueError("Duplicate neuron IDs detected")
        for nid in ordered_ids:
            if not isinstance(nid, str) or not nid:
                raise ValueError(f"Invalid neuron ID {nid!r}; expected non-empty string")
        id_to_idx = {nid: i for i, nid in enumerate(ordered_ids)}

        nt_map = dict(neurotransmitters or {})
        nt_tuple: tuple[str | None, ...] = tuple(nt_map.get(nid) for nid in ordered_ids)

        rows: list[int] = []
        cols: list[int] = []
        vals: list[int] = []
        seen_pairs: set[tuple[int, int]] = set()

        for edge in edges:
            if edge.pre_source_id not in id_to_idx:
                raise ValueError(f"Unknown presynaptic neuron ID: {edge.pre_source_id!r}")
            if edge.post_source_id not in id_to_idx:
                raise ValueError(f"Unknown postsynaptic neuron ID: {edge.post_source_id!r}")
            pre_idx = id_to_idx[edge.pre_source_id]
            post_idx = id_to_idx[edge.post_source_id]
            pair = (pre_idx, post_idx)
            if pair in seen_pairs and aggregation_policy == "error":
                raise ValueError(
                    f"Duplicate directed edge ({edge.pre_source_id} -> {edge.post_source_id}) "
                    "under aggregation_policy='error'"
                )
            seen_pairs.add(pair)
            # Explicit orientation: row = post (target), col = pre (source)
            rows.append(post_idx)
            cols.append(pre_idx)
            vals.append(edge.synapse_count)

        n = len(ordered_ids)
        if vals:
            mat = csr_matrix(
                (np.asarray(vals, dtype=np.int64), (rows, cols)),
                shape=(n, n),
                dtype=np.int64,
            )
            mat.sum_duplicates()
        else:
            mat = csr_matrix((n, n), dtype=np.int64)

        return cls(
            dataset_id=dataset_id,
            release=release,
            specimen_id=specimen_id,
            is_synthetic_fixture=is_synthetic_fixture,
            neuron_ids=ordered_ids,
            neurotransmitters=nt_tuple,
            adjacency_counts=mat,
            aggregation_policy=aggregation_policy,
        )

    @classmethod
    def from_arrays(
        cls,
        *,
        dataset_id: str,
        release: str,
        specimen_id: str,
        is_synthetic_fixture: bool,
        neuron_ids: Sequence[str],
        pre_indices: np.ndarray,
        post_indices: np.ndarray,
        counts: np.ndarray,
        neurotransmitters: Sequence[str | None] | None = None,
        aggregation_policy: Literal["error", "sum"] = "error",
    ) -> DirectedConnectomeGraph:
        """Build an immutable DirectedConnectomeGraph directly from vectorized index arrays."""
        ordered_ids = tuple(neuron_ids)
        n = len(ordered_ids)
        if n == 0:
            raise ValueError("neuron_ids must not be empty")
        if len(set(ordered_ids)) != n:
            raise ValueError("Duplicate neuron IDs detected")
        if any(not isinstance(nid, str) or not nid for nid in ordered_ids):
            raise ValueError("All neuron_ids must be non-empty strings")

        pre = np.asarray(pre_indices, dtype=np.int64)
        post = np.asarray(post_indices, dtype=np.int64)
        raw_cnt = np.asarray(counts)
        if raw_cnt.dtype.kind not in ("i", "u"):
            raise ValueError(f"counts must have integer dtype, got {raw_cnt.dtype}")
        cnt = raw_cnt.astype(np.int64, copy=False)

        if not (pre.ndim == post.ndim == cnt.ndim == 1):
            raise ValueError("pre_indices, post_indices, and counts must be 1D arrays")
        if not (len(pre) == len(post) == len(cnt)):
            raise ValueError("pre_indices, post_indices, and counts must have identical lengths")
        if len(cnt) > 0:
            if np.any(pre < 0) or np.any(pre >= n):
                raise ValueError("pre_indices out of range [0, n_neurons)")
            if np.any(post < 0) or np.any(post >= n):
                raise ValueError("post_indices out of range [0, n_neurons)")
            if np.any(cnt <= 0):
                raise ValueError("counts must be strictly positive")

        if neurotransmitters is None:
            nt_tuple: tuple[str | None, ...] = (None,) * n
        else:
            if len(neurotransmitters) != n:
                raise ValueError("neurotransmitters length must match neuron_ids length")
            nt_tuple = tuple(neurotransmitters)

        if len(cnt) > 0:
            # Explicit orientation: row = post (target), col = pre (source)
            mat = csr_matrix((cnt, (post, pre)), shape=(n, n), dtype=np.int64)
            mat.sum_duplicates()
            if aggregation_policy == "error" and mat.nnz != len(cnt):
                raise ValueError(
                    "Duplicate directed edge detected under aggregation_policy='error'"
                )
        else:
            mat = csr_matrix((n, n), dtype=np.int64)

        return cls(
            dataset_id=dataset_id,
            release=release,
            specimen_id=specimen_id,
            is_synthetic_fixture=is_synthetic_fixture,
            neuron_ids=ordered_ids,
            neurotransmitters=nt_tuple,
            adjacency_counts=mat,
            aggregation_policy=aggregation_policy,
        )

    @property
    def dataset_id(self) -> str:
        return self._dataset_id

    @property
    def release(self) -> str:
        return self._release

    @property
    def specimen_id(self) -> str:
        return self._specimen_id

    @property
    def is_synthetic_fixture(self) -> bool:
        return self._is_synthetic_fixture

    @property
    def neuron_ids(self) -> tuple[str, ...]:
        return self._neuron_ids

    @property
    def neurotransmitters(self) -> tuple[str | None, ...]:
        return self._neurotransmitters

    @property
    def aggregation_policy(self) -> str:
        return self._aggregation_policy

    @property
    def n_neurons(self) -> int:
        return len(self._neuron_ids)

    @property
    def n_edges(self) -> int:
        return int(self._adjacency_counts.nnz)

    @property
    def total_synapses(self) -> int:
        return int(self._adjacency_counts.sum())

    def index_of(self, neuron_id: str) -> int:
        """Return dense integer index for ``neuron_id``."""
        if neuron_id not in self._id_to_index:
            raise KeyError(f"Neuron ID {neuron_id!r} not in graph")
        return self._id_to_index[neuron_id]

    def namespace_key(self, neuron_id: str) -> NeuronNamespaceKey:
        """Return specimen-scoped NeuronNamespaceKey for ``neuron_id``."""
        self.index_of(neuron_id)
        return NeuronNamespaceKey(
            dataset_id=self._dataset_id,
            release=self._release,
            specimen_id=self._specimen_id,
            source_neuron_id=neuron_id,
        )

    def adjacency_copy(self) -> csr_matrix:
        """Return a defensive copy of the CSR synapse-count matrix (row=post, col=pre)."""
        return self._adjacency_counts.tocsr(copy=True)

    def edge_arrays(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return ``(pre_indices, post_indices, counts)`` sorted deterministically."""
        coo = self._adjacency_counts.tocoo()
        # coo.row = post_idx, coo.col = pre_idx
        return (
            coo.col.astype(np.int64, copy=False),
            coo.row.astype(np.int64, copy=False),
            coo.data.astype(np.int64, copy=False),
        )

    def edge_count_between(self, pre_source_id: str, post_source_id: str) -> int:
        """Return directed synapse count for ``pre -> post`` (0 if absent)."""
        pre_idx = self.index_of(pre_source_id)
        post_idx = self.index_of(post_source_id)
        return int(self._adjacency_counts[post_idx, pre_idx])

    def signed_weight_matrix(
        self,
        w_syn_v: float,
        *,
        unknown_nt_policy: Literal["zero_effect", "error"] = "zero_effect",
        sign_map: Mapping[str, float] | None = None,
    ) -> csr_matrix:
        """Compute signed postsynaptic input weight matrix ``W[post, pre]`` in volts.

        Unknown neurotransmitters never silently default to excitatory (+1.0): they either
        raise ``ValueError`` (``unknown_nt_policy='error'``) or map to ``0.0``
        (``unknown_nt_policy='zero_effect'``).
        """
        if not math.isfinite(w_syn_v) or w_syn_v < 0.0:
            raise ValueError(f"w_syn_v must be finite and non-negative, got {w_syn_v}")
        effective_signs = dict(DEFAULT_SIGN_MAP if sign_map is None else sign_map)
        col_scales = np.zeros(self.n_neurons, dtype=np.float64)
        for idx, nt in enumerate(self._neurotransmitters):
            if nt is None or nt not in effective_signs:
                if unknown_nt_policy == "error":
                    raise ValueError(
                        f"Unknown neurotransmitter {nt!r} for neuron {self._neuron_ids[idx]!r}"
                    )
                col_scales[idx] = 0.0
            else:
                col_scales[idx] = float(effective_signs[nt]) * float(w_syn_v)

        coo = self._adjacency_counts.tocoo()
        signed_data = coo.data.astype(np.float64) * col_scales[coo.col]
        return csr_matrix((signed_data, (coo.row, coo.col)), shape=self._adjacency_counts.shape)

    def graph_sha256(self) -> str:
        """Compute canonical permutation-invariant SHA-256 over neurons, NTs, and CSR matrix."""
        n = len(self._neuron_ids)
        perm = sorted(range(n), key=self._neuron_ids.__getitem__)
        inv_perm = np.empty(n, dtype=np.int64)
        inv_perm[perm] = np.arange(n, dtype=np.int64)

        coo = self._adjacency_counts.tocoo()
        if coo.nnz > 0:
            canon_post = inv_perm[coo.row]
            canon_pre = inv_perm[coo.col]
            canon_mat = csr_matrix(
                (coo.data.astype(np.int64, copy=False), (canon_post, canon_pre)),
                shape=(n, n),
                dtype=np.int64,
            )
            canon_mat.sort_indices()
        else:
            canon_mat = csr_matrix((n, n), dtype=np.int64)

        header = {
            "dataset_id": self._dataset_id,
            "release": self._release,
            "specimen_id": self._specimen_id,
            "is_synthetic_fixture": self._is_synthetic_fixture,
            "neurons": [(self._neuron_ids[i], self._neurotransmitters[i]) for i in perm],
        }
        h = hashlib.sha256()
        h.update(json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        h.update(b"\x00")
        h.update(np.asarray(canon_mat.indptr, dtype="<i8").tobytes())
        h.update(np.asarray(canon_mat.indices, dtype="<i8").tobytes())
        h.update(np.asarray(canon_mat.data, dtype="<i8").tobytes())
        return h.hexdigest()
