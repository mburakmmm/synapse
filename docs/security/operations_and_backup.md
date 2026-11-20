# Security, Privacy, and Backup/Restore Operations (`AGENTS.md` §13)

## 1. Local-First Network & Access Boundaries

- **Loopback Binding Only:** `synapse_api.cli` and [`compose.yaml`](../../compose.yaml) bind HTTP, Web UI, and PostgreSQL ports strictly to `127.0.0.1` (`5432`, `8000`, `5173`). No public internet listener or telemetry egress is configured.
- **Restrictive CORS:** Only explicit local origins (`SYNAPSE_CORS_ORIGINS`, defaulting to `http://127.0.0.1:5173,http://localhost:5173`) and `GET`/`POST` methods are enabled without wildcard credentials.
- **No Clinical / PHI Ingestion:** SYNAPSE is Research Use Only (`RUO`); human patient records or clinical identifiers must never be stored in `data/`, `runs/`, or the metadata DB.
- **Zero Secret Storage in VCS:** Credentials stay in untracked `.env`; [`.env.example`](../../.env.example) carries placeholder values only.

## 2. Execution & Input Safety Controls

- **Allowlisted Worker Execution:** [`subprocess_entry.py`](../../apps/worker/synapse_worker/subprocess_entry.py) accepts only three fixed job kinds (`protocol_experiment`, `analysis`, `export_bundle`). No user-supplied Python, shell command, or untrusted pickle deserialization is allowed.
- **No Docker Socket in Workers:** The worker container runs as UID/GID `10001` without `/var/run/docker.sock` and mounts `./data` read-only.
- **Path Containment & Identifier Allowlisting:** [`security.py`](../../apps/api/synapse_api/security.py) enforces regex validation (`validate_identifier`) and real-path containment (`resolve_within_root`) on every dataset, protocol, run artifact, and bundle file endpoint.
- **Human Freeze Gate:** Freezing a protocol via CLI (`--confirm-freeze`) or HTTP (`confirmed: true`) fails closed without deliberate confirmation and refuses to overwrite existing frozen revisions.

## 3. Backup & Restore Procedures

### Local SQLite Metadata + Immutable `runs/` Snapshot Verification

The automated round-trip script [`backup_restore_verify.py`](../../scripts/backup_restore_verify.py) exercises `sqlite3.Connection.backup(...)` (WAL-safe online snapshot) plus SHA-256 verification across all files under `runs/`:

```powershell
uv run python scripts/backup_restore_verify.py --db-path runs/synapse_lab.sqlite3 --runs-dir runs --work-dir artifacts/backup_check
```

### PostgreSQL (`compose.yaml` Profile) Backup & Restore

```sh
# Backup metadata database (custom compressed archive)
docker compose exec -T postgres pg_dump -U synapse -d synapse -Fc > backup_synapse.dump

# Archive immutable run artifacts alongside database backup
tar -czf backup_runs.tar.gz runs/

# Restore into a fresh PostgreSQL instance + run Alembic check
docker compose exec -T postgres pg_restore -U synapse -d synapse --clean --if-exists < backup_synapse.dump
SYNAPSE_DATABASE_URL="postgresql+psycopg://synapse:<password>@127.0.0.1:5432/synapse" uv run alembic -c apps/api/alembic.ini upgrade head
```

### Live Container & PostgreSQL Verification Record (`2026-11-20`)

- Built and booted full `compose.yaml` stack (`postgres:16-alpine`, non-root `api`, `worker`, `web` on Docker `29.9.3` `linux/x86_64`).
- Verified loopback HTTP health (`127.0.0.1:8000/api/v1/health`), Web UI & `/api` Vite proxy (`127.0.0.1:5173`), idempotent `POST /api/v1/jobs` (`201`/`200`), PostgreSQL `FOR UPDATE SKIP LOCKED` worker execution for `analysis` + `export_bundle` with SVG download, and PostgreSQL `pg_dump` -> `pg_restore` exact table row count parity (`jobs=2`, `audit_events=6`) prior to clean teardown (`docker compose down -v`).

Never auto-prune immutable research outputs in `runs/` or raw datasets in `data/`.
