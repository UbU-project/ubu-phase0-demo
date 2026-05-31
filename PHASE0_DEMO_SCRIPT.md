## 14. `PHASE0_DEMO_SCRIPT.md`

### 14.1 Story

UbU is preparing its own Phase 0 release. The project's work lives as GitHub issues. UbU imports those issues as Tasks, builds a planning request, applies dependency and affect constraints, and shows what fits into the next four hours — honestly labeling what it does and does not model.

### 14.2 Setup

```
export UBU_PHASE0_GITHUB_TOKEN=...
export UBU_PHASE0_GITHUB_OWNER=UbU-dummy
export UBU_PHASE0_GITHUB_REPO=ubu-design
```

Pre-flight (operator): run `ubu-phase0 demo --offline` once to confirm the fixture path is healthy before going live.

### 14.3 Live run

```
ubu-phase0 demo
```

Expected output sections, in order:

```
UbU Phase 0 Demo
Data source: live GitHub          Repository: UbU-dummy/ubu-design
Imported Tasks                    (number, with source_ref and authority_source)
Affect Profile                    (qualitative presets chosen at bootstrap)
Planning Window                   (today, next 4 hours)
Calendar Preview                  (Rich table)
Claim Register Summary            (status counts and notable deferrals)
Footer                            probability_quality / coverage_estimate
```

Calendar table columns and a representative row:

```
Time          Task                                   Source         Affect
09:00–09:30   Write Phase 0 contract profile         github_event   ▆▆▆
09:30–10:00   Freeze schema module                   github_event   ▃▃▃
10:00–10:30   Generate acceptance fixtures           github_event   ▆▆▆

probability_quality: not_estimated  (Phase 1 will populate)
coverage_estimate:   —              (Phase 1 will populate)
```

### 14.4 Audience-created issue flow

An audience member opens an issue in `UbU-dummy/ubu-design` (optionally tagging `ubu:duration:60m`, `ubu:priority:high`, `ubu:depends-on:#N`). The operator then:

```
ubu-phase0 refresh
ubu-phase0 demo
```

The new issue appears as a Task in the next preview.

### 14.5 Required visible proof

The demo must visibly show, for at least one Task: the issue number, the issue title, the `source_ref`, the `authority_source`, the Calendar placement, the affect-margin indicator, the active data source, and the claim summary.

### 14.6 Offline safety

If the network or token fails at any point, the operator reruns with `--offline`. The fixture run reproduces the full loop deterministically from `static_dummy_issue.json` with known dependency edges, so the demo always has a working path.

### 14.7 v1.5 stretch (only if implemented)

Mark the first Task complete with a single key; the planner reruns with the accumulated `LogEntry` list; the CLI shows a "Completed" section above a changed Calendar preview. Optionally, `--demo-impossible` loads a cyclic fixture to show UbU rendering a `SkeletonFailureDiagnostic` instead of crashing.

---

---

_Extracted from `docs/PHASE0_PROCESS.md`. The master document is the authority; if this file and the master disagree, the master wins._
