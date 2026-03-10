# Stream C — Structured Logging

**Status:** Complete
**Priority:** P2 — Do first (enables debugging in all other streams)
**Branch:** `feature/phase4-production-automation`

---

## Goal

Replace all `print()` statements with Python `logging` module. Provide a single
configuration point that routes log output correctly in both Maya mode (Script
Editor / Output Window) and headless mode (stderr / file).

---

## Background

- `core/asset_scanner.py` already uses `logging.getLogger(__name__)` — this is
  the target pattern for all modules.
- All other modules use `print()` directly, making it impossible to filter,
  redirect, or suppress output programmatically.
- Farm scripts running headlessly have no Maya Script Editor, so a Maya-specific
  handler must be optional.

---

## Deliverables

### 1. `core/logging_config.py` (NEW)

```python
import logging
import logging.handlers

MAYA_HANDLER_NAME = 'maya_output'
DEFAULT_FORMAT = '%(name)s [%(levelname)s] %(message)s'
VERBOSE_FORMAT  = '%(asctime)s %(name)s [%(levelname)s] %(message)s'

def setup_logging(level='INFO', log_file=None, maya_mode=True, verbose=False):
    """Configure root logger for CTX Tools.

    Args:
        level (str): Logging level name ('DEBUG', 'INFO', 'WARNING', 'ERROR').
        log_file (str|None): Optional path to write log file.
        maya_mode (bool): If True, route INFO/WARNING/ERROR to Maya display.
        verbose (bool): If True, use VERBOSE_FORMAT with timestamps.
    """

def get_logger(name):
    """Return a logger under the 'ctx_tools' namespace."""
    return logging.getLogger('ctx_tools.' + name)
```

### 2. Maya output handler (inside `logging_config.py`)

Routes to `maya.OpenMaya.MGlobal.displayInfo/Warning/Error`.
Only registered when `maya_mode=True` AND Maya is importable.
Gracefully skips if Maya not available (headless mode).

### 3. File handler (inside `logging_config.py`)

Optional. Activated when `log_file` path is given.
Uses `RotatingFileHandler` (max 5 MB, 3 backups).

### 4. Config-driven log level (in `project_configs/ctx_config.json`)

Add section:
```json
"logging": {
    "level": "INFO",
    "file": null,
    "verbose": false
}
```

`ProjectConfig.get_logging_config()` returns this dict.
`tools/maya_menu.py` calls `setup_logging(**config.get_logging_config())` at startup.

### 5. Replace `print()` across all modules

Modules to update (in priority order):

| Module | Current State | Action |
|--------|---------------|--------|
| `core/asset_scanner.py` | Already uses logger | Ensure namespace is `ctx_tools.*` |
| `core/nodes.py` | Mixed print/logger | Replace all print |
| `core/gaffer/manager.py` | print + some logger | Replace all print |
| `core/gaffer/light_ops.py` | print statements | Replace all print |
| `core/gaffer/resolver.py` | print statements | Replace all print |
| `core/renderers/__init__.py` | print statements | Replace all print |
| `core/renderers/redshift.py` | print statements | Replace all print |
| `core/renderers/arnold.py` | print statements | Replace all print |
| `tools/base_manager.py` | print statements | Replace all print |
| `tools/maya_menu.py` | print statements | Replace all print |
| `ui/gaffer_manager_dialog.py` | print statements | Replace all print |
| `ui/asset_manager_dialog.py` | print statements | Replace all print |
| `config/project_config.py` | print statements | Replace all print |

Pattern for each module top:
```python
from core.logging_config import get_logger
logger = get_logger(__name__)
```

Replace:
```python
# Before
print("CTX Tools: Added {} to Python path".format(path))

# After
logger.info("CTX Tools: Added %s to Python path", path)
```

---

## Rules

- Use `%`-style formatting in log calls (NOT f-strings) — logging defers
  string interpolation until the message is actually emitted.
- `logger.debug()` — internal detail (loop iterations, attribute values)
- `logger.info()` — operations completing normally
- `logger.warning()` — recoverable unexpected state
- `logger.error()` — operation failed, impact to user
- `logger.exception()` — inside except blocks (auto-attaches traceback)
- Keep existing `print()` in `userSetup.py` — that is outside the tool module.

---

## Tests

File: `tests/test_logging_config.py`

- `test_setup_logging_headless` — configure without Maya, no error
- `test_setup_logging_level` — DEBUG level passes DEBUG messages
- `test_setup_logging_file` — log_file creates file and writes
- `test_get_logger_namespace` — logger name has `ctx_tools.` prefix
- `test_no_print_in_core` — grep test: assert no `print(` in `core/*.py`
- `test_no_print_in_tools` — grep test: assert no `print(` in `tools/*.py`

---

## Completion Criteria

- [x] `core/logging_config.py` created
- [x] `project_configs/ctx_config.json` has `logging` section
- [x] `ProjectConfig.get_logging_config()` method added
- [x] `tools/maya_menu.py` calls `setup_logging()` on startup
- [x] All listed modules have `print()` replaced with `logger.*`
- [x] All new tests pass
- [x] No regressions in existing test suite
