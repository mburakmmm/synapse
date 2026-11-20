"""Export evidence-linked figures, underlying source tables, and checksum manifests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from synapse_analysis import sha256_file

# Okabe-Ito colorblind-safe palette
_COLOR_BASELINE = "#0072B2"
_COLOR_TREATMENT = "#D55E00"
_COLOR_PAIR_LINE = "#666666"


def export_evidence_bundle(analysis_dir: Path, out_dir: Path) -> Path:
    """Export SVG/PNG figure, exact source tables, bundle manifest, and factual README."""
    manifest_path = analysis_dir / "analysis_manifest.json"
    summary_pq = analysis_dir / "analysis_summary.parquet"
    paired_pq = analysis_dir / "paired_differences.parquet"
    for req in (manifest_path, summary_pq, paired_pq):
        if not req.is_file():
            raise FileNotFoundError(f"Missing required analysis artifact: {req}")

    analysis_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary_df = pl.read_parquet(summary_pq)
    paired_df = pl.read_parquet(paired_pq)

    prov = analysis_manifest["provenance"]
    is_synth = bool(prov["is_synthetic_fixture"])
    b_cond = str(analysis_manifest["baseline_condition"])
    t_cond = str(analysis_manifest["treatment_condition"])
    target_id = str(analysis_manifest["target_neuron_id"])
    paired_metrics = analysis_manifest["paired_metrics"]
    n_pairs = int(paired_metrics["n_pairs"])

    b_row = summary_df.filter(pl.col("condition_id") == b_cond).to_dicts()[0]
    t_row = summary_df.filter(pl.col("condition_id") == t_cond).to_dicts()[0]

    # Prepare exact figure source data table (matches plotted values 1-to-1)
    source_rows: list[dict[str, Any]] = []
    for row in paired_df.iter_rows(named=True):
        rep_id = int(row["replicate_id"])
        source_rows.append(
            {
                "condition_id": b_cond,
                "replicate_id": rep_id,
                "target_neuron_id": target_id,
                "firing_rate_hz": float(row["baseline_rate_hz"]),
                "condition_mean_hz": float(b_row["mean_hz"]),
                "condition_sd_hz": float(b_row["sd_hz"]),
                "n_seed_replicates": int(b_row["n_seed_replicates"]),
                "is_synthetic_fixture": is_synth,
            }
        )
        source_rows.append(
            {
                "condition_id": t_cond,
                "replicate_id": rep_id,
                "target_neuron_id": target_id,
                "firing_rate_hz": float(row["treatment_rate_hz"]),
                "condition_mean_hz": float(t_row["mean_hz"]),
                "condition_sd_hz": float(t_row["sd_hz"]),
                "n_seed_replicates": int(t_row["n_seed_replicates"]),
                "is_synthetic_fixture": is_synth,
            }
        )

    figures_dir = out_dir / "figures"
    tables_dir = out_dir / "tables"
    prov_dir = out_dir / "provenance"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)
    prov_dir.mkdir(parents=True, exist_ok=True)

    source_df = pl.DataFrame(source_rows)
    table_csv = tables_dir / "figure1_source_data.csv"
    table_pq = tables_dir / "figure1_source_data.parquet"
    source_df.write_csv(table_csv)
    source_df.write_parquet(table_pq)

    # Render figure strictly via Matplotlib OO API (no pyplot global state)
    fig = Figure(figsize=(7.2, 4.8), dpi=200)
    FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)

    x_pos = np.array([0.0, 1.0])
    means = [float(b_row["mean_hz"]), float(t_row["mean_hz"])]
    sds = [float(b_row["sd_hz"]), float(t_row["sd_hz"])]

    ax.bar(
        x_pos,
        means,
        width=0.45,
        color=[_COLOR_BASELINE, _COLOR_TREATMENT],
        alpha=0.25,
        edgecolor=[_COLOR_BASELINE, _COLOR_TREATMENT],
        linewidth=1.5,
        zorder=1,
    )
    ax.errorbar(
        x_pos,
        means,
        yerr=sds,
        fmt="o",
        color="#111111",
        ecolor="#111111",
        elinewidth=1.5,
        capsize=5,
        zorder=4,
        label="Condition mean ± 1 SD across seeds",
    )

    for row in paired_df.iter_rows(named=True):
        y_b = float(row["baseline_rate_hz"])
        y_t = float(row["treatment_rate_hz"])
        ax.plot(
            [0.0, 1.0],
            [y_b, y_t],
            color=_COLOR_PAIR_LINE,
            alpha=0.55,
            linewidth=1.0,
            marker="o",
            markersize=4,
            zorder=3,
        )

    ax.set_xticks(x_pos)
    ax.set_xticklabels([b_cond, t_cond], fontsize=10)
    ax.set_ylabel("Modeled firing rate (Hz)", fontsize=10)
    y_max = max(
        max(float(r["baseline_rate_hz"]), float(r["treatment_rate_hz"]))
        for r in paired_df.iter_rows(named=True)
    )
    y_top = max(10.0, y_max * 1.18, max(m + s for m, s in zip(means, sds, strict=True)) * 1.18)
    ax.set_ylim(0.0, y_top)  # Start y-axis at 0 Hz to prevent misleading truncation
    ax.grid(axis="y", linestyle="--", alpha=0.35, zorder=0)

    title_prefix = "SYNTHETIC ENGINEERING FIXTURE — NOT BIOLOGICAL DATA\n" if is_synth else ""
    ax.set_title(
        f"{title_prefix}Target Neuron {target_id}: {b_cond} vs {t_cond}\n"
        f"(n = {n_pairs} paired simulation seeds; Δ = "
        f"{paired_metrics['mean_difference_hz']:+.2f} Hz, "
        f"95% seed bootstrap [{paired_metrics['bootstrap_ci95_low_hz']:+.2f}, "
        f"{paired_metrics['bootstrap_ci95_high_hz']:+.2f}] Hz)",
        fontsize=10,
        pad=10,
    )
    ax.legend(loc="upper left", fontsize=8, frameon=True)

    footer = (
        f"Dataset: {prov['dataset_id']} ({prov['dataset_release']}) | "
        f"Model: {prov['model_id']} v{prov['model_revision']} | "
        f"Protocol SHA256: {prov['protocol_sha256'][:12]} | "
        "Error bars: ±1 SD across simulation seeds (model-conditional)"
    )
    fig.text(0.5, 0.015, footer, ha="center", va="bottom", fontsize=7.5, color="#444444")
    fig.tight_layout(rect=(0.0, 0.05, 1.0, 1.0))

    svg_path = figures_dir / "firing_rate_comparison.svg"
    png_path = figures_dir / "firing_rate_comparison.png"
    fig.savefig(svg_path, format="svg")
    fig.savefig(png_path, format="png", dpi=200)

    # Generate strictly factual REPRODUCIBILITY.md
    failed_count = int(analysis_manifest["failed_run_count"])
    failed_lines = (
        "- None (0 failed or incomplete runs observed in `runs_dir`)."
        if failed_count == 0
        else "\n".join(
            f"- `{fr['run_id']}`: status=`{fr['status']}`, reason=`{fr['failure_reason']}`"
            for fr in analysis_manifest["failed_runs"]
        )
    )
    banner = (
        "> **SYNTHETIC ENGINEERING FIXTURE:** This bundle was generated from a synthetic "
        "microcircuit fixture (`is_synthetic_fixture=true`). It validates software pipelines only "
        "and carries zero biological or clinical evidence.\n\n"
        if is_synth
        else "> **RESEARCH USE ONLY (RUO):** Conditional on specified connectome and model.\n\n"
    )
    repro_md = out_dir / "REPRODUCIBILITY.md"
    repro_md.write_text(
        f"# SYNAPSE Reproducibility Bundle\n\n"
        f"{banner}"
        f"- **Generated (UTC):** `{datetime.now(UTC).isoformat()}`\n"
        f"- **Analysis Intent:** `{prov['analysis_intent']}`\n"
        f"- **Protocol:** `{prov['protocol_id']}` rev `{prov['protocol_revision']}` "
        f"(SHA-256 `{prov['protocol_sha256']}`)\n"
        f"- **Dataset:** `{prov['dataset_id']}` `{prov['dataset_release']}` "
        f"(Manifest SHA-256 `{prov['dataset_manifest_sha256']}`)\n"
        f"- **Model:** `{prov['model_id']}` rev `{prov['model_revision']}` "
        f"(Params SHA-256 `{prov['parameter_manifest_sha256']}`)\n"
        f"- **Target Neuron ID:** `{target_id}`\n"
        f"- **Paired Seed Replicates:** `{n_pairs}`\n"
        f"- **Mean Paired Difference (`{t_cond} - {b_cond}`):** "
        f"`{paired_metrics['mean_difference_hz']:+.4f}` Hz "
        f"(SD `{paired_metrics['sd_difference_hz']:.4f}` Hz; "
        f"uncertainty: `{paired_metrics['uncertainty_interpretation']}`)\n\n"
        f"## Included Succeeded Runs ({len(analysis_manifest['included_run_ids'])})\n\n"
        + "\n".join(
            f"- `{rid}` "
            f"(manifest SHA-256 `{analysis_manifest['included_run_manifest_sha256s'][rid]}`)"
            for rid in analysis_manifest["included_run_ids"]
        )
        + f"\n\n## Failed / Incomplete Run Accounting ({failed_count})\n\n"
        + failed_lines
        + "\n",
        encoding="utf-8",
    )

    exported_files = [svg_path, png_path, table_csv, table_pq, repro_md]
    bundle_manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "is_synthetic_fixture": is_synth,
        "upstream_provenance": prov,
        "analysis_manifest_sha256": sha256_file(manifest_path),
        "included_run_manifest_sha256s": analysis_manifest["included_run_manifest_sha256s"],
        "failed_run_count": failed_count,
        "files": [
            {
                "path": p.relative_to(out_dir).as_posix(),
                "bytes": p.stat().st_size,
                "sha256": sha256_file(p),
            }
            for p in exported_files
        ],
    }
    bundle_manifest_path = prov_dir / "bundle_manifest.json"
    bundle_manifest_path.write_text(
        json.dumps(bundle_manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return bundle_manifest_path
