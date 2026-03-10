"""Wrapper around Maya Render Setup API.

Provides a stable interface for enumerating and switching render layers.
Headless-safe: all methods return safe defaults when Maya is unavailable.
"""

from core.logging_config import get_logger

logger = get_logger(__name__)

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False


class RenderLayerInfo(object):
    """Lightweight data object for a Render Setup layer."""

    def __init__(self, name, renderable, is_default=False):
        self.name = name
        self.renderable = renderable
        self.is_default = is_default

    def __repr__(self):
        return 'RenderLayerInfo(name=%r, renderable=%r)' % (self.name, self.renderable)

    def to_dict(self):
        return {
            'name': self.name,
            'renderable': self.renderable,
            'is_default': self.is_default,
        }


class RenderSetupManager(object):
    """Wrapper for Maya Render Setup layer management.

    Usage::

        mgr = RenderSetupManager()
        if mgr.is_available():
            for layer in mgr.get_renderable_layers():
                mgr.switch_to_layer(layer.name)
                # render...
        else:
            # No Render Setup -- render with default layer
    """

    def is_available(self):
        """Return True if Maya Render Setup is accessible.

        Returns:
            bool
        """
        if not MAYA_AVAILABLE:
            return False
        try:
            import maya.app.renderSetup.model.renderSetup as rs
            rs.instance()
            return True
        except Exception:
            return False

    def get_all_layers(self):
        """Return all Render Setup layers (renderable or not).

        Returns:
            list[RenderLayerInfo]: Empty list if Render Setup unavailable.
        """
        if not self.is_available():
            logger.debug("Render Setup not available -- returning empty layer list")
            return []
        try:
            import maya.app.renderSetup.model.renderSetup as rs
            setup = rs.instance()
            default_layer = setup.getDefaultRenderLayer()
            default_name = default_layer.name() if default_layer else 'defaultRenderLayer'

            result = []
            for layer in setup.getRenderLayers():
                name = layer.name()
                result.append(RenderLayerInfo(
                    name=name,
                    renderable=bool(layer.isRenderable()),
                    is_default=(name == default_name),
                ))
            logger.debug("Found %d Render Setup layers", len(result))
            return result
        except Exception as exc:
            logger.warning("Failed to list Render Setup layers: %s", exc)
            return []

    def get_renderable_layers(self):
        """Return only layers marked as renderable.

        Returns:
            list[RenderLayerInfo]
        """
        return [l for l in self.get_all_layers() if l.renderable]

    def get_active_layer_name(self):
        """Return the name of the currently active layer.

        Returns:
            str: Layer name, or 'defaultRenderLayer' if unavailable.
        """
        if not self.is_available():
            return 'defaultRenderLayer'
        try:
            import maya.app.renderSetup.model.renderSetup as rs
            setup = rs.instance()
            visible = setup.getVisibleRenderLayer()
            return visible.name() if visible else 'defaultRenderLayer'
        except Exception as exc:
            logger.warning("Failed to get active render layer: %s", exc)
            return 'defaultRenderLayer'

    def switch_to_layer(self, layer_name):
        """Switch to a named Render Setup layer.

        Applies all overrides defined in that layer to the scene.

        Args:
            layer_name (str): Layer name as returned by RenderLayerInfo.name.

        Returns:
            bool: True if switch succeeded.
        """
        if not self.is_available():
            logger.warning("Render Setup not available -- cannot switch to %s", layer_name)
            return False
        try:
            import maya.app.renderSetup.model.renderSetup as rs
            setup = rs.instance()
            for layer in setup.getRenderLayers():
                if layer.name() == layer_name:
                    setup.switchToLayer(layer)
                    logger.info("Switched to render layer: %s", layer_name)
                    return True
            logger.warning("Render layer not found: %s", layer_name)
            return False
        except Exception as exc:
            logger.error("Failed to switch to layer %s: %s", layer_name, exc)
            return False

    def switch_to_default_layer(self):
        """Switch back to the default render layer.

        Returns:
            bool: True if switch succeeded.
        """
        if not self.is_available():
            return False
        try:
            import maya.app.renderSetup.model.renderSetup as rs
            setup = rs.instance()
            default = setup.getDefaultRenderLayer()
            if default:
                setup.switchToLayer(default)
                logger.info("Switched to default render layer")
                return True
            return False
        except Exception as exc:
            logger.error("Failed to switch to default layer: %s", exc)
            return False

    def get_layer_names(self, renderable_only=True):
        """Return list of layer name strings.

        Args:
            renderable_only (bool): If True, only return renderable layers.

        Returns:
            list[str]
        """
        layers = self.get_renderable_layers() if renderable_only else self.get_all_layers()
        return [l.name for l in layers]

    def is_render_setup_scene(self):
        """Return True if the current scene uses Render Setup (not legacy layers).

        Returns:
            bool
        """
        if not MAYA_AVAILABLE:
            return False
        try:
            layers = self.get_all_layers()
            return len(layers) > 0
        except Exception:
            return False
