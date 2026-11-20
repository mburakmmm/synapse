"""Path containment and identifier validation controls for HTTP/worker boundaries."""

from __future__ import annotations

import re
from pathlib import Path

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class PathContainmentError(PermissionError):
    """Raised when a caller-supplied path attempts to escape an allowed root directory."""


class InvalidIdentifierError(ValueError):
    """Raised when an identifier violates safe allowlist constraints."""


def validate_identifier(value: str, label: str = "identifier") -> str:
    """Validate path-segment identifiers against safe characters and reject dot-segments."""
    if not value or len(value) > 200 or value in {".", ".."} or ".." in value:
        raise InvalidIdentifierError(f"Invalid {label}: {value!r}")
    if not _IDENTIFIER_RE.fullmatch(value):
        raise InvalidIdentifierError(f"Disallowed characters in {label}: {value!r}")
    return value


def resolve_within_root(root: Path, relative_path: str) -> Path:
    """Safely resolve a relative path strictly inside ``root`` (blocks traversal and symlinks)."""
    if not relative_path or "\x00" in relative_path:
        raise PathContainmentError("Path cannot be empty or contain NUL bytes")
    normalized = relative_path.replace("\\", "/")
    candidate_rel = Path(normalized)
    if candidate_rel.is_absolute() or candidate_rel.drive:
        raise PathContainmentError(f"Absolute paths are not permitted: {relative_path!r}")
    if any(part == ".." for part in candidate_rel.parts):
        raise PathContainmentError(f"Parent traversal '..' is not permitted: {relative_path!r}")

    resolved_root = root.resolve()
    resolved_target = (resolved_root / candidate_rel).resolve()
    if resolved_target == resolved_root or not resolved_target.is_relative_to(resolved_root):
        raise PathContainmentError(
            f"Resolved path escapes allowed directory boundary: {relative_path!r}"
        )
    return resolved_target
