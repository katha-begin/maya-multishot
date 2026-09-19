# -*- coding: utf-8 -*-
"""Asset type naming and discovery policy.

Single source of truth for the questions that differ per asset type:

    - How is the asset part of a publish name parsed into
      (type, name, variant)?
    - Is the publish a single file, or a directory of per-frame files?
    - What Maya namespace does an instance of this type get?

Before this module these answers were spread across ``core/asset_scanner.py``
(twice), ``ui/asset_manager_dialog.py`` and ``core/asset_reconciler.py`` as
``if asset_type == 'CAM'`` branches.  Centralising them keeps discovery,
import, adopt and validation from drifting apart.

Deliberately excluded: building Maya nodes.  The Asset Manager already has one
context-menu handler per import kind, and a builder registry would be
speculative.

Policies may be overridden from project config via an ``assetTypePolicies``
section; the defaults below apply when config is absent or silent.

Usage:
    from core import asset_types

    info = asset_types.parse_publish_name(
        'Ep02_sq0210_SH1180__CFX_botgroomevelyn001_ass', is_dir=True)
    # {'type': 'CFX', 'name': 'botgroomevelyn', 'variant': '001',
    #  'ext': 'ass'}
"""

from __future__ import absolute_import, division, print_function

import os
import re


# --- publish shapes --------------------------------------------------------

PUBLISH_SHAPE_FILE = 'file'
PUBLISH_SHAPE_SEQUENCE_DIR = 'sequenceDir'

# --- parse modes -----------------------------------------------------------

PARSE_STANDARD = 'standard'                       # TYPE_Name_Variant
PARSE_CAMERA = 'camera'                           # detected by filename suffix
PARSE_NO_SEPARATOR_VARIANT = 'noSeparatorVariant'  # TYPE_NameVariant

# --- namespace modes -------------------------------------------------------

NS_TYPE_NAME_VARIANT = 'typeNameVariant'   # CHAR_CatStompie_001
NS_NAME_ONLY = 'nameOnly'                  # SWA_Ep04_SH0170_camera
NS_BASENAME = 'basename'                   # Ep02_..._CFX_botgroomSamS001

# --- shared defaults -------------------------------------------------------

DEFAULT_VARIANT = '001'
DEFAULT_VARIANT_PATTERN = r'(\d{3})$'
DEFAULT_FRAME_TOKEN = '####'
DEFAULT_STANDIN_SUFFIX = '_aiStandIn'
SHOT_ASSET_SEPARATOR = '__'

_DEFAULT_POLICY = {
    'parse': PARSE_STANDARD,
    'publishShape': PUBLISH_SHAPE_FILE,
    'namespace': NS_TYPE_NAME_VARIANT,
    'variantPattern': DEFAULT_VARIANT_PATTERN,
}

_DEFAULT_POLICIES = {
    'CAM': {
        'parse': PARSE_CAMERA,
        'publishShape': PUBLISH_SHAPE_FILE,
        'namespace': NS_NAME_ONLY,
    },
    'CFX': {
        'parse': PARSE_NO_SEPARATOR_VARIANT,
        'publishShape': PUBLISH_SHAPE_SEQUENCE_DIR,
        'namespace': NS_BASENAME,
        'variantPattern': DEFAULT_VARIANT_PATTERN,
    },
}

_DEFAULT_EXTENSIONS = ['abc', 'vdb', 'ass', 'rs', 'ma', 'mb']
_DEFAULT_CAMERA_SUFFIX = '_camera'

# The asset half of a publish name, and the camera form that carries only a name
_ASSET_NAME_TOKENS = '$ep_$seq_$shot__$assetType_$assetName_$variant.$ext'
_CAMERA_NAME_TOKENS = '$ep_$seq_$shot__$assetName.$ext'


# ---------------------------------------------------------------------------
# config access -- every reader tolerates config=None
# ---------------------------------------------------------------------------

def _config_call(config, method_name, default):
    """Call an optional config accessor, falling back to a default.

    Args:
        config: ProjectConfig instance or None.
        method_name (str): Accessor name.
        default: Value returned when config is absent or the call fails.

    Returns:
        The accessor's value, or default.
    """
    if config is None:
        return default
    method = getattr(config, method_name, None)
    if not callable(method):
        return default
    try:
        value = method()
    except Exception:
        return default
    return default if value is None else value


def get_policy(asset_type, config=None):
    """Get the merged policy for an asset type.

    Args:
        asset_type (str): Asset type code (e.g. 'CFX').
        config: Optional ProjectConfig instance.

    Returns:
        dict: Policy with all keys populated.
    """
    policy = dict(_DEFAULT_POLICY)
    policy.update(_DEFAULT_POLICIES.get(asset_type, {}))

    overrides = _config_call(config, 'get_asset_type_policies', {})
    if isinstance(overrides, dict):
        override = overrides.get(asset_type)
        if isinstance(override, dict):
            policy.update(override)

    return policy


