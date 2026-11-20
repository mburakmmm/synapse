"""Checksum-verified atomic file downloader with retry and offline reuse."""

from __future__ import annotations

import hashlib
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


class ChecksumMismatchError(ValueError):
    """Raised when a downloaded or cached file fails byte-size or checksum verification."""


class DownloadError(RuntimeError):
    """Raised when a file transfer fails after exhausting bounded retries."""


def git_blob_sha1_file(path: Path) -> str:
    """Compute the Git blob SHA-1 object hash (``sha1('blob <size>\\0' + bytes)``)."""
    size = path.stat().st_size
    h = hashlib.sha1()
    h.update(f"blob {size}\0".encode("ascii"))
    with path.open("rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.hexdigest()


def md5_file(path: Path) -> str:
    """Compute streaming MD5 hex digest of a file."""
    h = hashlib.md5()
    with path.open("rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.hexdigest()


def sha256_file_digest(path: Path) -> str:
    """Compute streaming SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.hexdigest()


def verify_upstream_checksum(path: Path, upstream_checksum: str) -> bool:
    """Verify a file against an explicit prefixed upstream checksum.

    Supported prefixes: ``git-blob-sha1:``, ``md5:``, ``sha256:``.
    """
    if ":" not in upstream_checksum:
        raise ValueError(f"Checksum must be '<algo>:<hex>', got {upstream_checksum!r}")
    algo, expected = upstream_checksum.split(":", 1)
    algo_norm = algo.strip().lower()
    expected_norm = expected.strip().lower()
    if algo_norm == "git-blob-sha1":
        return git_blob_sha1_file(path).lower() == expected_norm
    if algo_norm == "md5":
        return md5_file(path).lower() == expected_norm
    if algo_norm == "sha256":
        return sha256_file_digest(path).lower() == expected_norm
    raise ValueError(f"Unsupported upstream checksum algorithm {algo!r}")


def _verify_file_complete(
    path: Path,
    *,
    expected_bytes: int | None,
    upstream_checksum: str | None,
) -> None:
    actual_bytes = path.stat().st_size
    if expected_bytes is not None and actual_bytes != expected_bytes:
        raise ChecksumMismatchError(
            f"Size mismatch for {path}: expected {expected_bytes} bytes, got {actual_bytes}"
        )
    if upstream_checksum is not None and not verify_upstream_checksum(path, upstream_checksum):
        raise ChecksumMismatchError(
            f"Upstream checksum mismatch for {path}: expected {upstream_checksum}"
        )


def download_file_atomic(
    url: str,
    dest: Path,
    *,
    expected_bytes: int | None = None,
    upstream_checksum: str | None = None,
    max_retries: int = 3,
    timeout_s: float = 60.0,
) -> tuple[int, str]:
    """Download ``url`` atomically to ``dest``, verifying size and upstream checksum.

    Reuses an existing file at ``dest`` offline when its size and checksum already match.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("https", "http"):
        raise ValueError(f"Disallowed URL scheme {parsed.scheme!r} for {url!r}")
    if max_retries < 1:
        raise ValueError("max_retries must be >= 1")

    dest = dest.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.is_file():
        try:
            _verify_file_complete(
                dest, expected_bytes=expected_bytes, upstream_checksum=upstream_checksum
            )
            return dest.stat().st_size, sha256_file_digest(dest)
        except ChecksumMismatchError:
            pass

    part_path = dest.with_name(f"{dest.name}.part")
    last_exc: Exception | None = None

    for attempt in range(max_retries):
        try:
            existing_part_bytes = part_path.stat().st_size if part_path.is_file() else 0
            headers = {"User-Agent": "synapse-research-downloader/0.1"}
            if existing_part_bytes > 0 and (
                expected_bytes is None or existing_part_bytes < expected_bytes
            ):
                headers["Range"] = f"bytes={existing_part_bytes}-"

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                status = getattr(resp, "status", 200)
                mode = "ab" if status == 206 and existing_part_bytes > 0 else "wb"
                with part_path.open(mode) as fh:
                    while chunk := resp.read(262144):
                        fh.write(chunk)

            _verify_file_complete(
                part_path, expected_bytes=expected_bytes, upstream_checksum=upstream_checksum
            )
            part_path.replace(dest)
            return dest.stat().st_size, sha256_file_digest(dest)

        except ChecksumMismatchError:
            if part_path.is_file():
                part_path.unlink()
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_exc = exc
            if attempt + 1 < max_retries:
                time.sleep(min(2.0**attempt, 8.0))

    raise DownloadError(f"Failed to download {url} after {max_retries} attempt(s): {last_exc}")
