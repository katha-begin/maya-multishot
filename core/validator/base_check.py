# -*- coding: utf-8 -*-
"""Base class for all scene validator checks."""

from __future__ import absolute_import, division, print_function

from core.logging_config import get_logger

logger = get_logger(__name__)


class BaseCheck(object):
    """Abstract base for a single named validation check.

    Subclasses must:
    - Set ``name`` class attribute (used as check_name in CheckResult)
    - Set ``severity`` class attribute ('error' | 'warning' | 'info')
    - Implement ``run(shot_node, config, platform_config=None, **kwargs)``
      which must return a CheckResult instance.
    """

    name = ''
    severity = 'error'

    def run(self, shot_node, config, platform_config=None, **kwargs):
        """Execute the check against shot_node.

        Args:
            shot_node: CTXShotNode wrapper instance.
            config: ProjectConfig instance.
            platform_config: PlatformConfig instance or None.
            **kwargs: Reserved for future extension.

        Returns:
            CheckResult
        """
        raise NotImplementedError(
            'BaseCheck subclass %s must implement run()' % type(self).__name__
        )
