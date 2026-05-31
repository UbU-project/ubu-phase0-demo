## 9. `PHASE0_DEMO_FAILURE_MODES.md`

The demo fails predictably and never silently. Live-mode credential and network failures are clean non-zero exits; data-shape problems degrade gracefully.

| Condition | Mode | Behavior |
|---|---|---|
| Missing token | live | Clean message naming `UBU_PHASE0_GITHUB_TOKEN`; non-zero exit. No fallback. |
| Invalid token | live | Clean message (note GitHub may surface this as a 404, not 401); non-zero exit. |
| Network failure | live | Clean message; non-zero exit. |
| Rate limit | live | Clean message with reset time if available; non-zero exit. |
| Empty issue list | live | Warn that no open issues were found; exit cleanly. Operator may rerun with `--offline`. |
| Malformed issue | either | Skip the issue, report the skipped count, continue if at least one valid Task remains. |
| Duplicate issue | either | Deduplicate by `source_ref`, report the duplicate count if useful, continue. |
| Missing dependency target | either | Warn, treat as absent, log, continue. |
| Dependency cycle | either | Planner reports an invalid dependency graph; CLI shows a clear error. In fixture mode the bundled edges are known-acyclic, so this only arises from live audience input. |
| No feasible tasks after affect gate | either | Show an empty Calendar preview with an explanation of why nothing was scheduled. Do not crash. |
| Fixture missing | offline | Hard failure naming the missing path. |

The `--offline` switch removes the entire first block of credential/network failure modes by construction, which is its purpose as a demo safety net.

---

---

_Extracted from `docs/PHASE0_PROCESS.md`. The master document is the authority; if this file and the master disagree, the master wins._
