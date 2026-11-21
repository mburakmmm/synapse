"""SYNAPSE paired statistical analysis, permutation tests, and sensitivity summaries."""

from synapse_analysis.paired import AnalysisError, run_paired_analysis, sha256_file
from synapse_analysis.stats import (
    bh_fdr_adjust,
    local_sensitivity_summary,
    paired_permutation_test,
)
from synapse_analysis.windows import compute_windowed_response_metrics

__all__ = [
    "AnalysisError",
    "bh_fdr_adjust",
    "compute_windowed_response_metrics",
    "local_sensitivity_summary",
    "paired_permutation_test",
    "run_paired_analysis",
    "sha256_file",
]
