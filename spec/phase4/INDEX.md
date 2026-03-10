# Phase 4 — Production & Automation: Task Index

**Branch:** `feature/phase4-production-automation`
**Started:** 2026-03-10
**Status:** In Progress

---

## Streams

| Stream | Document | Status | Priority |
|--------|----------|--------|----------|
| A | [CLI & Headless Pipeline API](./STREAM_A_CLI_API.md) | Complete | P1 |
| B | [Scene Validator](./STREAM_B_SCENE_VALIDATOR.md) | Complete | P1 |
| C | [Structured Logging](./STREAM_C_LOGGING.md) | Complete | P2 |
| D | [Config-Driven Parameters](./STREAM_D_CONFIG_DRIVEN.md) | Complete | P2 |
| E | [Renderer Adapter Improvements](./STREAM_E_RENDERER_ADAPTERS.md) | Complete | P2 |

> Asset Manager (Stream F) and VRay adapter deferred — not in scope for this branch.

---

## Recommended Execution Order

```
1. Stream C  (Logging)        — low risk, touches every file, enables better debugging
2. Stream D  (Config-driven)  — small patches, unlocks correct behaviour in other streams
3. Stream B  (Validator)      — new isolated module, no UI
4. Stream E  (Renderer)       — extends existing pattern
5. Stream A  (CLI + API)      — builds on all above, highest external impact
```

---

## Completion Checklist

- [x] Stream C complete + tests passing
- [x] Stream D complete + tests passing
- [x] Stream B complete + tests passing
- [x] Stream E complete + tests passing
- [x] Stream A complete + tests passing
- [ ] CLAUDE.md Phase 4 status updated
- [ ] MEMORY.md updated
- [ ] Branch merged to main

---

## Key Files Touched Per Stream

| Stream | New Files | Modified Files |
|--------|-----------|----------------|
| C | `core/logging_config.py` | All modules (replace print with logger) |
| D | none | `asset_scanner.py`, `asset_manager_dialog.py`, `core/nodes.py`, `core/gaffer/resolver.py`, `project_configs/ctx_config.json` |
| B | `core/validator/__init__.py`, `core/validator/base_check.py`, `core/validator/checks/*.py` | none |
| E | `core/renderers/vray.py` (deferred) | `core/renderers/__init__.py`, `core/renderers/redshift.py`, `core/renderers/arnold.py`, `project_configs/ctx_config.json`, `core/nodes.py` |
| A | `tools/pipeline_api.py`, `tools/cli.py` | none |
