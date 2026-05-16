# -*- coding: utf-8 -*-
"""Gaffer chain serializer for JSON export and import.

Converts gaffer chains attached to a shot to/from a JSON-serializable dict.
Operates on CTX nodes already present in the current Maya scene.
Does NOT open or save scene files.
"""

from __future__ import absolute_import
from __future__ import print_function

import json
import os
import datetime

from core.logging_config import get_logger

logger = get_logger(__name__)


# All attribute groups tracked by CTXLightContextSchema.
# Each entry is (group_name, [value_attrs], has_mode_flag)
# scalar attrs store a single value; compound attrs store a list.
_SCALAR_ATTRS = [
    ('intensity',         ['intensity'],                            True),
    ('exposure',          ['exposure'],                             True),
    ('color',             ['colorR', 'colorG', 'colorB'],          True),
    ('temperature',       ['temperature'],                          True),
    ('muted',             ['muted'],                                False),
    ('translate',         ['translateX', 'translateY', 'translateZ'], True),
    ('rotate',            ['rotateX', 'rotateY', 'rotateZ'],       True),
    ('scale',             ['scaleX', 'scaleY', 'scaleZ'],          True),
    ('spread',            ['spread'],                               True),
    ('affectDiffuse',     ['affectDiffuse'],                        False),
    ('affectSpecular',    ['affectSpecular'],                       False),
    ('affectGI',          ['affectGI'],                             False),
    ('shadowEnable',      ['shadowEnable'],                         False),
    ('areaSpread',        ['areaSpread'],                           True),
    ('diffuseContrib',    ['diffuseContrib'],                       True),
    ('reflectionContrib', ['reflectionContrib'],                    True),
    ('transmissionContrib', ['transmissionContrib'],                True),
    ('singleScatterContrib', ['singleScatterContrib'],              True),
    ('multiScatterContrib',  ['multiScatterContrib'],               True),
    ('volumeContrib',     ['volumeContrib'],                        True),
    ('indirectContrib',   ['indirectContrib'],                      True),
    ('toonDiffuseContrib', ['toonDiffuseContrib'],                  True),
    ('toonReflectionContrib', ['toonReflectionContrib'],            True),
]


