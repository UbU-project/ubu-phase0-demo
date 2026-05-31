## 8. `PHASE0_GITHUB_INGESTION.md`

### 8.1 Source repository and configuration

```
owner: UbU-dummy
repo:  ubu-design
url:   https://github.com/UbU-dummy/ubu-design
```

Environment variables:

```
UBU_PHASE0_GITHUB_TOKEN   (required for live mode; never committed)
UBU_PHASE0_GITHUB_OWNER   (default UbU-dummy)
UBU_PHASE0_GITHUB_REPO    (default ubu-design)
```

The intended token is a fine-grained, read-only token scoped to `UbU-dummy/ubu-design` with Issues and metadata permissions only. The implementation must not require broader permissions.

### 8.2 Mode selection

- Default: live. `demo` fetches open issues from the configured repository.
- `--offline`: fixture mode. `demo` reads `fixtures/static_dummy_issue.json` and never touches the network.
- The two modes are mutually exclusive. There is no auto-fallback and no on-disk cache.
- The CLI must report the active source on every run (see `PHASE0_DEMO_SCRIPT.md`).

### 8.3 Data read from issues

Supported: issue number, title, body, labels, state, `html_url`, `created_at`, `updated_at`.

Ignored: comments, pull requests, CI, milestones, assignees, project boards, reactions, linked branches.

### 8.4 Issue-to-`TaskSpec` mapping

For issue number `N` in `UbU-dummy/ubu-design`:

```
id            = github:UbU-dummy/ubu-design#N
title         = issue title
description   = issue body or ""
source        = github_issue
source_ref    = github:UbU-dummy/ubu-design#N
external_id   = "N"
external_url  = issue html_url
authority_source = github_event   (imported_config for the static fixture issue)
duration      = label-derived, default fixed 30 minutes (1800 seconds)
priority      = label-derived, default medium
affect hints  = label-derived, else safe defaults
dependencies  = depends-on label edges (live) or hardcoded (fixture), else []
```

### 8.5 Pull-request exclusion

The GitHub `/issues` endpoint returns pull requests alongside issues. If an item carries `pull_request` metadata, skip it. This rule is mandatory; agents miss it without explicit instruction.

### 8.6 Deduplication

Deduplicate by `source_ref` (equivalently owner/repo/number). The deduplicated result must be deterministic in ordering.

### 8.7 Label mapping

Supported label families:

```
ubu:duration:15m | ubu:duration:30m | ubu:duration:60m | ubu:duration:90m
ubu:priority:low | ubu:priority:medium | ubu:priority:high
ubu:energy:low-ok | ubu:energy:medium | ubu:energy:high
ubu:stress:low | ubu:stress:medium | ubu:stress:high-risk
ubu:mood:calm | ubu:mood:engaged | ubu:mood:intense-risk
ubu:depends-on:#N   (dependency edge; see 8.9)
```

Conflict rule: when an issue carries more than one label in the same family, take the first one alphabetically and emit a warning. Never silently merge.

Unknown labels: preserve for display, do not fail import, do not affect scheduling.

### 8.8 Safe defaults

```
duration_minutes    = 30
priority            = medium
energy_requirement  = medium
stress_risk         = medium
mood_intensity_risk = engaged
dependencies        = []
```

An unlabeled issue must import successfully under these defaults.

### 8.9 Dependencies

Live issues declare dependencies via a label convention `depends-on: #N` (carried as an `ubu:depends-on:#N` label). The fixture file hardcodes dependency edges directly.

- Source of truth is labels only. Issue bodies are not parsed in v1.
- A `depends-on` target that does not exist in the imported set or has been closed: emit a warning, treat the dependency as absent, log the event, continue. Do not crash and do not drop the dependent issue from the plan.
- Cycles are reported clearly by the planner's DAG validation and surfaced by the CLI.

The fixture dependency edges live inside `fixtures/static_dummy_issue.json` so that fixture mode is fully deterministic and self-contained.

---

---

_Extracted from `docs/PHASE0_PROCESS.md`. The master document is the authority; if this file and the master disagree, the master wins._
