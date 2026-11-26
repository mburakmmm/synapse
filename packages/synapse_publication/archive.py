"""Phase 6 open-science publication archival, bundle integrity, and citation audit (RUO)."""

from __future__ import annotations

import json
import shutil
import zipfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from synapse_analysis import sha256_file

RESTRICTED_ARCHIVE_PATTERNS: tuple[str, ...] = (
    ".env",
    ".env.",
    ".pem",
    ".key",
    ".p12",
    "spikes.parquet",
    "data/",
    "data\\",
)

_FIXED_ZIP_DATE_TIME = (2026, 1, 1, 0, 0, 0)


def _is_restricted_relative_path(rel_posix: str) -> bool:
    norm = rel_posix.replace("\\", "/").lstrip("./")
    lower = norm.lower()
    if lower.startswith("data/") or "/data/" in lower:
        return True
    name = Path(norm).name.lower()
    if name == ".env" or name.startswith(".env."):
        return True
    if name.endswith((".pem", ".key", ".p12")):
        return True
    return name == "spikes.parquet"


def _resolve_contained_path(root: Path, rel_path: str) -> Path:
    if not rel_path or rel_path.startswith(("/", "\\")) or ":" in rel_path.split("/")[0]:
        raise ValueError(f"Unsafe non-relative archive path: {rel_path!r}")
    candidate = (root / rel_path).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"Path traversal outside {root_resolved}: {rel_path!r}") from exc
    return candidate


def verify_evidence_bundle(bundle_dir: Path) -> dict[str, Any]:
    """Verify checksums, byte counts, path containment, and required artifacts of a bundle."""
    errors: list[str] = []
    manifest_path = bundle_dir / "provenance" / "bundle_manifest.json"
    if not manifest_path.is_file():
        return {
            "valid": False,
            "bundle_dir": str(bundle_dir),
            "checked_files": 0,
            "failed_run_count": -1,
            "is_synthetic_fixture": False,
            "errors": [f"Missing bundle_manifest.json at {manifest_path}"],
        }

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        errors.append("bundle_manifest.json missing non-empty 'files' list")
        files = []

    seen_paths: set[str] = set()
    checked = 0
    for entry in files:
        rel = str(entry.get("path", ""))
        expected_sha = str(entry.get("sha256", ""))
        expected_bytes = entry.get("bytes")
        seen_paths.add(rel)
        try:
            target = _resolve_contained_path(bundle_dir, rel)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not target.is_file():
            errors.append(f"Missing listed bundle file: {rel}")
            continue
        actual_bytes = target.stat().st_size
        if expected_bytes is not None and int(expected_bytes) != actual_bytes:
            errors.append(f"Byte mismatch for {rel}: expected {expected_bytes}, got {actual_bytes}")
        actual_sha = sha256_file(target)
        if actual_sha != expected_sha:
            errors.append(f"SHA-256 mismatch for {rel}: expected {expected_sha}, got {actual_sha}")
        checked += 1

    required_rel = (
        "figures/firing_rate_comparison.svg",
        "figures/firing_rate_comparison.png",
        "tables/figure1_source_data.csv",
        "REPRODUCIBILITY.md",
    )
    for req in required_rel:
        if req not in seen_paths:
            errors.append(f"Bundle manifest missing required artifact: {req}")

    failed_run_count = int(manifest.get("failed_run_count", -1))
    if failed_run_count < 0:
        errors.append("bundle_manifest.json missing valid failed_run_count")

    return {
        "valid": len(errors) == 0,
        "bundle_dir": str(bundle_dir),
        "checked_files": checked,
        "failed_run_count": failed_run_count,
        "is_synthetic_fixture": bool(manifest.get("is_synthetic_fixture", False)),
        "errors": errors,
    }


