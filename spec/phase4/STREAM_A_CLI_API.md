# Stream A — CLI & Headless Pipeline API

**Status:** Not Started
**Priority:** P1 — Farm scripts cannot currently call the tool without knowing internals
**Branch:** `feature/phase4-production-automation`
**Dependencies:** Streams B, C, D, E should be done first

---

## Goal

Provide two entry points for non-UI access:

1. **`tools/pipeline_api.py`** — Python API for programmatic use from farm scripts,
   renderers, and other tools. No UI. No Maya UI dependency.
2. **`tools/cli.py`** — argparse command-line wrapper around `pipeline_api.py`.
   Run as `python -m tools.cli <command> [args]`.

---

## Design Decisions

- **argparse** (not click) — no new dependencies, matches project style.
- **Pipeline API first** — CLI is a thin wrapper; all logic lives in API.
- **Config file path** from CLI flag or `CTX_CONFIG` environment variable.
- **Exit codes:** 0 = success, 1 = validation/logic error, 2 = argument error.
- **Output format:** human-readable by default; `--json` flag for machine-readable.

---

## `tools/pipeline_api.py`

### Class `PipelineAPI`

```python
class PipelineAPI:
    def __init__(self, config_path=None, maya_standalone=False):
        """
        Args:
            config_path (str): Path to ctx_config.json.
                               Falls back to CTX_CONFIG env var, then
                               'project_configs/ctx_config.json'.
            maya_standalone (bool): If True, calls maya.standalone.initialize()
                                    before any Maya operation.
        """
```

#### Methods

```python
def scan_assets(self, ep, seq, shot, departments=None):
    """Scan filesystem for assets for a given shot.

    Does NOT require Maya. Pure filesystem operation.

    Args:
        ep (str): Episode code, e.g. 'Ep04'
        seq (str): Sequence code, e.g. 'sq0070'
        shot (str): Shot code, e.g. 'SH0170'
        departments (list|None): Departments to scan. None = all from config.

    Returns:
        list[dict]: Each dict has keys:
            type, name, variant, dept, version, file_path, ext
    """

def validate_scene(self, scene_file, ep, seq, shot):
    """Run scene validator on a Maya scene file.

    Requires Maya standalone.

    Args:
        scene_file (str): Path to .ma or .mb file.
        ep, seq, shot (str): Shot codes.

    Returns:
        ValidatorReport
    """

def apply_shot(self, scene_file, ep, seq, shot, save=True):
    """Open a scene file, apply the specified shot, optionally save.

    Requires Maya standalone.

    Args:
        scene_file (str): Path to .ma or .mb file.
        ep, seq, shot (str): Shot codes.
        save (bool): If True, save the scene after applying.

    Returns:
        dict: {'success': bool, 'message': str, 'output_file': str|None}
    """

def export_gaffer(self, ep, seq, shot, output_path, scene_file=None):
    """Export gaffer chain for a shot to JSON.

    If scene_file provided, opens it first. Otherwise operates on current scene
    (assumes running inside Maya).

    Args:
        ep, seq, shot (str): Shot codes.
        output_path (str): Path to write .json file.
        scene_file (str|None): Optional scene file to open first.

    Returns:
        dict: {'success': bool, 'message': str, 'lights_exported': int}
    """

def import_gaffer(self, ep, seq, shot, json_path, scene_file=None, save=True):
    """Load gaffer JSON and apply to shot in a scene.

    Args:
        ep, seq, shot (str): Shot codes.
        json_path (str): Path to gaffer .json file.
        scene_file (str|None): Optional scene file to open first.
        save (bool): If True, save the scene after import.

    Returns:
        dict: {'success': bool, 'message': str, 'lights_imported': int}
    """
```

### Internal Helpers

