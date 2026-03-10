"""Tests for SlateManager.

All tests run without Maya using manual mock injection and unittest.mock,
matching the pattern used in test_slate_nodes.py.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch, call

# Ensure project root is on the path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from core.slate.manager import SlateManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_cmds():
    mock = MagicMock()
    mock.objExists.return_value = True
    return mock


def _make_slate_node(node_name='CTX_Slate1'):
    """Return a MagicMock that looks like a CTXSlateNode."""
    slate = MagicMock()
    slate.node_name = node_name
    return slate


def _make_shot_node(node_name='CTX_Shot1', seq_code='sq0070', shot_code='SH0170'):
    shot = MagicMock()
    shot.node_name = node_name
    shot.get_seq_code.return_value = seq_code
    shot.get_shot_code.return_value = shot_code
    shot.get_slate.return_value = None
    return shot


def _make_seq_node(node_name='CTX_Sequence1', seq_code='sq0070'):
    seq = MagicMock()
    seq.node_name = node_name
    seq.get_attribute.return_value = seq_code
    seq.get_slate.return_value = None
    return seq


# ---------------------------------------------------------------------------
# SlateManager public API tests
# ---------------------------------------------------------------------------

class TestCreateMasterSlate(unittest.TestCase):
    """SlateManager.create_master_slate() creates CTXSlateNode with type='master'."""

    def test_create_master_slate(self):
        """create_master_slate calls CTXSlateNode.create with slateType='master'."""
        mock_slate = _make_slate_node('CTX_Slate_Master')

        with patch('core.slate.manager.SlateManager.create_master_slate',
                   wraps=SlateManager.create_master_slate):
            with patch('core.nodes.wrappers.slate.CTXSlateNode.create',
                       return_value=mock_slate) as mock_create:
                result = SlateManager.create_master_slate('Master')

        mock_create.assert_called_once_with(
            slateName='Master',
            slateType='master',
            scopeCode='',
        )
        self.assertIs(result, mock_slate)

    def test_create_master_slate_default_name(self):
        """Default name is 'Master'."""
        mock_slate = _make_slate_node('CTX_Slate_Master')

        with patch('core.nodes.wrappers.slate.CTXSlateNode.create',
                   return_value=mock_slate) as mock_create:
            SlateManager.create_master_slate()

        args, kwargs = mock_create.call_args
        self.assertEqual(kwargs.get('slateName', args[0] if args else None), 'Master')


class TestCreateSequenceSlate(unittest.TestCase):
    """SlateManager.create_sequence_slate() assigns to sequence and wires parent."""

    def test_create_sequence_slate_assigns_to_seq(self):
        """Creates slate and calls seq.set_slate()."""
        mock_slate = _make_slate_node('CTX_Slate_seq')
        mock_seq = _make_seq_node()

        with patch('core.nodes.wrappers.slate.CTXSlateNode.create',
                   return_value=mock_slate):
            result = SlateManager.create_sequence_slate(mock_seq)

        mock_seq.set_slate.assert_called_once_with(mock_slate)
        self.assertIs(result, mock_slate)

    def test_create_sequence_slate_wires_parent(self):
        """parent_slate provided; set_parent_slate called."""
        mock_slate = _make_slate_node('CTX_Slate_seq')
        mock_seq = _make_seq_node()
        mock_parent = _make_slate_node('CTX_Slate_master')

        with patch('core.nodes.wrappers.slate.CTXSlateNode.create',
                   return_value=mock_slate):
            SlateManager.create_sequence_slate(mock_seq, parent_slate=mock_parent)

        mock_slate.set_parent_slate.assert_called_once_with(mock_parent)

    def test_create_sequence_slate_no_parent_wires_nothing(self):
        """Without parent_slate, set_parent_slate is not called."""
        mock_slate = _make_slate_node('CTX_Slate_seq')
        mock_seq = _make_seq_node()

        with patch('core.nodes.wrappers.slate.CTXSlateNode.create',
                   return_value=mock_slate):
            SlateManager.create_sequence_slate(mock_seq)

        mock_slate.set_parent_slate.assert_not_called()


class TestCreateShotSlate(unittest.TestCase):
    """SlateManager.create_shot_slate() assigns to shot and auto-wires seq slate."""

    def test_create_shot_slate_assigns_to_shot(self):
        """Creates slate and calls shot.set_slate()."""
        mock_slate = _make_slate_node('CTX_Slate_shot')
        mock_shot = _make_shot_node()

        with patch('core.nodes.wrappers.slate.CTXSlateNode.create',
                   return_value=mock_slate):
            with patch.object(SlateManager, '_find_sequence_slate_for_shot', return_value=None):
                result = SlateManager.create_shot_slate(mock_shot)

        mock_shot.set_slate.assert_called_once_with(mock_slate)
        self.assertIs(result, mock_slate)

    def test_create_shot_slate_explicit_parent(self):
        """Explicit parent_slate is wired; auto-wire is skipped."""
        mock_slate = _make_slate_node('CTX_Slate_shot')
        mock_shot = _make_shot_node()
        mock_parent = _make_slate_node('CTX_Slate_seq')

        with patch('core.nodes.wrappers.slate.CTXSlateNode.create',
                   return_value=mock_slate):
            with patch.object(SlateManager, '_find_sequence_slate_for_shot') as mock_find:
                SlateManager.create_shot_slate(mock_shot, parent_slate=mock_parent)

        mock_slate.set_parent_slate.assert_called_once_with(mock_parent)
        mock_find.assert_not_called()

    def test_create_shot_slate_auto_wires_seq_slate(self):
        """Shot has parent sequence with existing slate; auto-wired as parentSlate."""
        mock_slate = _make_slate_node('CTX_Slate_shot')
        mock_shot = _make_shot_node()
        mock_seq_slate = _make_slate_node('CTX_Slate_seq')

        with patch('core.nodes.wrappers.slate.CTXSlateNode.create',
                   return_value=mock_slate):
            with patch.object(SlateManager, '_find_sequence_slate_for_shot',
                              return_value=mock_seq_slate):
                SlateManager.create_shot_slate(mock_shot)

        mock_slate.set_parent_slate.assert_called_once_with(mock_seq_slate)

    def test_create_shot_slate_no_auto_wire_when_no_seq_slate(self):
        """If no sequence slate exists, set_parent_slate is not called."""
        mock_slate = _make_slate_node('CTX_Slate_shot')
        mock_shot = _make_shot_node()

        with patch('core.nodes.wrappers.slate.CTXSlateNode.create',
                   return_value=mock_slate):
            with patch.object(SlateManager, '_find_sequence_slate_for_shot', return_value=None):
                SlateManager.create_shot_slate(mock_shot)

        mock_slate.set_parent_slate.assert_not_called()


class TestGetOrCreateShotSlate(unittest.TestCase):
    """SlateManager.get_or_create_shot_slate() returns existing or creates new."""

    def test_get_or_create_returns_existing(self):
        """Shot already has slate; no new node created."""
        mock_existing = _make_slate_node('CTX_Slate_existing')
        mock_shot = _make_shot_node()
        mock_shot.get_slate.return_value = mock_existing

        with patch.object(SlateManager, 'create_shot_slate') as mock_create:
            result = SlateManager.get_or_create_shot_slate(mock_shot)

        mock_create.assert_not_called()
        self.assertIs(result, mock_existing)

    def test_get_or_create_creates_when_absent(self):
        """Shot has no slate; create_shot_slate is called."""
        mock_new_slate = _make_slate_node('CTX_Slate_new')
        mock_shot = _make_shot_node()
        mock_shot.get_slate.return_value = None  # no existing slate

        with patch.object(SlateManager, 'create_shot_slate',
                          return_value=mock_new_slate) as mock_create:
            result = SlateManager.get_or_create_shot_slate(mock_shot)

        mock_create.assert_called_once_with(mock_shot)
        self.assertIs(result, mock_new_slate)


class TestAddLayerToSlate(unittest.TestCase):
    """SlateManager.add_layer_to_slate() creates CTXSlateLayerNode in slate."""

    def test_add_layer_to_slate(self):
        """add_layer_to_slate calls slate_node.add_layer with correct args."""
        mock_layer = MagicMock()
        mock_slate = _make_slate_node('CTX_Slate1')
        mock_slate.add_layer.return_value = mock_layer

        result = SlateManager.add_layer_to_slate(mock_slate, 'beauty', renderable=True,
                                                  override_enabled=False)

        mock_slate.add_layer.assert_called_once_with(
            'beauty', renderable=True, enabled=False
        )
        self.assertIs(result, mock_layer)

    def test_add_layer_to_slate_string_node(self):
        """Accepts string node name; wraps in CTXSlateNode."""
        mock_layer = MagicMock()
        mock_slate_wrapper = _make_slate_node('CTX_Slate1')
        mock_slate_wrapper.add_layer.return_value = mock_layer

        # CTXSlateNode is imported inside add_layer_to_slate; patch at its source
        with patch('core.nodes.wrappers.slate.CTXSlateNode', return_value=mock_slate_wrapper):
            result = SlateManager.add_layer_to_slate(
                'CTX_Slate1', 'beauty', renderable=False, override_enabled=True
            )

        mock_slate_wrapper.add_layer.assert_called_once_with(
            'beauty', renderable=False, enabled=True
        )

    def test_add_layer_with_override_enabled_true(self):
        """override_enabled=True is passed as enabled=True to add_layer."""
        mock_layer = MagicMock()
        mock_slate = _make_slate_node()
        mock_slate.add_layer.return_value = mock_layer

        SlateManager.add_layer_to_slate(mock_slate, 'diffuse', renderable=False,
                                         override_enabled=True)
        mock_slate.add_layer.assert_called_with('diffuse', renderable=False, enabled=True)


class TestRemoveLayerFromSlate(unittest.TestCase):
    """SlateManager.remove_layer_from_slate() calls slate.remove_layer."""

    def test_remove_layer_from_slate(self):
        """remove_layer_from_slate calls slate_node.remove_layer with layer_name."""
        mock_slate = _make_slate_node('CTX_Slate1')

        SlateManager.remove_layer_from_slate(mock_slate, 'beauty')

        mock_slate.remove_layer.assert_called_once_with('beauty')

    def test_remove_layer_from_slate_string_node(self):
        """Accepts string node name; wraps in CTXSlateNode."""
        mock_slate_wrapper = _make_slate_node('CTX_Slate1')

        # CTXSlateNode is imported inside remove_layer_from_slate; patch at its source
        with patch('core.nodes.wrappers.slate.CTXSlateNode', return_value=mock_slate_wrapper):
            SlateManager.remove_layer_from_slate('CTX_Slate1', 'diffuse')

        mock_slate_wrapper.remove_layer.assert_called_once_with('diffuse')


# ---------------------------------------------------------------------------
# _find_sequence_slate_for_shot (no-Maya path)
# ---------------------------------------------------------------------------

class TestFindSequenceSlatForShot(unittest.TestCase):

    def test_returns_none_without_maya(self):
        """_find_sequence_slate_for_shot returns None when MAYA_AVAILABLE is False."""
        import core.slate.manager as manager_mod
        orig = manager_mod.MAYA_AVAILABLE
        manager_mod.MAYA_AVAILABLE = False
        try:
            mock_shot = _make_shot_node()
            result = SlateManager._find_sequence_slate_for_shot(mock_shot)
            self.assertIsNone(result)
        finally:
            manager_mod.MAYA_AVAILABLE = orig


# ---------------------------------------------------------------------------
# Static method existence checks
# ---------------------------------------------------------------------------

class TestSlateManagerStaticMethods(unittest.TestCase):

    def test_all_public_methods_exist(self):
        for method_name in [
            'create_master_slate',
            'create_sequence_slate',
            'create_shot_slate',
            'get_or_create_shot_slate',
            'add_layer_to_slate',
            'remove_layer_from_slate',
        ]:
            self.assertTrue(
                hasattr(SlateManager, method_name),
                'Missing method: {}'.format(method_name)
            )
            self.assertTrue(callable(getattr(SlateManager, method_name)))


if __name__ == '__main__':
    unittest.main()
