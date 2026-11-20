# Security Policy

> **Research Use Only (RUO):** SYNAPSE is an offline-capable, local-first computational neuroscience research environment. It must never ingest, store, or process Protected Health Information (PHI), patient identifiers, or clinical records.

## Security Design Controls

Full operational controls and backup/restore verification procedures are documented in [`docs/security/operations_and_backup.md`](docs/security/operations_and_backup.md):

1. **Loopback-Only Bindings:** [`compose.yaml`](compose.yaml) and `synapse-api` bind PostgreSQL (`5432`), HTTP API (`8000`), and the Vite workbench (`5173`) strictly to `127.0.0.1` with explicit local CORS allowlisting (`SYNAPSE_CORS_ORIGINS`).
2. **Allowlisted Subprocess Execution:** [`subprocess_entry.py`](apps/worker/synapse_worker/subprocess_entry.py) permits only fixed job kinds (`protocol_experiment`, `analysis`, `export_bundle`). Arbitrary code execution, remote URL fetches inside runs, and untrusted `pickle` deserialization (e.g., upstream `sez_neurons.pickle` is explicitly excluded) are forbidden.
3. **Container & Filesystem Isolation:** Docker services run as unprivileged user/group `10001:10001` without Docker socket mounts, mount `./data` read-only, and enforce strict path containment (`resolve_within_root`) and identifier regex checks in [`security.py`](apps/api/synapse_api/security.py).
4. **Secret Hygiene:** Keep runtime passwords and credentials out of Git and manifest logs. Use untracked `.env` files locally (only [`.env.example`](.env.example) with placeholder values is tracked).

## Reporting a Vulnerability

If you discover a security issue (path traversal, command injection, dependency vulnerability, or accidental credential exposure):

1. **Do not** open a public GitHub issue with exploit details or credentials.
2. Report privately via [GitHub Security Advisories](https://github.com/mburakmmm/synapse/security/advisories/new) on `mburakmmm/synapse`.
3. Include a minimal reproduction, affected commit/file paths, and potential impact. We will acknowledge receipt and work on a verified patch with regression tests.
