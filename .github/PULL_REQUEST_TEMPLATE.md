## Summary

<!-- Briefly describe what changed and why. Link relevant ADRs or protocols. -->

## Research & Integrity Classification

- [ ] Engineering / documentation / test change only (no biological claims)
- [ ] Numerical verification or computational reproduction change
- [ ] Experimental protocol / confirmatory analysis change (frozen or draft clearly marked)

## Checklist (`AGENTS.md` Compliance)

- [ ] Preserves strict **Research Use Only (RUO)** scope (no clinical/human diagnostic claims or PHI)
- [ ] Does not modify `AGENTS.md` or overwrite immutable frozen protocols (e.g. `research/protocols/*.frozen.yaml`)
- [ ] Contains **zero** files from `data/`, `runs/`, `graphify-out/`, `.env`, credentials, or binary connectome artifacts
- [ ] Preserves import DAG boundaries (`test_import_boundaries.py`) and 64-bit string neuron IDs
- [ ] Verified locally after final edits:
  - [ ] `uv run ruff check .` and `uv run ruff format --check .`
  - [ ] `uv run mypy packages apps/api apps/worker tests`
  - [ ] `uv run pytest -m "not slow and not gpu and not external" -v`
  - [ ] If `apps/web` modified: `npm run typecheck`, `npm run test`, `npm run build`