def audit_citation_register(register_path: Path) -> dict[str, Any]:
    """Audit literature source_register.yaml for identifiers, DOIs/URLs, and preprint flags."""
    if not register_path.is_file():
        return {
            "valid": False,
            "register_path": str(register_path),
            "sections_checked": 0,
            "total_references": 0,
            "peer_reviewed_count": 0,
            "preprint_count": 0,
            "preprint_ref_ids": [],
            "errors": [f"Citation register not found: {register_path}"],
        }

    doc = yaml.safe_load(register_path.read_text(encoding="utf-8"))
    sources = doc.get("sources") if isinstance(doc, dict) else None
    if not isinstance(sources, list):
        return {
            "valid": False,
            "register_path": str(register_path),
            "sections_checked": 0,
            "total_references": 0,
            "peer_reviewed_count": 0,
            "preprint_count": 0,
            "preprint_ref_ids": [],
            "errors": ["source_register.yaml missing top-level 'sources' list"],
        }

    errors: list[str] = []
    seen_ids: set[str] = set()
    total_refs = 0
    peer_reviewed = 0
    preprints: list[str] = []
    sections_checked = 0

    for sec in sources:
        if not isinstance(sec, dict):
            continue
        sections_checked += 1
        sec_id = str(sec.get("id") or "").strip()
        refs = sec.get("references")
        if isinstance(refs, list):
            if sec_id == "domain_validation_candidates":
                for ref in refs:
                    total_refs += 1
                    if not isinstance(ref, dict) or not (
                        ref.get("topic") and (ref.get("doi") or ref.get("url"))
                    ):
                        errors.append(
                            "Candidate reference in domain_validation_candidates "
                            "missing topic or doi/url"
                        )
                continue
            for ref in refs:
                total_refs += 1
                if not isinstance(ref, dict):
                    errors.append("Non-dict reference entry inside references list")
                    continue
                ref_id = str(ref.get("ref_id") or ref.get("id") or "").strip()
                if not ref_id:
                    errors.append(f"Reference in section {sec.get('id')} missing ref_id")
                elif ref_id in seen_ids:
                    errors.append(f"Duplicate ref_id in citation register: {ref_id}")
                else:
                    seen_ids.add(ref_id)

                has_locator = bool(ref.get("doi") or ref.get("url") or ref.get("pmid"))
                if not has_locator:
                    errors.append(f"Reference {ref_id or '?'} missing doi/url/pmid locator")
                if not (ref.get("citation_short") or ref.get("citation")):
                    errors.append(f"Reference {ref_id or '?'} missing citation text")
                if not ref.get("claim_scope"):
                    errors.append(f"Reference {ref_id or '?'} missing claim_scope")

                pr_status = str(ref.get("peer_review_status", "peer_reviewed")).lower()
                if "preprint" in pr_status:
                    preprints.append(ref_id)
                elif pr_status == "peer_reviewed":
                    peer_reviewed += 1
                else:
                    errors.append(
                        f"Reference {ref_id} has unrecognized peer_review_status: {pr_status}"
                    )
        else:
            sec_id = str(sec.get("id") or "").strip()
            if not sec_id:
                errors.append("Top-level source entry missing id")
            elif sec_id in seen_ids:
                errors.append(f"Duplicate top-level source id: {sec_id}")
            else:
                seen_ids.add(sec_id)
            if not (sec.get("doi") or sec.get("url")):
                errors.append(f"Top-level source {sec_id or '?'} missing doi or url")

    return {
        "valid": len(errors) == 0,
        "register_path": str(register_path),
        "sections_checked": sections_checked,
        "total_references": total_refs,
        "peer_reviewed_count": peer_reviewed,
        "preprint_count": len(preprints),
        "preprint_ref_ids": preprints,
        "errors": errors,
    }


