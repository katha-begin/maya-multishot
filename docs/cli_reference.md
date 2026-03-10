# CTX Tools — CLI Reference

Command-line interface for the Maya Multishot Pipeline.
Runs without Maya UI for use in farm scripts, CI pipelines, and batch operations.

```
python tools/cli.py [GLOBAL FLAGS] <command> [COMMAND FLAGS]
```

---

## Global Flags

These flags must be placed **before** the command name.

| Flag | Default | Description |
|------|---------|-------------|
| `--config PATH` | `project_configs/ctx_config.json` | Path to `ctx_config.json`. Also reads `CTX_CONFIG` env var. |
| `--log-level LEVEL` | `INFO` | Verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `--json` | off | Output results as JSON instead of human-readable text |
| `--help` | — | Show help and exit |

---

## Commands

### `scan-assets`

Scan the filesystem for published assets for a shot.
**Does not require Maya.**

```
python tools/cli.py scan-assets --ep EP --seq SEQ --shot SHOT [--dept DEPT]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--ep EP` | yes | Episode code, e.g. `Ep04` |
| `--seq SEQ` | yes | Sequence code, e.g. `sq0070` |
| `--shot SHOT` | yes | Shot code, e.g. `SH0170` |
| `--dept DEPT` | no | Comma-separated department list, e.g. `lighting,fx`. Default: all from config. |

**Exit codes:** `0` always (discovery warnings do not fail).

**Example — human-readable:**
```
python tools/cli.py scan-assets --ep Ep04 --seq sq0070 --shot SH0170
```
```
Found 3 assets for Ep04_sq0070_SH0170:
  CHAR    CatStompie            001     lighting    v003   V:/SWA/all/scene/...
  PROP    Chair                 001     anim        v002   V:/SWA/all/scene/...
  CAM     SWA_Ep04_SH0170_cam   001     lighting    v001   V:/SWA/all/scene/...
```

**Example — JSON output:**
```
python tools/cli.py --json scan-assets --ep Ep04 --seq sq0070 --shot SH0170
```
```json
[
  {
    "type": "CHAR",
    "name": "CatStompie",
    "variant": "001",
    "dept": "lighting",
    "version": "v003",
    "file_path": "V:/SWA/all/scene/Ep04/sq0070/SH0170/lighting/publish/v003/...",
    "ext": "abc"
  }
]
```

**Example — filter by department:**
```
python tools/cli.py scan-assets --ep Ep04 --seq sq0070 --shot SH0170 --dept lighting,fx
```

---

### `set-active-shot`

Set a shot as the active shot in a Maya scene.
Equivalent to clicking **Set** in the Context Manager UI:
marks the shot active, updates asset file paths, and applies the gaffer chain.
**Requires Maya.**

```
python tools/cli.py set-active-shot --ep EP --seq SEQ --shot SHOT [OPTIONS]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--ep EP` | yes | Episode code |
| `--seq SEQ` | yes | Sequence code |
| `--shot SHOT` | yes | Shot code |
| `--scene FILE` | no | Scene file to open first. Omit if already inside Maya. |
| `--no-save` | no | Do not save the scene after applying |
| `--no-paths` | no | Skip asset path updates |
| `--no-gaffer` | no | Skip gaffer chain application |

**Exit codes:** `0` success, `1` failure.

**Example — full shot switch:**
```
python tools/cli.py set-active-shot --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170
```
```
[OK] Active shot set: Ep04_sq0070_SH0170
  Assets updated : 5
  Gaffer applied : True
  Saved          : file.ma
```

**Example — paths only, skip gaffer:**
```
python tools/cli.py set-active-shot --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170 --no-gaffer
```

**Example — dry run (no save):**
```
python tools/cli.py set-active-shot --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170 --no-save
```

**Example — JSON output:**
```
python tools/cli.py --json set-active-shot --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170
```
```json
{
  "success": true,
  "message": "Active shot set: Ep04_sq0070_SH0170",
  "output_file": "file.ma",
  "assets_updated": 5,
  "gaffer_applied": true
}
```

---

### `apply-shot`

Open a scene and update asset file paths for a shot, without changing the active
shot flag or applying gaffer. Use `set-active-shot` for a full shot switch.
**Requires Maya.**

```
python tools/cli.py apply-shot --scene FILE --ep EP --seq SEQ --shot SHOT [--no-save]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--scene FILE` | yes | Scene file to open |
| `--ep EP` | yes | Episode code |
| `--seq SEQ` | yes | Sequence code |
| `--shot SHOT` | yes | Shot code |
| `--no-save` | no | Do not save after applying |

**Exit codes:** `0` success, `1` failure.

**Example:**
```
python tools/cli.py apply-shot --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170
```
```
[OK] Shot applied: Ep04_sq0070_SH0170
Saved: file.ma
```

