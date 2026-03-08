# -*- coding: utf-8 -*-
"""Shader assignment system for geometry.

This module provides utilities to assign shaders from shader namespaces to
geometry namespaces using stored mapping data. It also handles Redshift
rsMeshParameters binding.

Author: Context Variables Pipeline
Date: 2026-02-18
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import logging

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False
    from core.custom_nodes import cmds  # Use mock cmds

logger = logging.getLogger(__name__)


def read_mapping_from_shading_group(sg):
    """Read stored shape mapping from snow__assign_shade attribute.

    The shader.ma file contains shading groups with a custom attribute 'snow__assign_shade'
    that stores the original DAG paths of geometry shapes that should be assigned to this
    shading group. This mapping is created during shader authoring and preserved in the file.

    Args:
        sg (str): Shading group node name

    Returns:
        list: List of stored DAG paths (e.g., ['|GEO|body|bodyShape']), or empty list if not found

    Example:
        >>> mapping = read_mapping_from_shading_group('CHAR_CatStompie_001_Shade:body_SG')
        >>> # Returns: ['|GEO|body|bodyShape', '|GEO|head|headShape']
    """
    attr = "{}.snow__assign_shade".format(sg)

    if not cmds.objExists(attr):
        return []

    # Get attribute type to handle different storage formats
    try:
        atype = cmds.getAttr(attr, type=True)
    except Exception:
        return []

    try:
        if atype == "stringArray":
            # Maya stringArray returns tuple: (size, [items])
            arr = cmds.getAttr(attr)
            if isinstance(arr, (list, tuple)):
                # Handle Maya's stringArray format: (2, ['path1', 'path2'])
                if len(arr) == 2 and isinstance(arr[1], (list, tuple)):
                    return list(arr[1])
                return list(arr)
            return []
        elif atype == "string":
            # Single string - might be JSON or Python literal
            raw = cmds.getAttr(attr)
            if not raw:
                return []

            # Try JSON parsing first
            try:
                import json
                val = json.loads(raw)
                if isinstance(val, list):
                    return [str(x) for x in val]
            except Exception:
                pass

            # Try Python literal_eval
            try:
                import ast
                val = ast.literal_eval(raw)
                if isinstance(val, list):
                    return [str(x) for x in val]
            except Exception:
                pass

            # Fallback: treat as single path
            return [raw]

        return []

    except Exception as e:
        logger.warning("Failed to read mapping from {}: {}".format(sg, str(e)))
        return []


def _strip_namespace(node_name):
    """Strip namespace from node name.

    Args:
        node_name (str): Node name with or without namespace

    Returns:
        str: Node name without namespace

    Example:
        >>> _strip_namespace('CHAR_CatStompie_001:bodyShape')
        >>> # Returns: 'bodyShape'
    """
    return node_name.split(':')[-1] if node_name else node_name


def _apply_namespace_to_path(src_dag_path, namespace):
    """Apply namespace to all segments of a DAG path.

    Args:
        src_dag_path (str): Original DAG path (e.g., '|GEO|body|bodyShape')
        namespace (str): Namespace to apply (e.g., 'CHAR_CatStompie_001')

    Returns:
        str: DAG path with namespace applied, or None if invalid

    Example:
        >>> _apply_namespace_to_path('|GEO|body|bodyShape', 'CHAR_CatStompie_001')
        >>> # Returns: '|CHAR_CatStompie_001:GEO|CHAR_CatStompie_001:body|CHAR_CatStompie_001:bodyShape'
    """
    if not src_dag_path or not src_dag_path.startswith("|"):
        return None

    parts = [p for p in src_dag_path.split("|") if p]
    new_parts = ["{}:{}".format(namespace, _strip_namespace(seg)) for seg in parts]
    return "|" + "|".join(new_parts)


def resolve_shape_in_scene(stored_path, geo_namespace):
    """Resolve stored DAG path to actual shape in scene.

    This function implements the same logic as igl_shot_build.py to resolve
    stored DAG paths from shader.ma files to actual geometry in the scene.

    The shader.ma file stores original DAG paths (e.g., '|GEO|body|bodyShape').
    When geometry is referenced with a namespace, we need to resolve these paths
    to the actual namespaced shapes (e.g., 'CHAR_CatStompie_001:bodyShape').

    Resolution strategies:
    1. Full DAG path reconstruction with namespace
    2. Check if resolved path is a shape node
    3. If transform, get its first shape child
    4. Fallback: Search by leaf name in namespace
    5. If multiple matches, use DAG path matching

    Args:
        stored_path (str): Original DAG path from mapping (e.g., '|GEO|body|bodyShape')
        geo_namespace (str): Target geometry namespace (e.g., 'CHAR_CatStompie_001')

    Returns:
        str: Resolved shape node name (full path), or None if not found

    Example:
        >>> shape = resolve_shape_in_scene('|GEO|body|bodyShape', 'CHAR_CatStompie_001')
        >>> # Returns: '|CHAR_CatStompie_001:GEO|CHAR_CatStompie_001:body|CHAR_CatStompie_001:bodyShape'
    """
    if not MAYA_AVAILABLE:
        return None

    # Strategy 1: Try full DAG path reconstruction with namespace
    candidate = _apply_namespace_to_path(stored_path, geo_namespace)
    if candidate and cmds.objExists(candidate):
        # Check if it's a shape node
        try:
            node_type = cmds.nodeType(candidate)
            if node_type in ("mesh", "nurbsSurface", "nurbsCurve", "subdiv", "aiStandIn"):
                return candidate

            # If it's a transform, get its first shape
            if cmds.objectType(candidate, isAType="transform"):
                shapes = cmds.listRelatives(candidate, shapes=True, fullPath=True) or []
                if shapes:
                    return shapes[0]
        except Exception:
            pass

    # Strategy 2: Fallback by leaf shape name within geo namespace
    leaf = _strip_namespace(stored_path.split("|")[-1]) if "|" in stored_path else _strip_namespace(stored_path)

    # Search for shapes with matching leaf name in the namespace
    candidates = []
    try:
        for shp in cmds.ls(type=["mesh", "nurbsSurface", "nurbsCurve", "aiStandIn"], long=True) or []:
            if _strip_namespace(shp).lower() == leaf.lower():
                # Ensure it's under geo namespace
                last_seg = shp.split("|")[-1]
                if ":" in last_seg and last_seg.split(":")[0] == geo_namespace:
                    candidates.append(shp)
    except Exception as e:
        logger.warning("Failed to search for shape {}: {}".format(leaf, str(e)))

    # If single match, return it
    if len(candidates) == 1:
        return candidates[0]

    # If multiple matches, use DAG path matching to find best match
    elif len(candidates) > 1:
        target_segments = [s for s in stored_path.split("|") if s]
        target_wo_ns = [_strip_namespace(s) for s in target_segments]

        for shp in candidates:
            segs = [s for s in shp.split("|") if s]
            segs_wo_ns = [_strip_namespace(s) for s in segs]

            # Check if the tail of the candidate matches the stored path
            if segs_wo_ns[-len(target_wo_ns):] == target_wo_ns:
                return shp

        # If no perfect match, return first candidate
        return candidates[0]

    return None


def _get_material_from_shading_group(sg):
    """Get material connected to shading group.

    Checks both Redshift (rsSurfaceShader) and standard Maya (surfaceShader) connections.

    Args:
        sg (str): Shading group node name

    Returns:
        str: Material node name, or None if not found
    """
    if not MAYA_AVAILABLE:
        return None

    # Check Redshift connection first, then standard Maya
    for plug in ("rsSurfaceShader", "surfaceShader"):
        plg = "{}.{}".format(sg, plug)
        if cmds.objExists(plg):
            try:
                conns = cmds.listConnections(plg, source=True, destination=False) or []
                if conns:
                    return conns[0]
            except Exception:
                pass

    return None


def scan_shader_assignments(shader_namespace):
    """Scan for shading groups with stored mapping data.

    This function scans all shading groups in the shader namespace and finds those
    that have the 'snow__assign_shade' attribute. This attribute is created during
    shader authoring and stores the original DAG paths of geometry that should be
    assigned to each shading group.

    Args:
        shader_namespace (str): Shader namespace to scan (e.g., 'CHAR_CatStompie_001_Shade')

    Returns:
        list: List of tuples (sg, material, mapping_list) where:
            - sg: Shading group node name
            - material: Connected material node name (or None)
            - mapping_list: List of stored DAG paths

    Example:
        >>> entries = scan_shader_assignments('CHAR_CatStompie_001_Shade')
        >>> # Returns: [
        >>> #   ('CHAR_CatStompie_001_Shade:body_SG', 'body_MAT', ['|GEO|body|bodyShape']),
        >>> #   ('CHAR_CatStompie_001_Shade:head_SG', 'head_MAT', ['|GEO|head|headShape'])
        >>> # ]
    """
    if not MAYA_AVAILABLE:
        return []

    all_sg = cmds.ls(type='shadingEngine') or []
    hit = []

    for sg in all_sg:
        # Check if SG belongs to shader namespace
        if not sg.startswith(shader_namespace + ":"):
            continue

        # Check if it has stored mapping data
        if cmds.objExists("{}.snow__assign_shade".format(sg)):
            mapping = read_mapping_from_shading_group(sg)

            # Get connected material
            material = _get_material_from_shading_group(sg)

            hit.append((sg, material, mapping))

    logger.info("Found {} shading groups with mapping data in {}".format(
        len(hit), shader_namespace))

    return hit


def plan_shader_assignments(geo_namespace, sg_entries):
    """Plan shader assignments using stored mapping data.

    Args:
        geo_namespace (str): Geometry namespace
        sg_entries (list): List of tuples from scan_shader_assignments()

    Returns:
        list: List of assignment plan dicts with 'sg', 'material', 'targets', 'resolved', 'unresolved'

    Example:
        >>> plan = plan_shader_assignments('CHAR_CatStompie_001', sg_entries)
        >>> # Returns: [{'sg': 'body_SG', 'resolved': ['CHAR_CatStompie_001:bodyShape'], ...}]
    """
    plan = []

    for sg, mat, stored_paths in sg_entries:
        resolved = []
        unresolved = []

        for path in stored_paths:
            shape = resolve_shape_in_scene(path, geo_namespace)
            if shape and cmds.objExists(shape):
                resolved.append(shape)
            else:
                unresolved.append(path)

        plan.append({
            'sg': sg,
            'material': mat,
            'targets': list(stored_paths),
            'resolved': sorted(list(set(resolved))),
            'unresolved': list(unresolved)
        })

    return plan


def assign_shapes_to_shading_group(shapes, sg):
    """Assign list of shapes to shading group.

    Uses Maya's sets command with forceElement to assign shapes to the shading group.
    This is the same method used in production (igl_shot_build.py).

    Args:
        shapes (list): List of shape node names (full paths)
        sg (str): Shading group node name

    Returns:
        tuple: (assigned_count, failed_list) where failed_list contains (shape, error) tuples

    Example:
        >>> assigned, failed = assign_shapes_to_shading_group(
        ...     ['|CHAR_CatStompie_001:GEO|CHAR_CatStompie_001:body|CHAR_CatStompie_001:bodyShape'],
        ...     'CHAR_CatStompie_001_Shade:body_SG'
        ... )
        >>> # Returns: (1, [])
    """
    if not MAYA_AVAILABLE:
        return 0, []

    assigned = 0
    failed = []

    for shape in shapes:
        try:
            # Check if shape exists before assigning
            if not cmds.objExists(shape):
                failed.append((shape, "missing"))
                continue

            # Assign shape to shading group
            cmds.sets(shape, edit=True, forceElement=sg)
            assigned += 1

        except Exception as e:
            failed.append((shape, str(e)))
            logger.warning("Failed to assign {} to {}: {}".format(shape, sg, str(e)))

    return assigned, failed


def assign_shaders_to_geometry(shader_namespace, geo_namespace):
    """Complete shader assignment workflow.

    This function:
    1. Scans for shading groups with stored mapping data
    2. Plans assignments by resolving stored paths
    3. Executes assignments

    Args:
        shader_namespace (str): Shader namespace
        geo_namespace (str): Geometry namespace

    Returns:
        dict: Summary with 'total_assigned', 'total_failed', 'details'

    Example:
        >>> result = assign_shaders_to_geometry('CHAR_CatStompie_001_Shade', 'CHAR_CatStompie_001')
        >>> # Returns: {'total_assigned': 10, 'total_failed': 0, 'details': [...]}
    """
    if not MAYA_AVAILABLE:
        return {'total_assigned': 0, 'total_failed': 0, 'details': []}

    # Scan for shader assignments
    sg_entries = scan_shader_assignments(shader_namespace)
    logger.info("Found {} shading groups with mapping data".format(len(sg_entries)))

    # Plan assignments
    assignment_plan = plan_shader_assignments(geo_namespace, sg_entries)

    # Execute assignments
    total_assigned = 0
    total_failed = 0
    details = []

    for entry in assignment_plan:
        sg = entry['sg']
        resolved = entry.get('resolved', [])
        unresolved = entry.get('unresolved', [])

        if resolved:
            assigned, failed = assign_shapes_to_shading_group(resolved, sg)
            total_assigned += assigned
            total_failed += len(failed)

            details.append({
                'sg': sg,
                'material': entry.get('material'),
                'assigned': assigned,
                'failed': len(failed),
                'unresolved': len(unresolved)
            })

            logger.info("Assigned {} shapes to {} (failed: {}, unresolved: {})".format(
                assigned, sg, len(failed), len(unresolved)))

    return {
        'total_assigned': total_assigned,
        'total_failed': total_failed,
        'details': details
    }


def bind_to_redshift_mesh_parameters(geo_namespace, shader_namespace, top_level_transforms=None):
    """Bind top-level geometry transforms to rsMeshParameters sets in shader namespace.

    This function implements three binding strategies:
    1. Name matching - Match set names to transform names
    2. All-to-all - Add all transforms to all sets
    3. Aggressive fallback - Try various name patterns

    Args:
        geo_namespace (str): Geometry namespace
        shader_namespace (str): Shader namespace
        top_level_transforms (list, optional): List of top-level transforms. If None, auto-detect.

    Returns:
        dict: Summary with 'sets_found', 'transforms_bound', 'details'

    Example:
        >>> result = bind_to_redshift_mesh_parameters('CHAR_CatStompie_001', 'CHAR_CatStompie_001_Shade')
        >>> # Returns: {'sets_found': 2, 'transforms_bound': 5, 'details': [...]}
    """
    if not MAYA_AVAILABLE:
        return {'sets_found': 0, 'transforms_bound': 0, 'details': []}

    # Get top-level transforms if not provided
    if top_level_transforms is None:
        all_transforms = cmds.ls("{}:*".format(geo_namespace), type='transform') or []
        top_level_transforms = []
        for node in all_transforms:
            parent = cmds.listRelatives(node, parent=True, fullPath=False)
            if not parent or parent[0] == 'world':
                top_level_transforms.append(node)

    if not top_level_transforms:
        logger.warning("No top-level transforms found in namespace: {}".format(geo_namespace))
        return {'sets_found': 0, 'transforms_bound': 0, 'details': []}

    # Find all rsMeshParameters sets in shader namespace
    rs_mesh_sets = []
    shader_sets = cmds.ls("{}:*".format(shader_namespace), type='objectSet') or []

    for set_node in shader_sets:
        set_short = set_node.split(':')[-1]
        if 'rsMeshParameters' in set_short or 'rsMP' in set_short:
            rs_mesh_sets.append(set_node)

    if not rs_mesh_sets:
        logger.info("No rsMeshParameters sets found in shader namespace: {}".format(shader_namespace))
        return {'sets_found': 0, 'transforms_bound': 0, 'details': []}

    logger.info("Found {} rsMeshParameters sets".format(len(rs_mesh_sets)))

    # Strategy 1: Try to match by name pattern
    details = []
    total_bound = 0

    for rs_set in rs_mesh_sets:
        set_short = rs_set.split(':')[-1]
        bound_count = 0

        # Try to find matching transforms by name
        for transform in top_level_transforms:
            transform_short = transform.split(':')[-1]

            # Check if transform name is in set name or vice versa
            if transform_short.lower() in set_short.lower() or set_short.lower() in transform_short.lower():
                try:
                    cmds.sets(transform, edit=True, addElement=rs_set)
                    bound_count += 1
                    logger.info("Bound {} to {}".format(transform, rs_set))
                except Exception as e:
                    logger.warning("Failed to bind {} to {}: {}".format(transform, rs_set, str(e)))

        # Strategy 2: If no matches found, add all transforms to this set
        if bound_count == 0:
            for transform in top_level_transforms:
                try:
                    cmds.sets(transform, edit=True, addElement=rs_set)
                    bound_count += 1
                except Exception as e:
                    logger.warning("Failed to bind {} to {}: {}".format(transform, rs_set, str(e)))

        total_bound += bound_count
        details.append({
            'set': rs_set,
            'bound_count': bound_count
        })

    return {
        'sets_found': len(rs_mesh_sets),
        'transforms_bound': total_bound,
        'details': details
    }

