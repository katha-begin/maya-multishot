# -*- coding: utf-8 -*-
"""CTX Tools command-line interface.

Provides argparse-based commands for operating on the CTX pipeline from
scripts, farm render hooks, and CI pipelines without requiring Maya UI.

Usage::

    python tools/cli.py --help
    python tools/cli.py scan-assets --ep Ep04 --seq sq0070 --shot SH0170
    python tools/cli.py scan-assets --ep Ep04 --seq sq0070 --shot SH0170 --json
    python tools/cli.py validate --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170
    python tools/cli.py apply-shot --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170
    python tools/cli.py set-active-shot --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170
    python tools/cli.py set-active-shot --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170 --no-gaffer
    python tools/cli.py export-gaffer --ep Ep04 --seq sq0070 --shot SH0170 --out gaffer.json
    python tools/cli.py import-gaffer --scene file.ma --ep Ep04 --seq sq0070 --shot SH0170 --json-file gaffer.json

Exit codes:
    0 -- success
    1 -- logic / validation error
    2 -- argument error (handled by argparse)
"""

from __future__ import absolute_import, division, print_function

import argparse
import json
import sys


# ---------------------------------------------------------------------------
# Argument parser construction
# ---------------------------------------------------------------------------

def build_parser():
    """Build and return the top-level ArgumentParser.

    Returns:
        argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog='ctx-tools',
        description='CTX Tools -- Maya Multishot Pipeline CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global flags
    parser.add_argument(
        '--config',
        metavar='PATH',
        default=None,
        help='Path to ctx_config.json (also: CTX_CONFIG env var)',
    )
    parser.add_argument(
        '--log-level',
        metavar='LEVEL',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging verbosity (default: INFO)',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        default=False,
        help='Output results as JSON',
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

    # ------------------------------------------------------------------ #
    # scan-assets
    # ------------------------------------------------------------------ #
    p_scan = subparsers.add_parser(
        'scan-assets',
        help='Scan filesystem for published assets for a shot (no Maya required)',
    )
    p_scan.add_argument('--ep',   required=True, help='Episode code, e.g. Ep04')
    p_scan.add_argument('--seq',  required=True, help='Sequence code, e.g. sq0070')
    p_scan.add_argument('--shot', required=True, help='Shot code, e.g. SH0170')
    p_scan.add_argument(
        '--dept',
        metavar='DEPT[,DEPT...]',
        default=None,
        help='Comma-separated department list (default: all from config)',
    )

    # ------------------------------------------------------------------ #
    # validate
    # ------------------------------------------------------------------ #
    p_val = subparsers.add_parser(
        'validate',
        help='Run scene validator against a Maya scene file (requires Maya)',
    )
    p_val.add_argument('--scene', required=True, metavar='FILE', help='Path to .ma/.mb scene file')
    p_val.add_argument('--ep',    required=True, help='Episode code')
    p_val.add_argument('--seq',   required=True, help='Sequence code')
    p_val.add_argument('--shot',  required=True, help='Shot code')

    # ------------------------------------------------------------------ #
    # apply-shot
    # ------------------------------------------------------------------ #
    p_apply = subparsers.add_parser(
        'apply-shot',
        help='Open a scene, apply the specified shot context, optionally save',
    )
    p_apply.add_argument('--scene', required=True, metavar='FILE', help='Path to .ma/.mb scene file')
    p_apply.add_argument('--ep',    required=True, help='Episode code')
    p_apply.add_argument('--seq',   required=True, help='Sequence code')
    p_apply.add_argument('--shot',  required=True, help='Shot code')
    p_apply.add_argument(
        '--no-save',
        action='store_true',
        default=False,
        help='Do not save the scene after applying',
    )

    # ------------------------------------------------------------------ #
    # set-active-shot
    # ------------------------------------------------------------------ #
    p_set = subparsers.add_parser(
        'set-active-shot',
        help='Mark a shot as active, update asset paths, and apply gaffer (requires Maya)',
    )
    p_set.add_argument('--scene', default=None, metavar='FILE',
                       help='Optional scene file to open first')
    p_set.add_argument('--ep',   required=True, help='Episode code')
    p_set.add_argument('--seq',  required=True, help='Sequence code')
    p_set.add_argument('--shot', required=True, help='Shot code')
    p_set.add_argument('--no-save',         action='store_true', default=False,
                       help='Do not save the scene after applying')
    p_set.add_argument('--no-paths',        action='store_true', default=False,
                       help='Skip asset path updates')
    p_set.add_argument('--no-gaffer',       action='store_true', default=False,
                       help='Skip gaffer chain application')

    # ------------------------------------------------------------------ #
    # export-gaffer
    # ------------------------------------------------------------------ #
    p_exp = subparsers.add_parser(
        'export-gaffer',
        help='Export gaffer chain for a shot to a JSON file',
    )
    p_exp.add_argument('--ep',    required=True, help='Episode code')
    p_exp.add_argument('--seq',   required=True, help='Sequence code')
    p_exp.add_argument('--shot',  required=True, help='Shot code')
    p_exp.add_argument('--out',   required=True, metavar='PATH', help='Output .json path')
    p_exp.add_argument(
        '--scene',
        default=None,
        metavar='FILE',
        help='Optional scene file to open first',
    )

    # ------------------------------------------------------------------ #
    # import-gaffer
    # ------------------------------------------------------------------ #
    p_imp = subparsers.add_parser(
        'import-gaffer',
        help='Load a gaffer JSON file and apply it to a shot in a scene',
    )
    p_imp.add_argument('--scene',     required=True, metavar='FILE', help='Path to .ma/.mb scene file')
    p_imp.add_argument('--ep',        required=True, help='Episode code')
    p_imp.add_argument('--seq',       required=True, help='Sequence code')
    p_imp.add_argument('--shot',      required=True, help='Shot code')
    p_imp.add_argument(
        '--json-file',
        required=True,
        dest='json_file',
        metavar='PATH',
        help='Path to gaffer .json file',
    )
    p_imp.add_argument(
        '--no-save',
        action='store_true',
        default=False,
        help='Do not save the scene after import',
    )

    # ------------------------------------------------------------------ #
    # batch-render
    # ------------------------------------------------------------------ #
    p_batch = subparsers.add_parser('batch-render', help='Render multiple shots in batch')
    p_batch.add_argument('--scene', metavar='FILE', help='Scene file (.ma/.mb)')
    p_batch.add_argument('--shots', nargs='+', metavar='SHOT',
                         help='Shot IDs as ep_seq_shot (e.g. Ep04_sq0070_SH0170)')
    p_batch.add_argument('--all-shots', action='store_true',
                         help='Use all CTX shots in scene')
    p_batch.add_argument('--layers', nargs='+', metavar='LAYER',
                         help='Render layers (default: all renderable)')
    p_batch.add_argument('--start-frame', type=int, metavar='N',
                         help='Override start frame')
    p_batch.add_argument('--end-frame', type=int, metavar='N',
                         help='Override end frame')
    p_batch.add_argument('--reserve-gpus', type=int, metavar='N',
                         help='Number of GPUs to reserve for interactive use')
    p_batch.add_argument('--dry-run', action='store_true',
                         help='Prepare scenes but do not render')
    p_batch.add_argument('--no-save', action='store_true',
                         help='Do not save temp scenes after render')
    p_batch.add_argument(
        '--use-slate-layers',
        action='store_true',
        default=False,
        help="Resolve render layers from each shot's slate instead of --layers.",
    )

    return parser


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _cmd_scan_assets(args, api):
    """Handle the scan-assets command.

    Args:
        args: Parsed argparse namespace.
        api: PipelineAPI instance.

    Returns:
        int: Exit code (always 0 for discovery).
    """
    departments = None
    if args.dept:
        departments = [d.strip() for d in args.dept.split(',') if d.strip()]

    assets = api.scan_assets(args.ep, args.seq, args.shot, departments=departments)

    if args.json:
        print(json.dumps(assets, indent=2))
    else:
        shot_id = '%s_%s_%s' % (args.ep, args.seq, args.shot)
        print('Found %d assets for %s:' % (len(assets), shot_id))
        for a in assets:
            print('  %-6s  %-20s  %-6s  %-10s  %-6s  %s' % (
                a.get('type', ''),
                a.get('name', ''),
                a.get('variant', ''),
                a.get('dept', ''),
                a.get('version', ''),
                a.get('file_path', ''),
            ))

    return 0


def _cmd_validate(args, api):
    """Handle the validate command.

    Args:
        args: Parsed argparse namespace.
        api: PipelineAPI instance.

    Returns:
        int: 0 if passed, 1 if any errors found.
    """
    try:
        report = api.validate_scene(args.scene, args.ep, args.seq, args.shot)
    except RuntimeError as exc:
        if args.json:
            print(json.dumps({'error': str(exc)}))
        else:
            print('ERROR: %s' % exc)
        return 1

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(report.to_text())

    return 0 if report.passed() else 1


def _cmd_apply_shot(args, api):
    """Handle the apply-shot command.

    Args:
        args: Parsed argparse namespace.
        api: PipelineAPI instance.

    Returns:
        int: 0 on success, 1 on failure.
    """
    try:
        result = api.apply_shot(
            args.scene, args.ep, args.seq, args.shot,
            save=not args.no_save,
        )
    except RuntimeError as exc:
        if args.json:
            print(json.dumps({'success': False, 'message': str(exc), 'output_file': None}))
        else:
            print('ERROR: %s' % exc)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = 'OK' if result.get('success') else 'FAILED'
        print('[%s] %s' % (status, result.get('message', '')))
        if result.get('output_file'):
            print('Saved: %s' % result['output_file'])

    return 0 if result.get('success') else 1


def _cmd_set_active_shot(args, api):
    """Handle the set-active-shot command.

    Args:
        args: Parsed argparse namespace.
        api: PipelineAPI instance.

    Returns:
        int: 0 on success, 1 on failure.
    """
    try:
        result = api.set_active_shot(
            args.ep, args.seq, args.shot,
            scene_file=args.scene,
            save=not args.no_save,
            apply_paths=not args.no_paths,
            apply_gaffer=not args.no_gaffer,
        )
    except RuntimeError as exc:
        if args.json:
            print(json.dumps({'success': False, 'message': str(exc)}))
        else:
            print('ERROR: %s' % exc)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = 'OK' if result.get('success') else 'FAILED'
        print('[%s] %s' % (status, result.get('message', '')))
        if result.get('success'):
            print('  Assets updated : %d' % result.get('assets_updated', 0))
            print('  Gaffer applied : %s' % result.get('gaffer_applied', False))
            if result.get('output_file'):
                print('  Saved          : %s' % result['output_file'])

    return 0 if result.get('success') else 1


def _cmd_export_gaffer(args, api):
    """Handle the export-gaffer command.

    Args:
        args: Parsed argparse namespace.
        api: PipelineAPI instance.

    Returns:
        int: 0 on success, 1 on failure.
    """
    try:
        result = api.export_gaffer(
            args.ep, args.seq, args.shot,
            args.out,
            scene_file=args.scene,
        )
    except RuntimeError as exc:
        if args.json:
            print(json.dumps({'success': False, 'message': str(exc), 'lights_exported': 0}))
        else:
            print('ERROR: %s' % exc)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = 'OK' if result.get('success') else 'FAILED'
        print('[%s] %s' % (status, result.get('message', '')))

    return 0 if result.get('success') else 1


def _cmd_import_gaffer(args, api):
    """Handle the import-gaffer command.

    Args:
        args: Parsed argparse namespace.
        api: PipelineAPI instance.

    Returns:
        int: 0 on success, 1 on failure.
    """
    try:
        result = api.import_gaffer(
            args.ep, args.seq, args.shot,
            args.json_file,
            scene_file=args.scene,
            save=not args.no_save,
        )
    except RuntimeError as exc:
        if args.json:
            print(json.dumps({'success': False, 'message': str(exc), 'lights_imported': 0}))
        else:
            print('ERROR: %s' % exc)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = 'OK' if result.get('success') else 'FAILED'
        print('[%s] %s' % (status, result.get('message', '')))

    return 0 if result.get('success') else 1


def _cmd_batch_render(args, api, output):
    """Handle batch-render command.

    Args:
        args: Parsed argparse namespace.
        api: PipelineAPI instance.
        output (callable): Called with result dict.

    Returns:
        int: 0 on success, 1 on failure.
    """
    shots = []

    if getattr(args, 'all_shots', False):
        # Discover shots from CTXShotNode.list_all() -- requires Maya
        try:
            from core.nodes.wrappers import CTXShotNode
            shot_nodes = CTXShotNode.list_all()
            for sn in shot_nodes:
                shots.append({'ep': sn.ep, 'seq': sn.seq, 'shot': sn.shot})
        except Exception as exc:
            output({'success': False, 'error': 'Failed to list shots: %s' % exc})
            return 1
    elif getattr(args, 'shots', None):
        for shot_str in args.shots:
            parts = shot_str.split('_', 2)
            if len(parts) != 3:
                output({'success': False,
                        'error': 'Invalid shot ID %r (expected ep_seq_shot)' % shot_str})
                return 1
            shots.append({'ep': parts[0], 'seq': parts[1], 'shot': parts[2]})
    else:
        output({'success': False, 'error': '--shots or --all-shots required'})
        return 1

    if getattr(args, 'use_slate_layers', False):
        render_layers = None  # ScenePreparer will resolve from slate
    elif getattr(args, 'layers', None):
        render_layers = args.layers
    else:
        render_layers = None

    result = api.batch_render(
        shots=shots,
        scene_file=getattr(args, 'scene', None),
        render_layers=render_layers,
        start_frame=getattr(args, 'start_frame', None),
        end_frame=getattr(args, 'end_frame', None),
        dry_run=getattr(args, 'dry_run', False),
        reserved_gpus=getattr(args, 'reserve_gpus', None),
    )
    output(result)
    return 0 if result.get('success') else 1


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv=None):
    """Parse arguments and dispatch to the appropriate command handler.

    Args:
        argv (list|None): Argument list. None means sys.argv[1:].

    Returns:
        int: Exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Configure logging
    from core.logging_config import setup_logging
    setup_logging(level=args.log_level, maya_mode=False)

    # Build API instance
    from tools.pipeline_api import PipelineAPI
    api = PipelineAPI(config_path=args.config)

    # Output helper used by commands that accept an output callable
    def _output(result):
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            success = result.get('success', False)
            status = 'OK' if success else 'FAILED'
            error = result.get('error') or result.get('message', '')
            total = result.get('total', 0)
            done = result.get('done', 0)
            failed = result.get('failed', 0)
            print('[%s] total=%d done=%d failed=%d%s' % (
                status, total, done, failed,
                (' -- ' + error if error and not success else ''),
            ))

    # Dispatch
    command = args.command
    if command == 'scan-assets':
        return _cmd_scan_assets(args, api)
    elif command == 'validate':
        return _cmd_validate(args, api)
    elif command == 'apply-shot':
        return _cmd_apply_shot(args, api)
    elif command == 'set-active-shot':
        return _cmd_set_active_shot(args, api)
    elif command == 'export-gaffer':
        return _cmd_export_gaffer(args, api)
    elif command == 'import-gaffer':
        return _cmd_import_gaffer(args, api)
    elif command == 'batch-render':
        sys.exit(_cmd_batch_render(args, api, _output))
    else:
        parser.error('Unknown command: %s' % command)
        return 2


if __name__ == '__main__':
    sys.exit(main())
