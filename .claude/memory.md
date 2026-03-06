# Project Memory — Maya Multishot Pipeline

> AI agent session log. Update this file at the end of every work session.
> Format: newest entries first. Keep entries concise.

---

## Project Identity

- **Name:** Maya Multishot Pipeline
- **Repo:** https://github.com/katha-begin/maya-multishot.git
- **Purpose:** Multi-shot context management for Maya artists (no scene open/close cycling)
- **Stack:** Python 3.7+ (Maya 2022+), PySide2/PySide6, Maya cmds API, custom network nodes

---

## Current State

**Updated:** 2026-03-06
**Active Branch:** `feature/ui-tools-framework`
**Current Phase:** Phase 2 — UI & Tools Framework Migration (COMPLETE)

### Phase 2 Checklist

| Step | File | Status |
|---|---|---|
| 1 | `tools/base_manager.py` | ✅ Done |
| 2 | `ui/base_dialog.py` | ✅ Done |
| 3 | `tools/shot_manager.py` (migrate) | ✅ Done |
| 4 | `tools/asset_manager.py` (migrate) | ✅ Done |
| 5 | `ui/main_window.py` (migrate) | ✅ Done |
| 6 | `ui/__init__.py` (update) | ✅ Done |
| 7 | `tools/__init__.py` (update) | ✅ Done |
| 8 | Remove 5 dead `ui/` files | ✅ Done |
| 9 | Fix `core/ctx_linker.py` Maya import guard | ✅ Done |
| 10 | Fix `tests/test_node_schemas.py` stale assertions | ✅ Done |

### Completed Phases (DO NOT REVISIT)

- ✅ Phase 0: Repository setup
- ✅ Phase 1–4: Core nodes, paths, display layers, basic UI
- ✅ Phase 5: Light Gaffer System (63 tests passing)
- ✅ Phase 1-schema: Schema-based node system (all 6 node types complete)

---

## Key Decisions & Architecture

### Node System Decision (FINAL)
- **Primary:** `core/nodes/wrappers/` — schema-based, use for ALL new code
- **Legacy:** `core/custom_nodes.py` — FROZEN, backward compat only, do NOT modify
- **Attribute name:** `ctx_type` (snake_case) — NOT `ctx_node_type`

### Connection Pattern Decision (FINAL)
- **Unidirectional ONLY:** `child.message → parent.attribute`
- Never create bidirectional connections
- Query in both directions from a single connection using `source=True/False`

### Gaffer Architecture (FINAL)
- Each Sequence and Shot directly owns its gaffer (`Sequence.gaffer`, `Shot.gaffer`)
- Gaffers form an inheritance chain via `parentGaffer` connections
- Attribute resolution walks chain: Shot gaffer → Sequence gaffer → Master gaffer → fallback

### Path Resolution (CRITICAL — easy to get wrong)
- Config: `project_configs/ctx_config.json` — single source of truth for templates, roots, tokens
- Templates are **named keys** in config (`publishPath`, `assetPath`, etc.) — never write template strings by hand
- All tokens are **camelCase**: `$projRoot`, `$assetType`, `$assetName`, `$variant` — NOT `$asset_type`
- `_` in templates is a separator, NOT part of token names: `$ep_$seq_$shot` = three tokens
- Resolver auto-injects `projRoot`, `imgRoot`, `project`, `sceneBase`, `assetBase` from config
- Real example: `"publishPath"` → `$projRoot$project/$sceneBase/$ep/$seq/$shot/$dept/publish`
  → Windows result: `V:\SWA\all\scene\Ep04\sq0070\SH0170\lighting\publish`

### BaseManager Pattern (PLANNED for Phase 2)
- `MAYA_AVAILABLE` flag for Maya-free testing
- `MockCmds` for test isolation
- Dependency injection: pass `cmds` to constructors

---

## Known Issues / Watchpoints

| Issue | File | Notes |
|---|---|---|
| Pre-existing test failures | `tests/test_asset_manager.py` | `add_asset()` imports `create_standin_with_namespace` from `core.nodes` which doesn't exist — renderer handlers not yet implemented (Phase 3+) |

---

## Session Log

### 2026-03-06 — Session 3
**Done:**
- Completed Phase 2 — all 8 migration tasks done
- Fixed `core/ctx_linker.py`: added try/except guard around `from maya import cmds` (was causing ImportError in non-Maya test environments)
- Fixed `tests/test_node_schemas.py`: updated stale assertions — `ctx_node_type` → `ctx_type`; removed `parentNode` (deleted from gaffer schema); removed `parentGaffer` from LightContext connections (also deleted per unidirectional pattern)
- All schema tests and shot manager tests passing: 39/39

**Remaining pre-existing failure (NOT caused by Phase 2):**
- `tests/test_asset_manager.py` (10 failures) — `tools/asset_manager.py:87` imports `create_standin_with_namespace` from `core.nodes` which doesn't exist; renderer handlers are Phase 3+ work

**Next session should start with:**
- Phase 3: Asset type handlers (Arnold StandIn, Redshift Proxy, USD)
- Or: Fix `test_asset_manager.py` by stubbing or removing the renderer-specific import in `add_asset()`

### 2026-03-05 — Session 1
**Done:**
- Reviewed entire project architecture and code
- Created `CLAUDE.md` (project root) — AI agent quick reference
- Created `.claude/memory.md` (this file) — session persistence

---

## Quick Command Reference

```bash
# Run tests
pytest tests/ -v
pytest --cov=core --cov-report=html tests/

# Git
git checkout feature/ui-tools-framework
git status
git log --oneline -10
```

```python
# Maya: Launch main UI
exec(open(r'E:/dev/maya-multishot/launch_multishot_dockable.py').read())

# Create nodes (correct pattern)
from core.nodes.wrappers import CTXManagerNode, CTXSequenceNode, CTXShotNode
manager = CTXManagerNode.create(projectName='MyProject')
seq = CTXSequenceNode.create(sequenceCode='sq0070')
shot = CTXShotNode.create(ep='Ep04', seq='sq0070', shot='SH0170')
manager.add_sequence(seq)
seq.add_shot(shot)
```
