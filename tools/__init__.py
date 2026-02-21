"""
Tools module for Context Variables Pipeline.

This module contains user-facing tools including shot manager, asset manager,
importer, converter, validator, scene saver, and Maya menu integration.
"""

__version__ = "0.1.0"

# Export maya_menu for easy access
from . import maya_menu

__all__ = ['maya_menu']