---

### `validate`

Run the scene validator against a Maya scene file.
Reports on node hierarchy, asset paths, frame range, renderer match,
gaffer chain integrity, and namespace conflicts.
**Requires Maya.**

```
python tools/cli.py validate --scene FILE --ep EP --seq SEQ --shot SHOT
```

| Flag | Required | Description |
|------|----------|-------------|
| `--scene FILE` | yes | Scene file to open |
| `--ep EP` | yes | Episode code |
| `--seq SEQ` | yes | Sequence code |
| `--shot SHOT` | yes | Shot code |

**Exit codes:** `0` all checks passed, `1` one or more errors found.

**Example — human-readable:**
```
python tools/cli.py validate --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170
```
```
Validator Report: Ep04_sq0070_SH0170
Overall: PASSED
------------------------------------------------------------
[OK]    ctx_node_hierarchy: Node hierarchy intact
[OK]    asset_paths: All 5 asset paths exist on disk
[WARN]  frame_range: Maya timeline (1001-1100) does not match shot range (1001-1080)
[OK]    renderer_match: All asset formats match active renderer (redshift)
[OK]    gaffer_chain: Gaffer chain valid, no orphaned contexts
[OK]    namespace_conflict: No duplicate namespaces
```

**Example — JSON output (for farm scripts):**
```
python tools/cli.py --json validate --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170
```
```json
{
  "shot_id": "Ep04_sq0070_SH0170",
  "passed": true,
  "results": [
    {"check_name": "ctx_node_hierarchy", "passed": true, "severity": "error", "message": "Node hierarchy intact", "details": {}},
    ...
  ]
}
```

---

### `export-gaffer`

Export the gaffer chain for a shot to a JSON file.
**Requires Maya.**

```
python tools/cli.py export-gaffer --ep EP --seq SEQ --shot SHOT --out PATH [--scene FILE]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--ep EP` | yes | Episode code |
| `--seq SEQ` | yes | Sequence code |
| `--shot SHOT` | yes | Shot code |
| `--out PATH` | yes | Output `.json` file path |
| `--scene FILE` | no | Scene file to open first. Omit if already inside Maya. |

**Exit codes:** `0` success, `1` failure.

**Example:**
```
python tools/cli.py export-gaffer --ep Ep04 --seq sq0070 --shot SH0170 --out gaffer.json
```
```
[OK] Exported 4 lights to gaffer.json
```

---

### `import-gaffer`

Load a gaffer JSON file and apply it to a shot in a scene.
**Requires Maya.**

```
python tools/cli.py import-gaffer --scene FILE --ep EP --seq SEQ --shot SHOT --json-file PATH [--no-save]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--scene FILE` | yes | Scene file to open |
| `--ep EP` | yes | Episode code |
| `--seq SEQ` | yes | Sequence code |
| `--shot SHOT` | yes | Shot code |
| `--json-file PATH` | yes | Path to gaffer `.json` file |
| `--no-save` | no | Do not save after import |

**Exit codes:** `0` success, `1` failure.

**Example:**
```
python tools/cli.py import-gaffer --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170 --json-file gaffer.json
```
```
[OK] Imported 4 lights
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CTX_CONFIG` | Path to `ctx_config.json`. Overridden by `--config` flag. |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Logic or validation error (scene not found, missing asset, etc.) |
| `2` | Argument error — missing or invalid flag (handled by argparse) |

---

## Farm / Deadline Integration

Use `set-active-shot` as a pre-render step, or `validate` as a pre-render gate:

```python
import subprocess, sys, os

result = subprocess.run(
    [
        sys.executable, 'tools/cli.py', '--json', 'validate',
        '--scene', os.environ['SCENE_FILE'],
        '--ep',    os.environ['CTX_EP'],
        '--seq',   os.environ['CTX_SEQ'],
        '--shot',  os.environ['CTX_SHOT'],
    ],
    capture_output=True, text=True
)
if result.returncode != 0:
    raise RuntimeError('Scene validation failed:\n' + result.stdout)
```

Or as a Deadline pre-render script:

```python
# Deadline pre-render plugin script
import subprocess, sys

def __main__(*args):
    scene = deadlinePlugin.GetPluginInfoEntry('SceneFile')
    ep    = deadlinePlugin.GetPluginInfoEntry('CTX_EP')
    seq   = deadlinePlugin.GetPluginInfoEntry('CTX_SEQ')
    shot  = deadlinePlugin.GetPluginInfoEntry('CTX_SHOT')

    r = subprocess.run(
        [sys.executable, 'tools/cli.py', 'set-active-shot',
         '--scene', scene, '--ep', ep, '--seq', seq, '--shot', shot,
         '--no-save'],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        raise RuntimeError('set-active-shot failed: ' + r.stdout + r.stderr)
```