class GafferSerializer(object):
    """Serializes and deserializes gaffer chains to/from JSON.

    Works on CTX nodes already present in the current Maya scene.
    Does not open or save scene files.
    """

    FORMAT_VERSION = 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export_shot(self, shot_node, config=None):
        """Export all gaffers attached to a shot as a JSON-serializable dict.

        Requires Maya -- raises RuntimeError if Maya is not available.

        Args:
            shot_node: CTXShotNode instance or node name string.
            config: Optional ProjectConfig (reserved for future use).

        Returns:
            dict: JSON-serializable gaffer data.

        Raises:
            RuntimeError: If Maya is not available.
        """
        try:
            import maya.cmds as cmds
        except ImportError:
            raise RuntimeError("Maya is required for gaffer export/import")

        shot_node_name = shot_node if isinstance(shot_node, str) else shot_node.node_name

        # Resolve shot ID
        try:
            ep = cmds.getAttr('%s.ep_code' % shot_node_name) or ''
            seq = cmds.getAttr('%s.seq_code' % shot_node_name) or ''
            shot = cmds.getAttr('%s.shot_code' % shot_node_name) or ''
            shot_id = '%s_%s_%s' % (ep, seq, shot)
        except Exception:
            shot_id = shot_node_name

        # Collect gaffer chain starting from the shot's own gaffer
        gaffers_data = []
        visited = set()

        shot_gaffer_connections = cmds.listConnections(
            '%s.gaffer' % shot_node_name,
            source=True,
            destination=False,
            plugs=False
        ) or []

        if shot_gaffer_connections:
            root_gaffer = shot_gaffer_connections[0]
            self._collect_gaffer_chain(root_gaffer, gaffers_data, visited, cmds)

        result = {
            'version': self.FORMAT_VERSION,
            'shot': shot_id,
            'exported': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S'),
            'gaffers': gaffers_data,
        }

        logger.info(
            "Exported %d gaffers (%d total lights) for shot %s",
            len(gaffers_data),
            sum(len(g.get('lights', [])) for g in gaffers_data),
            shot_id,
        )
        return result

    def import_shot(self, shot_node, data, config=None):
        """Apply gaffer data dict to a shot in the current scene.

        Requires Maya -- raises RuntimeError if Maya is not available.

        Args:
            shot_node: CTXShotNode instance or node name string.
            data (dict): Gaffer data from export_shot() or from_json().
            config: Optional ProjectConfig (reserved for future use).

        Returns:
            int: Number of light contexts imported.

        Raises:
            RuntimeError: If Maya is not available.
        """
        try:
            import maya.cmds as cmds
        except ImportError:
            raise RuntimeError("Maya is required for gaffer export/import")

        from core.nodes.wrappers import CTXLightGafferNode, CTXLightContextNode

        shot_node_name = shot_node if isinstance(shot_node, str) else shot_node.node_name

        version = data.get('version', 1)
        if version != self.FORMAT_VERSION:
            logger.warning(
                "Gaffer JSON version %s does not match expected %s -- attempting import anyway",
                version, self.FORMAT_VERSION
            )

        gaffers_data = data.get('gaffers', [])
        total_lights = 0
        prev_gaffer_node = None  # track chain for parentGaffer wiring

        for gaffer_data in gaffers_data:
            gaffer_name = gaffer_data.get('name', 'ImportedGaffer')
            gaffer_type = gaffer_data.get('type', 'master')

            # Find or create a gaffer with matching name
            gaffer_node_name = self._find_or_create_gaffer(
                gaffer_name, gaffer_type, cmds, CTXLightGafferNode
            )

            # Wire parentGaffer chain: first gaffer in list is owned by shot
            if prev_gaffer_node is None:
                # Connect this gaffer to the shot
                try:
                    cmds.connectAttr(
                        '%s.message' % gaffer_node_name,
                        '%s.gaffer' % shot_node_name,
                        force=True
                    )
                except Exception as exc:
                    logger.warning(
                        "Could not connect gaffer %s to shot %s: %s",
                        gaffer_node_name, shot_node_name, exc
                    )
            else:
                # Wire parent inheritance: parent_gaffer.message -> child_gaffer.parentGaffer
                try:
                    cmds.connectAttr(
                        '%s.message' % prev_gaffer_node,
                        '%s.parentGaffer' % gaffer_node_name,
                        force=True
                    )
                except Exception as exc:
                    logger.warning(
                        "Could not connect parentGaffer %s -> %s: %s",
                        prev_gaffer_node, gaffer_node_name, exc
                    )

            prev_gaffer_node = gaffer_node_name

            # Import light contexts
            lights_data = gaffer_data.get('lights', [])
            for light_data in lights_data:
                light_name = light_data.get('light_name', '')
                target_shape = light_data.get('target_shape', '')
                attributes = light_data.get('attributes', {})

                ctx_node_name = self._find_or_create_light_context(
                    gaffer_node_name, gaffer_name, light_name,
                    target_shape, cmds, CTXLightContextNode
                )

                self._apply_attributes(ctx_node_name, attributes, cmds)
                total_lights += 1

        logger.info(
            "Imported %d light contexts across %d gaffers for shot %s",
            total_lights, len(gaffers_data), shot_node_name
        )
        return total_lights

    def to_json(self, data, path):
        """Write data dict to a JSON file.

        Creates parent directories as needed.

        Args:
            data (dict): Gaffer data dict from export_shot().
            path (str): Output file path.
        """
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, 'w') as fh:
            json.dump(data, fh, indent=2)
        logger.info("Gaffer exported to %s", path)

    def from_json(self, path):
        """Read JSON file and return data dict.

        Args:
            path (str): Path to gaffer JSON file.

        Returns:
            dict: Gaffer data dict.

        Raises:
            IOError: If file cannot be read.
        """
        with open(path, 'r') as fh:
            data = json.load(fh)
        logger.info("Gaffer loaded from %s", path)
        return data

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _collect_gaffer_chain(self, gaffer_node, gaffers_data, visited, cmds):
        """Recursively collect gaffer data walking the parentGaffer chain.

        Args:
            gaffer_node (str): Maya node name of the gaffer.
            gaffers_data (list): Accumulator list.
            visited (set): Already-visited node names.
            cmds: maya.cmds module.
        """
        if gaffer_node in visited:
            return
        visited.add(gaffer_node)

        # Read gaffer attributes
        try:
            gaffer_name = cmds.getAttr('%s.gafferName' % gaffer_node) or gaffer_node
        except Exception:
            gaffer_name = gaffer_node

        try:
            gaffer_type = cmds.getAttr('%s.gafferType' % gaffer_node) or 'master'
        except Exception:
            gaffer_type = 'master'

        # Collect light contexts
        lights_data = []
        light_connections = cmds.listConnections(
            '%s.lights' % gaffer_node,
            source=True,
            destination=False,
            plugs=False
        ) or []

        for lc_node in light_connections:
            light_entry = self._export_light_context(lc_node, cmds)
            if light_entry:
                lights_data.append(light_entry)

        gaffers_data.append({
            'name': gaffer_name,
            'type': gaffer_type,
            'lights': lights_data,
        })

        # Walk parentGaffer
        parent_connections = cmds.listConnections(
            '%s.parentGaffer' % gaffer_node,
            source=True,
            destination=False,
            plugs=False
        ) or []

        for parent_node in parent_connections:
            self._collect_gaffer_chain(parent_node, gaffers_data, visited, cmds)

    def _export_light_context(self, lc_node, cmds):
        """Export a single CTXLightContext node to a dict.

        Args:
            lc_node (str): Maya node name.
            cmds: maya.cmds module.

        Returns:
            dict or None: Light data, or None on failure.
        """
        try:
            light_name = cmds.getAttr('%s.lightName' % lc_node) or ''
        except Exception:
            light_name = ''

        # Resolve the connected target light shape name
        target_shape = ''
        try:
            tl_connections = cmds.listConnections(
                '%s.targetLight' % lc_node,
                source=True,
                destination=False,
                plugs=False
            ) or []
            if tl_connections:
                target_shape = tl_connections[0]
        except Exception:
            pass

        attributes = {}
        for group_name, value_attrs, has_mode in _SCALAR_ATTRS:
            enabled_attr = '%s.%sEnabled' % (lc_node, group_name)
            try:
                enabled = bool(cmds.getAttr(enabled_attr))
            except Exception:
                enabled = False

            # Read value(s)
            values = []
            for va in value_attrs:
                try:
                    v = cmds.getAttr('%s.%s' % (lc_node, va))
                    # Ensure JSON-safe types
                    if isinstance(v, bool):
                        values.append(v)
                    elif isinstance(v, (int, float)):
                        values.append(float(v))
                    else:
                        values.append(v)
                except Exception:
                    values.append(None)

            # Collapse single-element lists to scalar
            serialized_value = values[0] if len(values) == 1 else values

            entry = {
                'value': serialized_value,
                'enabled': enabled,
            }

            if has_mode:
                mode_attr = '%s.%sMode' % (lc_node, group_name)
                try:
                    mode = cmds.getAttr(mode_attr) or 'replace'
                except Exception:
                    mode = 'replace'
                entry['mode'] = mode

            attributes[group_name] = entry

        return {
            'light_name': light_name,
            'target_shape': target_shape,
            'attributes': attributes,
        }

    def _find_or_create_gaffer(self, gaffer_name, gaffer_type, cmds, CTXLightGafferNode):
        """Find an existing CTXLightGaffer node by gafferName or create a new one.

        Args:
            gaffer_name (str): Human-readable gaffer name.
            gaffer_type (str): Gaffer type string.
            cmds: maya.cmds module.
            CTXLightGafferNode: Wrapper class.

        Returns:
            str: Maya node name.
        """
        all_nodes = cmds.ls(type='network') or []
        for node in all_nodes:
            try:
                ctx_t = cmds.getAttr('%s.ctx_type' % node)
            except Exception:
                continue
            if ctx_t != 'CTX_LightGaffer':
                continue
            try:
                name_val = cmds.getAttr('%s.gafferName' % node) or ''
            except Exception:
                name_val = ''
            if name_val == gaffer_name:
                logger.debug("Reusing existing gaffer node: %s", node)
                return node

        # Create new
        new_gaffer = CTXLightGafferNode.create(
            gafferName=gaffer_name,
            gafferType=gaffer_type,
        )
        logger.info("Created new gaffer node: %s", new_gaffer.node_name)
        return new_gaffer.node_name

    def _find_or_create_light_context(
        self, gaffer_node_name, gaffer_name, light_name, target_shape,
        cmds, CTXLightContextNode
    ):
        """Find an existing CTXLightContext in this gaffer or create one.

        Args:
            gaffer_node_name (str): Maya gaffer node name.
            gaffer_name (str): Human-readable gaffer name (for new node naming).
            light_name (str): Light name to match.
            target_shape (str): Maya light shape to connect.
            cmds: maya.cmds module.
            CTXLightContextNode: Wrapper class.

        Returns:
            str: Maya node name of the light context.
        """
        existing_lights = cmds.listConnections(
            '%s.lights' % gaffer_node_name,
            source=True,
            destination=False,
            plugs=False
        ) or []

        for lc in existing_lights:
            try:
                existing_name = cmds.getAttr('%s.lightName' % lc) or ''
            except Exception:
                existing_name = ''
            if existing_name == light_name:
                logger.debug("Reusing existing light context: %s", lc)
                return lc

        # Create new
        new_ctx = CTXLightContextNode.create(
            gaffer_name=gaffer_name,
            lightName=light_name,
        )
        ctx_node = new_ctx.node_name

        # Wire to gaffer
        try:
            cmds.connectAttr(
                '%s.message' % ctx_node,
                '%s.lights' % gaffer_node_name,
                nextAvailable=True
            )
        except Exception as exc:
            logger.warning(
                "Could not connect light context %s to gaffer %s: %s",
                ctx_node, gaffer_node_name, exc
            )

        # Connect target light if it exists in the scene
        if target_shape and cmds.objExists(target_shape):
            try:
                cmds.connectAttr(
                    '%s.message' % target_shape,
                    '%s.targetLight' % ctx_node,
                    force=True
                )
            except Exception as exc:
                logger.warning(
                    "Could not connect target light %s to %s: %s",
                    target_shape, ctx_node, exc
                )
        elif target_shape:
            logger.warning(
                "Target light shape '%s' not found in scene -- skipping connection",
                target_shape
            )

        logger.info("Created light context: %s (light: %s)", ctx_node, light_name)
        return ctx_node

    def _apply_attributes(self, ctx_node, attributes, cmds):
        """Write attribute values and enabled flags from JSON data to the CTX node.

        Args:
            ctx_node (str): Maya node name of the light context.
            attributes (dict): Attribute dict from JSON.
            cmds: maya.cmds module.
        """
        for group_name, attr_entry in attributes.items():
            if not isinstance(attr_entry, dict):
                continue

            enabled = attr_entry.get('enabled', False)
            value = attr_entry.get('value')
            mode = attr_entry.get('mode', 'replace')

            # Find matching entry in _SCALAR_ATTRS
            group_def = None
            for entry in _SCALAR_ATTRS:
                if entry[0] == group_name:
                    group_def = entry
                    break

            if group_def is None:
                logger.debug("Unknown attribute group '%s' -- skipping", group_name)
                continue

            _, value_attrs, has_mode = group_def

            # Set enabled flag
            enabled_attr = '%s.%sEnabled' % (ctx_node, group_name)
            try:
                cmds.setAttr(enabled_attr, bool(enabled))
            except Exception as exc:
                logger.warning("Could not set %s: %s", enabled_attr, exc)

            # Set mode flag if present
            if has_mode:
                mode_attr = '%s.%sMode' % (ctx_node, group_name)
                try:
                    cmds.setAttr(mode_attr, mode, type='string')
                except Exception as exc:
                    logger.warning("Could not set %s: %s", mode_attr, exc)

            # Set value(s)
            if len(value_attrs) == 1:
                # Scalar
                try:
                    v = value
                    if isinstance(v, bool):
                        cmds.setAttr('%s.%s' % (ctx_node, value_attrs[0]), int(v))
                    elif v is not None:
                        cmds.setAttr('%s.%s' % (ctx_node, value_attrs[0]), float(v))
                except Exception as exc:
                    logger.warning(
                        "Could not set %s.%s: %s", ctx_node, value_attrs[0], exc
                    )
            else:
                # Compound (list of values)
                if not isinstance(value, (list, tuple)):
                    logger.warning(
                        "Expected list for compound attr '%s', got %s -- skipping",
                        group_name, type(value).__name__
                    )
                    continue
                for i, va in enumerate(value_attrs):
                    if i >= len(value):
                        break
                    try:
                        cmds.setAttr('%s.%s' % (ctx_node, va), float(value[i]))
                    except Exception as exc:
                        logger.warning(
                            "Could not set %s.%s: %s", ctx_node, va, exc
                        )