```python
def _get_config(self):
    """Load ProjectConfig from configured path."""

def _require_maya(self):
    """Assert MAYA_AVAILABLE; raise RuntimeError if not."""

def _open_scene(self, scene_file):
    """Open Maya scene file via cmds.file(). Requires _require_maya()."""

def _find_shot_node(self, ep, seq, shot):
    """Find CTXShotNode by codes. Raises ValueError if not found."""
```

---

## `tools/cli.py`

Entry point: `python -m tools.cli` (add `__main__` block).

### Commands

#### `scan-assets`

```
python -m tools.cli scan-assets --ep Ep04 --seq sq0070 --shot SH0170
python -m tools.cli scan-assets --ep Ep04 --seq sq0070 --shot SH0170 --dept lighting,fx
python -m tools.cli scan-assets --ep Ep04 --seq sq0070 --shot SH0170 --json
```

Output (default): table of discovered assets with dept/version/path.
Output (`--json`): JSON list.
Exit 0 always (discovery errors are warnings, not failures).

#### `validate`

```
python -m tools.cli validate --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170
python -m tools.cli validate --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170 --json
```

Output (default): pass/fail per check + summary.
Output (`--json`): `ValidatorReport.to_dict()`.
Exit 0 if passed, 1 if any errors.

#### `apply-shot`

```
python -m tools.cli apply-shot --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170
python -m tools.cli apply-shot --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170 --no-save
```

Requires Maya standalone.
Exit 0 if success, 1 if failed.

#### `export-gaffer`

```
python -m tools.cli export-gaffer --ep Ep04 --seq sq0070 --shot SH0170 --out gaffer.json
python -m tools.cli export-gaffer --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170 --out gaffer.json
```

Exit 0 if exported, 1 if failed.

#### `import-gaffer`

```
python -m tools.cli import-gaffer --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170 --json gaffer.json
python -m tools.cli import-gaffer --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170 --json gaffer.json --no-save
```

Exit 0 if imported, 1 if failed.

### Global Flags

```
--config PATH    Path to ctx_config.json (also: CTX_CONFIG env var)
--log-level LVL  DEBUG | INFO | WARNING | ERROR (default: INFO)
--json           Output as JSON
```

### CLI Structure

```python
# tools/cli.py

import argparse
import sys

def build_parser():
    parser = argparse.ArgumentParser(
        prog='ctx-tools',
        description='CTX Tools — Maya Multishot Pipeline CLI'
    )
    # global flags
    parser.add_argument('--config', help='Path to ctx_config.json')
    parser.add_argument('--log-level', default='INFO')
    parser.add_argument('--json', action='store_true')

    subparsers = parser.add_subparsers(dest='command', required=True)

    # scan-assets
    p_scan = subparsers.add_parser('scan-assets')
    p_scan.add_argument('--ep', required=True)
    p_scan.add_argument('--seq', required=True)
    p_scan.add_argument('--shot', required=True)
    p_scan.add_argument('--dept', help='Comma-separated dept list')

    # validate
    p_val = subparsers.add_parser('validate')
    p_val.add_argument('--scene', required=True)
    p_val.add_argument('--ep', required=True)
    p_val.add_argument('--seq', required=True)
    p_val.add_argument('--shot', required=True)

    # apply-shot
    p_apply = subparsers.add_parser('apply-shot')
    p_apply.add_argument('--scene', required=True)
    p_apply.add_argument('--ep', required=True)
    p_apply.add_argument('--seq', required=True)
    p_apply.add_argument('--shot', required=True)
    p_apply.add_argument('--no-save', action='store_true')

    # export-gaffer
    p_exp = subparsers.add_parser('export-gaffer')
    p_exp.add_argument('--ep', required=True)
    p_exp.add_argument('--seq', required=True)
    p_exp.add_argument('--shot', required=True)
    p_exp.add_argument('--out', required=True, help='Output .json path')
    p_exp.add_argument('--scene', help='Optional scene file to open')

    # import-gaffer
    p_imp = subparsers.add_parser('import-gaffer')
    p_imp.add_argument('--scene', required=True)
    p_imp.add_argument('--ep', required=True)
    p_imp.add_argument('--seq', required=True)
    p_imp.add_argument('--shot', required=True)
    p_imp.add_argument('--json-file', required=True, dest='json_file')
    p_imp.add_argument('--no-save', action='store_true')

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    # dispatch to command handlers
    ...


if __name__ == '__main__':
    sys.exit(main())
```