def get_publish_shape(asset_type, config=None):
    """Return 'file' or 'sequenceDir' for an asset type."""
    return get_policy(asset_type, config)['publishShape']


def get_asset_path_template(asset_type, config=None):
    """Return the publish path template for an asset type.

    A camera publish carries neither type nor variant in its filename
    ('Ep20_sq0010_SH0030__SWA_Ep20_SH0030_camera.abc'), so a camera-parsed
    type gets the same template with those tokens dropped.

    Args:
        asset_type (str): Asset type code (e.g. 'CHAR').
        config: Optional ProjectConfig instance.

    Returns:
        str or None: Template, or None when the config carries no 'assetPath'.
    """
    getter = getattr(config, 'get_template', None)
    if not callable(getter):
        return None

    try:
        template = getter('assetPath')
    except Exception:
        return None

    if not template:
        return None

    if get_policy(asset_type, config)['parse'] == PARSE_CAMERA:
        return template.replace(_ASSET_NAME_TOKENS, _CAMERA_NAME_TOKENS)

    return template


def _get_extensions(config):
    exts = _config_call(config, 'get_extensions', _DEFAULT_EXTENSIONS)
    if not isinstance(exts, (list, tuple)):
        exts = _DEFAULT_EXTENSIONS
    return [str(e).lstrip('.') for e in exts if e]


def _get_camera_suffix(config):
    return _config_call(config, 'get_camera_file_suffix', _DEFAULT_CAMERA_SUFFIX)


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

def parse_asset_part(asset_part, config=None):
    """Parse the asset half of a publish name into type, name and variant.

    The asset half is what follows the '__' separator, e.g. the
    'CHAR_CatStompie_001' of 'Ep04_sq0070_SH0140__CHAR_CatStompie_001'.

    Camera assets are detected by filename suffix rather than by a type
    prefix, because their asset part carries no type code at all
    (e.g. 'SWA_Ep04_SH0170_camera').  That check therefore runs first.

    Args:
        asset_part (str): Asset half of a publish name.
        config: Optional ProjectConfig instance.

    Returns:
        dict: {'type', 'name', 'variant'}, or None if unparseable.
    """
    if not asset_part:
        return None

    # Camera: suffix-based, no type prefix present.
    cam_suffix = _get_camera_suffix(config)
    if cam_suffix and asset_part.endswith(cam_suffix):
        return {
            'type': 'CAM',
            'name': asset_part,
            'variant': DEFAULT_VARIANT,
        }

    segments = asset_part.split('_')
    asset_type = segments[0]
    if not asset_type:
        return None

    policy = get_policy(asset_type, config)
    mode = policy['parse']

    if mode == PARSE_NO_SEPARATOR_VARIANT:
        return _parse_no_separator_variant(asset_type, asset_part, policy)

    # A camera-parsed type without the camera suffix, e.g. CAM_shotCam_001,
    # falls through to the standard split -- the parse it always had.
    return _parse_standard(segments)


def _parse_standard(segments):
    """Parse TYPE_Name_Variant, where Name may itself contain underscores."""
    if len(segments) < 3:
        return None

    asset_type = segments[0]
    variant = segments[-1]
    name = '_'.join(segments[1:-1])

    if not asset_type or not name or not variant:
        return None

    return {'type': asset_type, 'name': name, 'variant': variant}


def _parse_no_separator_variant(asset_type, asset_part, policy):
    """Parse TYPE_NameVariant, e.g. CFX_botgroomSamS001.

    The variant is a trailing digit run with no separator before it.  A name
    genuinely ending in digits will mis-split; this is inherent to the
    convention and is documented in the design.  The pattern is
    config-driven so it can be tuned without a code change.
    """
    prefix = asset_type + '_'
    if not asset_part.startswith(prefix):
        return None

    remainder = asset_part[len(prefix):]
    if not remainder:
        return None

    match = re.search(policy.get('variantPattern', DEFAULT_VARIANT_PATTERN),
                      remainder)
    if not match:
        return None

    variant = match.group(1)
    name = remainder[:match.start()]
    if not name:
        return None

    return {'type': asset_type, 'name': name, 'variant': variant}


def parse_publish_name(entry_name, is_dir=False, config=None):
    """Parse a publish directory entry into asset metadata.

    Handles both publish shapes.  A file entry is only accepted for types
    whose shape is 'file', and a directory entry only for types whose shape
    is 'sequenceDir' -- so a stray '.ass' file will not masquerade as a CFX
    publish, and a CHAR file will not be mistaken for a sequence directory.

    Args:
        entry_name (str): Basename of the entry inside a version directory.
        is_dir (bool): True if the entry is a directory.
        config: Optional ProjectConfig instance.

    Returns:
        dict: {'type', 'name', 'variant', 'ext'}, or None if not an asset.
    """
    if not entry_name:
        return None

    if is_dir:
        return _parse_sequence_dir(entry_name, config)

    base, ext = os.path.splitext(entry_name)
    ext = ext.lstrip('.')
    if not ext:
        return None

    info = _parse_basename(base, config)
    if not info:
        return None

    if get_publish_shape(info['type'], config) != PUBLISH_SHAPE_FILE:
        return None

    info['ext'] = ext
    return info