def generate_evidence_linked_methods(
    repo_root: Path,
    protocol_path: Path,
    analysis_dirs: Sequence[Path],
    out_path: Path,
) -> dict[str, Any]:
    """Generate strictly factual methods & results summary from verified on-disk artifacts."""
    proto_doc = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    proto_sha = sha256_file(protocol_path)
    model_cfg = proto_doc.get("model", {})
    seeds_cfg = proto_doc.get("seeds", {})

    analysis_rows: list[dict[str, Any]] = []
    for adir in analysis_dirs:
        mpath = adir / "analysis_manifest.json"
        if not mpath.is_file():
            raise FileNotFoundError(f"Missing analysis_manifest.json in {adir}")
        am = json.loads(mpath.read_text(encoding="utf-8"))
        pm = am["paired_metrics"]
        analysis_rows.append(
            {
                "analysis_dir": adir.as_posix(),
                "manifest_sha256": sha256_file(mpath),
                "target_neuron_id": str(am["target_neuron_id"]),
                "baseline_condition": str(am["baseline_condition"]),
                "treatment_condition": str(am["treatment_condition"]),
                "n_pairs": int(pm["n_pairs"]),
                "failed_run_count": int(am["failed_run_count"]),
                "mean_difference_hz": float(pm["mean_difference_hz"]),
                "sd_difference_hz": float(pm["sd_difference_hz"]),
                "ci95_low_hz": float(pm["bootstrap_ci95_low_hz"]),
                "ci95_high_hz": float(pm["bootstrap_ci95_high_hz"]),
            }
        )

    rel_proto = (
        protocol_path.resolve().relative_to(repo_root.resolve()).as_posix()
        if protocol_path.resolve().is_relative_to(repo_root.resolve())
        else protocol_path.as_posix()
    )
    lines = [
        f"# Evidence-Linked Methods & Quantitative Summary (`{proto_doc['protocol_id']}`)",
        "",
        "> **Research Use Only (RUO):** Auto-generated strictly from verified protocol and "
        "`analysis_manifest.json` artifacts. Zero prose claims or references fabricated.",
        "",
        "## Protocol & Simulation Configuration",
        "",
        f"- **Protocol:** `{rel_proto}` (status: `{proto_doc.get('status')}`, "
        f"intent: `{proto_doc.get('analysis_intent')}`, SHA-256: `{proto_sha}`)",
        f"- **Model:** `{model_cfg.get('id')}` rev `{model_cfg.get('revision')}` "
        f"(backend: `{model_cfg.get('backend')}`, params SHA-256: "
        f"`{model_cfg.get('parameter_manifest_sha256')}`)",
        f"- **Seeds:** `strategy={seeds_cfg.get('strategy')}`, "
        f"`master={seeds_cfg.get('master')}`, `replicates={seeds_cfg.get('replicates')}`",
        "",
        "## Verified Paired Contrasts",
        "",
        "| Target Neuron | Baseline -> Treatment | N Pairs | Failed Runs | Paired Delta (Hz) | "
        "95% Seed Bootstrap CI (Hz) | Manifest SHA-256 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in analysis_rows:
        lines.append(
            f"| `{row['target_neuron_id']}` | `{row['baseline_condition']}` -> "
            f"`{row['treatment_condition']}` | {row['n_pairs']} | {row['failed_run_count']} | "
            f"`{row['mean_difference_hz']:+.4f} +/- {row['sd_difference_hz']:.4f}` | "
            f"`[{row['ci95_low_hz']:+.4f}, {row['ci95_high_hz']:+.4f}]` | "
            f"`{row['manifest_sha256'][:16]}...` |"
        )
    lines.extend(
        [
            "",
            "## Governance & Human Author Sign-Off Placeholders",
            "",
            "- **Authors & ORCID:** `[HUMAN AUTHOR INPUT REQUIRED]`",
            "- **CRediT Contributor Roles:** `[HUMAN AUTHOR INPUT REQUIRED]`",
            "- **Institutional Affiliations & Ethics Scope:** `[HUMAN AUTHOR INPUT REQUIRED]`",
            "- **Funding & Competing Interests:** `[HUMAN AUTHOR INPUT REQUIRED]`",
            "- **AI Assistance Disclosure:** `[HUMAN AUTHOR INPUT REQUIRED]`",
            "",
        ]
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "out_path": str(out_path),
        "protocol_sha256": proto_sha,
        "n_analyses": len(analysis_rows),
    }


def _collect_release_files(repo_root: Path) -> list[Path]:
    candidates: list[Path] = []
    top_files = (
        "CITATION.cff",
        "LICENSE",
        "THIRD_PARTY_NOTICES.md",
        "CHANGELOG.md",
        "pyproject.toml",
        "uv.lock",
        "research/literature/source_register.yaml",
    )
    for rel in top_files:
        p = repo_root / rel
        if p.is_file():
            candidates.append(p)

    glob_patterns = (
        "research/protocols/*.yaml",
        "research/modules/*/target_sets/*.json",
        "research/modules/*/README.md",
        "research/modules/*/evidence_register.md",
        "research/modules/*/model_card.md",
        "research/modules/*/pilot_report.md",
        "research/modules/*/confirmatory_report.md",
        "research/manuscripts/*.md",
        "docs/STATUS.md",
        "docs/data-cards/*.md",
        "docs/model-cards/*.md",
        "docs/validation/*.md",
        "docs/security/*.md",
        "docs/adr/*.md",
    )
    for pat in glob_patterns:
        candidates.extend(sorted(repo_root.glob(pat)))

    unique_sorted = sorted({p.resolve() for p in candidates if p.is_file()})
    return unique_sorted


def build_publication_release_archive(
    repo_root: Path,
    out_dir: Path,
    *,
    include_bundle_dirs: Sequence[Path] = (),
    release_version: str = "0.1.0.dev0",
) -> Path:
    """Assemble and verify an open-science release archive (zip + SHA-256 manifest)."""
    root_res = repo_root.resolve()
    citation_audit = audit_citation_register(
        root_res / "research" / "literature" / "source_register.yaml"
    )
    if not citation_audit["valid"]:
        raise ValueError(f"Citation register audit failed: {citation_audit['errors']}")

    verified_bundles: list[dict[str, Any]] = []
    for bdir in include_bundle_dirs:
        vres = verify_evidence_bundle(bdir)
        if not vres["valid"]:
            raise ValueError(f"Evidence bundle verification failed for {bdir}: {vres['errors']}")
        verified_bundles.append(vres)

    payload_dir = out_dir / "payload"
    if payload_dir.exists():
        shutil.rmtree(payload_dir)
    payload_dir.mkdir(parents=True, exist_ok=True)

    archived_entries: list[dict[str, Any]] = []

    def _copy_and_record(src: Path, rel_posix: str) -> None:
        if _is_restricted_relative_path(rel_posix):
            raise ValueError(f"Refusing to archive restricted path: {rel_posix}")
        dst = _resolve_contained_path(payload_dir, rel_posix)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        archived_entries.append(
            {
                "path": rel_posix,
                "bytes": dst.stat().st_size,
                "sha256": sha256_file(dst),
            }
        )

    for src_path in _collect_release_files(root_res):
        rel = src_path.relative_to(root_res).as_posix()
        _copy_and_record(src_path, rel)

    for bdir in include_bundle_dirs:
        bname = bdir.name
        broot = bdir.resolve()
        for fpath in sorted(broot.rglob("*")):
            if fpath.is_file():
                rel_in_b = fpath.relative_to(broot).as_posix()
                _copy_and_record(fpath, f"bundles/{bname}/{rel_in_b}")

    repro_path = payload_dir / "RELEASE_REPRODUCIBILITY.md"
    repro_path.write_text(
        "\n".join(
            [
                f"# SYNAPSE Open-Science Release Archive (`v{release_version}`)",
                "",
                "> **Research Use Only (RUO):** External biological datasets (`FlyWire/FAFB v630`, "
                "`MaleCNS v1.0`) and credentials (`.env`) are intentionally excluded from this "
                "archive and remain under their upstream terms (`THIRD_PARTY_NOTICES.md`).",
                "",
                "## Offline Verification Commands",
                "",
                "```sh",
                "uv sync --locked",
                "uv run ruff check . && uv run ruff format --check .",
                "uv run pytest -m 'not slow and not gpu and not external'",
                "uv run synapse export verify-citations --json",
                "```",
                "",
                "## Human Approval Gates Required Before External Release",
                "",
                "- Zenodo DOI minting & public archive upload",
                "- Journal manuscript submission & author/CRediT sign-off",
                "- Institutional ethics scope determination & funding disclosure",
                "- Explicit human freeze of draft confirmatory protocols (`P5-SLEEP-001`, "
                "`P5-ADD-001`, `P5-NEURO-001`, `P5-PHARMA-001`, `P5-STRESS-001`)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    archived_entries.append(
        {
            "path": "RELEASE_REPRODUCIBILITY.md",
            "bytes": repro_path.stat().st_size,
            "sha256": sha256_file(repro_path),
        }
    )

    archived_entries.sort(key=lambda r: str(r["path"]))
    zip_filename = f"synapse_release_{release_version}.zip"
    zip_path = out_dir / zip_filename
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for entry in archived_entries:
            rel_posix = str(entry["path"])
            src_file = payload_dir / rel_posix
            info = zipfile.ZipInfo(filename=rel_posix, date_time=_FIXED_ZIP_DATE_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, src_file.read_bytes())

    manifest_payload: dict[str, Any] = {
        "schema_version": "1.0",
        "release_version": release_version,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "ruo_notice": "Research Use Only (RUO) - human approval required before DOI or submission",
        "excluded_restricted_roots": list(RESTRICTED_ARCHIVE_PATTERNS),
        "citation_audit": citation_audit,
        "verified_bundles_count": len(verified_bundles),
        "zip_filename": zip_filename,
        "zip_bytes": zip_path.stat().st_size,
        "zip_sha256": sha256_file(zip_path),
        "files": archived_entries,
    }
    manifest_out = out_dir / "ARCHIVE_MANIFEST.json"
    manifest_out.write_text(
        json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return manifest_out


def verify_publication_release_archive(archive_dir: Path) -> dict[str, Any]:
    """Verify ARCHIVE_MANIFEST.json, payload SHA-256 checksums, and zip-slip / denylist safety."""
    manifest_path = archive_dir / "ARCHIVE_MANIFEST.json"
    if not manifest_path.is_file():
        return {
            "valid": False,
            "archive_dir": str(archive_dir),
            "checked_files": 0,
            "zip_members": 0,
            "errors": [f"Missing ARCHIVE_MANIFEST.json at {manifest_path}"],
        }

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload_dir = archive_dir / "payload"
    errors: list[str] = []
    checked = 0

    for entry in manifest.get("files", []):
        rel = str(entry.get("path", ""))
        if _is_restricted_relative_path(rel):
            errors.append(f"Restricted path present in archive manifest: {rel}")
            continue
        try:
            target = _resolve_contained_path(payload_dir, rel)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if not target.is_file():
            errors.append(f"Missing archived payload file: {rel}")
            continue
        if int(entry["bytes"]) != target.stat().st_size:
            errors.append(f"Byte mismatch for {rel}")
        if str(entry["sha256"]) != sha256_file(target):
            errors.append(f"SHA-256 mismatch for {rel}")
        checked += 1

    zip_filename = str(manifest.get("zip_filename", ""))
    zip_path = archive_dir / zip_filename
    zip_members = 0
    if not zip_path.is_file():
        errors.append(f"Missing archive zip file: {zip_filename}")
    else:
        if str(manifest.get("zip_sha256", "")) != sha256_file(zip_path):
            errors.append(f"ZIP SHA-256 mismatch for {zip_filename}")
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            zip_members = len(names)
            for zname in names:
                if zname.startswith(("/", "\\")) or ".." in Path(zname).parts or ":" in zname:
                    errors.append(f"Unsafe zip member path: {zname}")
                if _is_restricted_relative_path(zname):
                    errors.append(f"Restricted file inside zip: {zname}")

    return {
        "valid": len(errors) == 0,
        "archive_dir": str(archive_dir),
        "checked_files": checked,
        "zip_members": zip_members,
        "errors": errors,
    }