---

## Gaffer JSON Format

Used by `export_gaffer` / `import_gaffer`. Format:

```json
{
    "version": 1,
    "shot": "Ep04_sq0070_SH0170",
    "exported": "2026-03-10T14:30:00",
    "gaffers": [
        {
            "name": "MasterGaffer",
            "type": "master",
            "lights": [
                {
                    "light_name": "KeyLight",
                    "target_shape": "KeyLightShape",
                    "attributes": {
                        "intensity": {"value": 1.5, "enabled": true, "mode": "replace"},
                        "color":     {"value": [1.0, 0.95, 0.9], "enabled": true, "mode": "replace"},
                        "exposure":  {"value": 0.0, "enabled": false, "mode": "replace"}
                    }
                }
            ]
        }
    ]
}
```

> NOTE: `export_gaffer` and `import_gaffer` in Stream A depend on a gaffer
> serializer that may be developed as part of Stream A or as a separate sub-task.
> See `core/gaffer/serializer.py` (to be created).

### `core/gaffer/serializer.py` (new file)

```python
class GafferSerializer:
    def export_shot(self, shot_node, config):
        """Export all gaffers for a shot to a dict (JSON-serializable)."""

    def import_shot(self, shot_node, data, config):
        """Apply gaffer data dict to a shot."""

    def to_json(self, data, path):
        """Write dict to JSON file."""

    def from_json(self, path):
        """Read JSON file and return dict."""
```

---

## Farm Integration Notes

For Deadline / Tractor pre-render hooks:

```python
# Pre-render script (no Maya UI)
import subprocess, sys, os

result = subprocess.run(
    [
        sys.executable, '-m', 'tools.cli', 'validate',
        '--scene', os.environ['SCENE_FILE'],
        '--ep',   os.environ['EP'],
        '--seq',  os.environ['SEQ'],
        '--shot', os.environ['SHOT'],
        '--json'
    ],
    capture_output=True, text=True
)
if result.returncode != 0:
    raise RuntimeError('Scene validation failed:\n' + result.stdout)
```

---

## Tests

File: `tests/test_pipeline_api.py`

- `test_scan_assets_no_maya` — works without Maya, returns list
- `test_scan_assets_empty_shot` — returns empty list gracefully
- `test_scan_assets_dept_filter` — filters by --dept arg
- `test_validate_returns_report` — returns ValidatorReport
- `test_cli_scan_assets_help` — `--help` exits 0
- `test_cli_scan_assets_json_output` — `--json` flag produces valid JSON
- `test_cli_validate_exits_1_on_error` — exits 1 when errors found
- `test_cli_validate_exits_0_on_pass` — exits 0 when passed
- `test_cli_missing_required_arg` — exits 2 on missing arg
- `test_cli_unknown_command` — exits 2 on unknown command
- `test_gaffer_serializer_round_trip` — export then import produces same data
- `test_gaffer_serializer_to_json_file` — writes valid JSON file
- `test_gaffer_serializer_from_json_file` — reads file correctly

---

## Completion Criteria

- [ ] `tools/pipeline_api.py` created with all public methods
- [ ] `tools/cli.py` created with all 5 commands + global flags
- [ ] `core/gaffer/serializer.py` created with export/import
- [ ] `python -m tools.cli --help` works without Maya
- [ ] `python -m tools.cli scan-assets ...` works without Maya
- [ ] `python -m tools.cli validate ...` runs validators and exits correctly
- [ ] `--json` flag produces valid JSON on all commands
- [ ] All tests pass
- [ ] No regressions in existing test suite
