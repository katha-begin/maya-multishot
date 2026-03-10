# Stream B — Scene Validator

**Status:** Not Started
**Priority:** P1 — Scene drift currently only discovered at render time
**Branch:** `feature/phase4-production-automation`
**Dependencies:** Stream C (logging) should be done first

---

## Goal

Provide a `SceneValidator` that runs a set of named checks against a shot and
returns a structured report. Can be called from the UI, from CLI (Stream A), or
from a farm pre-render hook.

---

## Architecture

```
core/
  validator/
    __init__.py          ← exports SceneValidator, ValidatorReport, CheckResult
    base_check.py        ← BaseCheck abstract class
    checks/
      __init__.py
      shot_nodes.py      ← CTX node hierarchy integrity
      asset_paths.py     ← resolved paths exist on disk
      frame_range.py     ← shot frame range vs Maya timeline
      renderer.py        ← active renderer matches asset file extensions
      gaffer.py          ← gaffer chain valid, no orphaned contexts
      namespace.py       ← no duplicate namespaces in scene
```

---

## Data Types

### `CheckResult` (in `core/validator/__init__.py`)

```python
class CheckResult:
    check_name: str        # e.g. 'asset_paths'
    passed: bool
    severity: str          # 'error' | 'warning' | 'info'
    message: str           # one-line human summary
    details: dict          # extra context (which asset, which node, etc.)
```

### `ValidatorReport` (in `core/validator/__init__.py`)

```python
class ValidatorReport:
    def __init__(self, shot_id, results):
        self.shot_id = shot_id         # e.g. 'Ep04_sq0070_SH0170'
        self.results = results         # list[CheckResult]

    def passed(self):
        """True if no CheckResult has severity='error'."""

    def errors(self):
        """Filter: severity='error'."""

    def warnings(self):
        """Filter: severity='warning'."""

    def to_dict(self):
        """JSON-serializable dict."""

    def to_text(self):
        """Human-readable multi-line summary."""
```

### `BaseCheck` (in `core/validator/base_check.py`)

```python
class BaseCheck:
    name = ''           # override in subclass
    severity = 'error'  # override in subclass

    def run(self, shot_node, config, platform_config, **kwargs):
        """Execute the check.

        Returns:
            CheckResult
        """
        raise NotImplementedError
```

---

## Individual Checks

### `checks/shot_nodes.py` — `CTXNodeHierarchyCheck`

**Severity:** error
**What it validates:**
- Shot node exists in scene
- Shot is connected to a sequence
- Sequence is connected to a manager
- All `assets[i]` connections resolve to valid CTX_Asset nodes (not dangling)
- Gaffer connection (if present) resolves to valid CTX_LightGaffer node

**Details dict keys:** `missing_connections`, `dangling_assets`, `node_name`

---

### `checks/asset_paths.py` — `AssetPathExistsCheck`

**Severity:** error
**What it validates:**
- For each CTX_Asset linked to the shot:
  - `get_file_path()` is not empty
  - The resolved path exists on disk (`os.path.exists`)
- For each CTX_Asset with a template:
  - Template has no unexpanded `$tokens`

**Details dict keys:** `missing_files`, `unresolved_tokens`, `asset_count`

---

### `checks/frame_range.py` — `FrameRangeCheck`

**Severity:** warning
**What it validates:**
- Shot node `get_frame_range()` returns (start, end)
- Maya timeline (`playbackOptions -q -min/max`) matches shot frame range
- Warns if they differ (does not auto-fix)

**Details dict keys:** `shot_range`, `maya_range`

**Notes:**
- Only runs if `MAYA_AVAILABLE` is True
- In headless mode, returns `passed=True` with `info` severity noting it was skipped

---

### `checks/renderer.py` — `RendererMatchCheck`

**Severity:** warning
**What it validates:**
- Detects active renderer via `get_active_renderer()` (Stream E)
- For each CTX_Asset, checks that asset file extension is supported by active renderer
  - e.g. `.rs` files are only valid for Redshift
  - e.g. `.ass` files are only valid for Arnold
- Warns if mismatch found (e.g. `.rs` proxy while Arnold is active)

**Details dict keys:** `active_renderer`, `mismatched_assets`

