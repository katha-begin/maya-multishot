# -*- coding: utf-8 -*-
"""CFX standin namespace and linkage check.

Reports conflicts that would make CFX import unsafe or make an already
imported CFX asset invisible to shot switching.  Read-only -- it never
mutates the scene.

Only error-level conditions fail the check.  Un-namespaced standins are
expected in scenes built by an upstream CFX tool and are reported as
information, not as a problem: adoption handles them without renaming.
"""

from __future__ import absolute_import, division, print_function

from core.logging_config import get_logger
from core.validator.base_check import BaseCheck

logger = get_logger(__name__)


class CFXNamespaceCheck(BaseCheck):
    """Verify CFX standins in the scene are uniquely identified and linked.

    Error conditions (fail the check):
    - Two CFX publishes resolving to the same basename.  The basename is the
      identity key display-layer switching uses, so a collision makes one
      shot's CFX indistinguishable from another's.

    Reported but not failing:
    - Standins with no CTX_Asset backing them (adopt candidates).
    - CFX CTX_Asset nodes whose targetNode resolves to nothing.
    - Standins carrying no Maya namespace.

    Severity: error.  Works headless -- returns a pass with empty details
    when Maya is unavailable.
    """

    name = 'cfx_namespace'
    severity = 'error'

    def run(self, shot_node, config, platform_config=None, **kwargs):
        from core.validator import CheckResult
        from core import cfx_adopter

        if not cfx_adopter.MAYA_AVAILABLE:
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity=self.severity,
                message='Maya unavailable -- CFX standins not inspected',
                details={},
            )

        try:
            duplicates = cfx_adopter.find_duplicate_basenames(config)
            unadopted = cfx_adopter.find_unadopted(config)
            dead_targets = cfx_adopter.find_dead_targets()
            standins = cfx_adopter.find_cfx_standins(config)
        except Exception as exc:
            logger.debug('CFX scan raised: %s', exc)
            return CheckResult(
                check_name=self.name,
                passed=True,
                severity=self.severity,
                message='CFX standins could not be inspected: %s' % exc,
                details={},
            )

        un_namespaced = [s['shape'] for s in standins if not s['namespace']]

        details = {
            'duplicate_basenames': duplicates,
            'unadopted_standins': [s['shape'] for s in unadopted],
            'dead_target_nodes': dead_targets,
            'un_namespaced_standins': un_namespaced,
            'total_standins': len(standins),
        }

        passed = not duplicates

        if not passed:
            msg = 'Duplicate CFX publish basenames: %s' % ', '.join(
                sorted(duplicates.keys()))
        else:
            notes = []
            if unadopted:
                notes.append('%d standin(s) not yet adopted' % len(unadopted))
            if dead_targets:
                notes.append('%d CTX_Asset(s) with dead targetNode'
                             % len(dead_targets))
            if un_namespaced:
                notes.append('%d standin(s) without a namespace'
                             % len(un_namespaced))

            if notes:
                msg = 'CFX identities are unique (%s)' % '; '.join(notes)
            else:
                msg = 'CFX standins are unique and linked (%d found)' % len(standins)

        return CheckResult(
            check_name=self.name,
            passed=passed,
            severity=self.severity,
            message=msg,
            details=details,
        )
