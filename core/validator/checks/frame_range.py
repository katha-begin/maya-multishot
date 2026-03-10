# -*- coding: utf-8 -*-
"""Frame range consistency check.

Compares the shot's stored frame range against the Maya timeline.
Skipped in headless mode.
"""

from __future__ import absolute_import

from core.logging_config import get_logger
from core.validator.base_check import BaseCheck

logger = get_logger(__name__)

try:
    import maya.cmds as cmds
    MAYA_AVAILABLE = True
except ImportError:
    MAYA_AVAILABLE = False


class FrameRangeCheck(BaseCheck):
    """Verify Maya timeline matches shot frame range stored in CTX_Shot.

    Severity: warning — a mismatch is notable but the pipeline can still run.
    Only runs when Maya is available.
    """

    name = 'frame_range'
    severity = 'warning'

    def run(self, shot_node, config, platform_config=None, **kwargs):
        from core.validator import CheckResult

        if not MAYA_AVAILABLE:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity='info',
                message='Skipped (no Maya)',
                details={},
            )

        # Get shot frame range from node
        try:
            shot_range = shot_node.get_frame_range()
        except Exception as exc:
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity=self.severity,
                message='Could not read shot frame range: %s' % exc,
                details={},
            )

        if not shot_range or shot_range[0] is None or shot_range[1] is None:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity='info',
                message='No frame range set on shot node — skipping check',
                details={},
            )

        shot_start = float(shot_range[0])
        shot_end = float(shot_range[1])

        # Get Maya playback range
        try:
            maya_start = cmds.playbackOptions(q=True, min=True)
            maya_end = cmds.playbackOptions(q=True, max=True)
        except Exception as exc:
            return CheckResult(
                check_name=self.name,
                passed=False,
                severity=self.severity,
                message='Could not query Maya playback options: %s' % exc,
                details={},
            )

        shot_range_tuple = (shot_start, shot_end)
        maya_range_tuple = (maya_start, maya_end)

        if shot_start == maya_start and shot_end == maya_end:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity=self.severity,
                message='Frame range matches: %g-%g' % (shot_start, shot_end),
                details={
                    'shot_range': shot_range_tuple,
                    'maya_range': maya_range_tuple,
                },
            )

        return CheckResult(
            check_name=self.name,
            passed=False,
            severity=self.severity,
            message='Frame range mismatch — shot: %g-%g, Maya: %g-%g' % (
                shot_start, shot_end, maya_start, maya_end,
            ),
            details={
                'shot_range': shot_range_tuple,
                'maya_range': maya_range_tuple,
            },
        )
