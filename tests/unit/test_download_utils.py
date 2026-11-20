"""Unit tests for upstream checksum hashing and offline download reuse."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from synapse_data import (
    ChecksumMismatchError,
    download_file_atomic,
    git_blob_sha1_file,
    md5_file,
    verify_upstream_checksum,
)


@pytest.mark.unit
def test_git_blob_sha1_and_md5_verification(tmp_path: Path) -> None:
    payload = b"hello flywire connectome\n"
    f = tmp_path / "sample.txt"
    f.write_bytes(payload)

    expected_blob = hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()
    expected_md5 = hashlib.md5(payload).hexdigest()
    expected_sha256 = hashlib.sha256(payload).hexdigest()

    assert git_blob_sha1_file(f) == expected_blob
    assert md5_file(f) == expected_md5
    assert verify_upstream_checksum(f, f"git-blob-sha1:{expected_blob}") is True
    assert verify_upstream_checksum(f, f"md5:{expected_md5}") is True
    assert verify_upstream_checksum(f, f"sha256:{expected_sha256}") is True
    assert verify_upstream_checksum(f, "md5:00000000000000000000000000000000") is False


@pytest.mark.unit
def test_download_file_atomic_offline_reuse_and_scheme_guard(tmp_path: Path) -> None:
    payload = b"cached connectome bytes"
    dest = tmp_path / "cached.bin"
    dest.write_bytes(payload)
    expected_md5 = f"md5:{hashlib.md5(payload).hexdigest()}"

    # Existing valid cached file reuses offline without performing HTTP transfer
    size, digest = download_file_atomic(
        "https://example.invalid/unreachable.bin",
        dest,
        expected_bytes=len(payload),
        upstream_checksum=expected_md5,
    )
    assert size == len(payload)
    assert digest == hashlib.sha256(payload).hexdigest()

    # Disallowed scheme raises ValueError
    with pytest.raises(ValueError, match="Disallowed URL scheme"):
        download_file_atomic("file:///etc/passwd", tmp_path / "x.bin")

    # Size mismatch helper check via verify_upstream_checksum
    assert not verify_upstream_checksum(dest, "sha256:" + "0" * 64)
    assert ChecksumMismatchError.__mro__[1] is ValueError
