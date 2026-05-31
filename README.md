# ubu-phase0-demo

UbU Phase 0 — a Python-only, CLI-only demo prototype for ETHConf NYC (June 8–10, 2026).

**This is not Phase 1 and not production architecture.** Phase 0 code is not assumed to survive into Phase 1. See `docs/PHASE0_PROCESS.md` for the full master specification.

## Status of this checkout

This repository is the **preparation foundation**. It contains:

- the **frozen schema** (`src/ubu_phase0/schema.py`, ticket T001 — complete and verified),
- the **golden fixtures** (`fixtures/`, ticket T002 — complete),
- the **documentation packet** (`PHASE0_*.md` and `docs/PHASE0_PROCESS.md`),
- `AGENTS.md` (agent rails),
- the **ticket files** (`tickets/`).

The implementation modules `affect.py`, `github_ingest.py`, `planner.py`, `bootstrap.py`, `loop.py`, and `cli.py` are **not yet written**. They are generated one ticket at a time (T003–T009) by an agent following `AGENTS.md` and the ticket JSON, with a reviewer pass between tickets.

## Quick start (developers)

Requires Python 3.10+ (pinned dependencies; PyGithub is optional and not needed for the offline demo or tests).

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # resolves cleanly with pinned versions
python -m pytest                 # 14 frozen-schema tests pass

# Live GitHub path only (optional, not needed for --offline demo):
pip install -e ".[github]"
```

## Demo (after implementation lands)

```bash
export UBU_PHASE0_GITHUB_TOKEN=...      # shell only; never commit
export UBU_PHASE0_GITHUB_OWNER=UbU-dummy
export UBU_PHASE0_GITHUB_REPO=ubu-design

ubu-phase0 demo                          # live
ubu-phase0 demo --offline                # deterministic fixture path
ubu-phase0 refresh                       # re-fetch live issues (operator-driven)
```

## Build order

1. `src/ubu_phase0/schema.py` — generated and FROZEN (done).
2. `fixtures/` — generated (done).
3. T003–T009 — one module per ticket, reviewer pass between each.
4. Rehearse live and `--offline`.
5. v1.5 tickets T010–T015 only if the v1 path is stable.

The single discipline that matters most: Phase 0 is impressive because it is concrete, not because it is broad.