**Notes:**
- Only runs if `MAYA_AVAILABLE` is True
- Falls back gracefully if renderer detection fails

---

### `checks/gaffer.py` — `GafferChainCheck`

**Severity:** warning
**What it validates:**
- Gaffer `parentGaffer` chain has no cycles (walk until no parent, max 10 hops)
- All `CTX_LightContext` nodes inside each gaffer have a valid target light
  - Target light shape exists in scene
  - Target is actually a light type
- No CTX_LightContext nodes are orphaned (exist in scene but connected to no gaffer)

**Details dict keys:** `cycles_found`, `orphaned_contexts`, `invalid_targets`

---

### `checks/namespace.py` — `NamespaceConflictCheck`

**Severity:** error
**What it validates:**
- No two CTX_Asset nodes on the same shot share the same namespace string
- Each namespace in the CTX_Asset list corresponds to at most one Maya namespace

**Details dict keys:** `conflicting_namespaces`

---

## `SceneValidator` Class (in `core/validator/__init__.py`)

```python
class SceneValidator:
    def __init__(self, config, platform_config=None):
        self.config = config
        self.platform_config = platform_config
        self._checks = [
            CTXNodeHierarchyCheck(),
            AssetPathExistsCheck(),
            FrameRangeCheck(),
            RendererMatchCheck(),
            GafferChainCheck(),
            NamespaceConflictCheck(),
        ]

    def validate_shot(self, shot_node):
        """Run all checks for a single shot.

        Args:
            shot_node: CTXShotNode instance or node name string

        Returns:
            ValidatorReport
        """

    def validate_shot_by_code(self, ep, seq, shot):
        """Convenience: find shot node by codes then validate."""

    def add_check(self, check):
        """Register a custom check (extensibility hook)."""

    def remove_check(self, check_name):
        """Deregister a check by name."""
```

---

## Usage Examples

**From Maya UI (future button in Context Manager):**
```python
validator = SceneValidator(config, platform_config)
report = validator.validate_shot(shot_node)
if not report.passed():
    for result in report.errors():
        logger.error('[%s] %s', result.check_name, result.message)
```

**From CLI (Stream A):**
```bash
python -m tools.cli validate --ep Ep04 --seq sq0070 --shot SH0170
```
Exits with code 0 if passed, 1 if any errors.

**From farm pre-render hook:**
```python
from core.validator import SceneValidator
from config.project_config import ProjectConfig
config = ProjectConfig('project_configs/ctx_config.json')
validator = SceneValidator(config)
report = validator.validate_shot_by_code('Ep04', 'sq0070', 'SH0170')
if not report.passed():
    raise RuntimeError('Scene validation failed:\n' + report.to_text())
```

---

## Tests

File: `tests/test_scene_validator.py`

- `test_hierarchy_check_passes_valid_scene` — wired nodes pass
- `test_hierarchy_check_fails_missing_sequence` — detects dangling shot
- `test_hierarchy_check_fails_dangling_asset` — detects broken asset connection
- `test_asset_path_check_passes_existing_files` — all paths exist
- `test_asset_path_check_fails_missing_file` — detects missing file on disk
- `test_asset_path_check_fails_unresolved_token` — detects `$token` in path
- `test_frame_range_check_skipped_headless` — skipped when no Maya
- `test_renderer_check_skipped_headless` — skipped when no Maya
- `test_gaffer_check_passes_valid_chain` — clean chain passes
- `test_gaffer_check_fails_orphaned_context` — detects orphan
- `test_namespace_check_fails_duplicate` — detects duplicate namespace
- `test_full_report_to_dict` — JSON-serializable output
- `test_full_report_to_text` — human-readable output
- `test_custom_check_registration` — add_check() is callable
- `test_report_passed_property` — True when no errors

---

## Completion Criteria

- [ ] `core/validator/` package created with all files
- [ ] All 6 checks implemented
- [ ] `SceneValidator.validate_shot()` works without Maya (headless)
- [ ] `SceneValidator.validate_shot()` works with Maya (skipped checks pass safely)
- [ ] `ValidatorReport.to_dict()` produces valid JSON
- [ ] `ValidatorReport.to_text()` produces readable summary
- [ ] All tests pass
- [ ] No regressions in existing test suite