def _parse_sequence_dir(dir_name, config):
    """Parse a '<basename>_<ext>' sequence directory name."""
    for ext in _get_extensions(config):
        suffix = '_' + ext
        if not dir_name.endswith(suffix):
            continue

        base = dir_name[:-len(suffix)]
        info = _parse_basename(base, config)
        if not info:
            continue

        if get_publish_shape(info['type'], config) != PUBLISH_SHAPE_SEQUENCE_DIR:
            continue

        info['ext'] = ext
        return info

    return None


def _parse_basename(base, config):
    """Split a publish basename on '__' and parse its asset half."""
    parts = base.split(SHOT_ASSET_SEPARATOR)
    if len(parts) != 2:
        return None
    return parse_asset_part(parts[1], config)


# ---------------------------------------------------------------------------
# construction
# ---------------------------------------------------------------------------

def build_asset_part(asset_type, asset_name, variant, config=None):
    """Build the asset half of a publish name for a type.

    Args:
        asset_type (str): Asset type code.
        asset_name (str): Asset name.
        variant (str): Variant code.
        config: Optional ProjectConfig instance.

    Returns:
        str: Asset part, e.g. 'CFX_botgroomSamS001' or 'CHAR_CatStompie_001'.
    """
    policy = get_policy(asset_type, config)

    if policy['parse'] == PARSE_CAMERA:
        return asset_name

    if policy['parse'] == PARSE_NO_SEPARATOR_VARIANT:
        return '{}_{}{}'.format(asset_type, asset_name, variant)

    return '{}_{}_{}'.format(asset_type, asset_name, variant)


def build_basename(ep, seq, shot, asset_type, asset_name, variant, config=None):
    """Build a full publish basename.

    Args:
        ep (str): Episode code.
        seq (str): Sequence code.
        shot (str): Shot code.
        asset_type (str): Asset type code.
        asset_name (str): Asset name.
        variant (str): Variant code.
        config: Optional ProjectConfig instance.

    Returns:
        str: e.g. 'Ep02_sq0220_SH1350__CFX_botgroomSamS001'.
    """
    asset_part = build_asset_part(asset_type, asset_name, variant, config)
    return '{}_{}_{}{}{}'.format(ep, seq, shot, SHOT_ASSET_SEPARATOR, asset_part)


def build_sequence_dir_name(basename, ext):
    """Build the sequence directory name for a publish basename."""
    return '{}_{}'.format(basename, ext.lstrip('.'))


def build_frame_file_name(basename, ext, frame_token=DEFAULT_FRAME_TOKEN):
    """Build the per-frame filename for a sequence publish.

    The frame token is left literal for the renderer to substitute -- Arnold
    expands '####' itself when useFrameExtension is enabled.
    """
    return '{}.{}.{}'.format(basename, frame_token, ext.lstrip('.'))


def build_namespace(asset_type, basename, asset_name, variant, config=None):
    """Build the Maya namespace for an asset instance.

    CFX uses the full publish basename, which carries the shot code and is
    therefore shot-unique.  That uniqueness is what lets the display-layer
    switch tell one shot's CFX from another's, since
    ``DisplayLayerManager.switch_shot_layers`` keys on the namespace as a
    global identity across all shots.

    Args:
        asset_type (str): Asset type code.
        basename (str): Full publish basename.
        asset_name (str): Asset name.
        variant (str): Variant code.
        config: Optional ProjectConfig instance.

    Returns:
        str: Namespace string.
    """
    mode = get_policy(asset_type, config)['namespace']

    if mode == NS_BASENAME:
        return basename
    if mode == NS_NAME_ONLY:
        return asset_name
    return '{}_{}_{}'.format(asset_type, asset_name, variant)


def build_standin_node_names(basename, suffix=DEFAULT_STANDIN_SUFFIX):
    """Build the three-level standin node names for a sequence asset.

    The observed CFX scene structure nests a standin transform under a
    per-asset transform, with the aiStandIn shape below that:

        <basename>                    top transform
          <basename>_aiStandIn        standin transform
            <basename>_aiStandInShape aiStandIn shape

    Args:
        basename (str): Publish basename.
        suffix (str): Standin transform suffix.

    Returns:
        dict: {'top', 'transform', 'shape'} node names, without namespace.
    """
    transform = '{}{}'.format(basename, suffix)
    return {
        'top': basename,
        'transform': transform,
        'shape': '{}Shape'.format(transform),
    }
