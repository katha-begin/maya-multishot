"""
Gaffer Chain Operations.

Provides operations for:
- Building gaffer chains (Master → Sequence → Shot)
- Validating chain integrity
- Getting chain statistics and information
"""

try:
    import maya.cmds as cmds
except ImportError:
    cmds = None

from ..nodes.wrappers.gaffer import CTXLightGafferNode


class ChainOperations(object):
    """Operations for gaffer chain management.
    
    Provides utilities for building, validating, and analyzing gaffer chains.
    """
    
    @staticmethod
    def build_gaffer_chain(master_name='Master', sequence_name=None, shot_name=None):
        """Build a gaffer chain: Master → Sequence → Shot.
        
        Creates gaffers and connects them in a hierarchy. If gaffers already exist,
        uses existing ones.
        
        Args:
            master_name (str): Master gaffer name (default: 'Master')
            sequence_name (str, optional): Sequence gaffer name (e.g., 'sq0070')
            shot_name (str, optional): Shot gaffer name (e.g., 'SH0010')
            
        Returns:
            dict: Created/found gaffers:
                {
                    'master': CTXLightGafferNode,
                    'sequence': CTXLightGafferNode or None,
                    'shot': CTXLightGafferNode or None
                }
                
        Raises:
            RuntimeError: If Maya is not available
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")
        
        result = {
            'master': None,
            'sequence': None,
            'shot': None
        }
        
        # Create or find master gaffer
        master = ChainOperations._find_or_create_gaffer(
            master_name, 'master', scope_code=''
        )
        result['master'] = master
        
        # Create or find sequence gaffer if requested
        if sequence_name:
            sequence = ChainOperations._find_or_create_gaffer(
                sequence_name, 'sequence', scope_code=sequence_name
            )
            sequence.set_parent_gaffer(master)
            result['sequence'] = sequence
            
            # Create or find shot gaffer if requested
            if shot_name:
                shot = ChainOperations._find_or_create_gaffer(
                    shot_name, 'shot', scope_code=shot_name
                )
                shot.set_parent_gaffer(sequence)
                result['shot'] = shot
        
        elif shot_name:
            # Shot without sequence - connect directly to master
            shot = ChainOperations._find_or_create_gaffer(
                shot_name, 'shot', scope_code=shot_name
            )
            shot.set_parent_gaffer(master)
            result['shot'] = shot
        
        return result
    
    @staticmethod
    def _find_or_create_gaffer(gaffer_name, gaffer_type, scope_code):
        """Find existing gaffer or create new one.
        
        Args:
            gaffer_name (str): Gaffer name
            gaffer_type (str): Gaffer type (master/sequence/shot/custom)
            scope_code (str): Scope code
            
        Returns:
            CTXLightGafferNode: Gaffer wrapper
        """
        # Search for existing gaffer with this name
        all_nodes = cmds.ls(type='network')
        
        for node in all_nodes:
            # Check if it's a CTX_LightGaffer
            if cmds.attributeQuery('ctx_type', node=node, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(node))
                if node_type == 'CTX_LightGaffer':
                    # Check if name matches
                    if cmds.attributeQuery('gafferName', node=node, exists=True):
                        existing_name = cmds.getAttr('{}.gafferName'.format(node))
                        if existing_name == gaffer_name:
                            return CTXLightGafferNode(node)
        
        # Not found, create new
        return CTXLightGafferNode.create(
            gafferName=gaffer_name,
            gafferType=gaffer_type,
            scopeCode=scope_code,
            enabled=True
        )
    
    @staticmethod
    def validate_chain(gaffer):
        """Validate gaffer chain integrity.
        
        Checks for:
        - Circular references
        - Broken connections
        - Disabled gaffers in chain
        
        Args:
            gaffer (CTXLightGafferNode or str): Gaffer to validate from
            
        Returns:
            dict: Validation results:
                {
                    'valid': bool,
                    'errors': list of error messages,
                    'warnings': list of warning messages,
                    'chain_length': int
                }
        """
        # Convert to wrapper if needed
        if isinstance(gaffer, str):
            gaffer = CTXLightGafferNode(gaffer)
        
        errors = []
        warnings = []
        
        # Build chain and check for circular references
        try:
            chain = gaffer.build_chain()
            chain_length = len(chain)
            
            # Check for duplicates (circular reference)
            seen_nodes = set()
            for gaffer_node in chain:
                if gaffer_node.node_name in seen_nodes:
                    errors.append("Circular reference detected: {}".format(gaffer_node.node_name))
                seen_nodes.add(gaffer_node.node_name)
            
            # Check for disabled gaffers
            for gaffer_node in chain:
                if not gaffer_node.is_enabled():
                    warnings.append("Gaffer '{}' is disabled".format(gaffer_node.get_gaffer_name()))
            
        except Exception as e:
            errors.append("Failed to build chain: {}".format(e))
            chain_length = 0
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'chain_length': chain_length
        }

    @staticmethod
    def get_chain_info(gaffer):
        """Get detailed information about a gaffer chain.

        Args:
            gaffer (CTXLightGafferNode or str): Gaffer to analyze

        Returns:
            dict: Chain information:
                {
                    'chain': [
                        {
                            'name': str,
                            'type': str,
                            'scope': str,
                            'enabled': bool,
                            'light_count': int,
                            'direct_light_count': int,
                            'node': str
                        },
                        ...
                    ],
                    'total_lights': int,
                    'unique_lights': set of light names,
                    'chain_length': int
                }
        """
        # Convert to wrapper if needed
        if isinstance(gaffer, str):
            gaffer = CTXLightGafferNode(gaffer)

        chain = gaffer.build_chain()

        chain_info = []
        all_lights = set()

        for gaffer_node in chain:
            # Get direct lights
            direct_lights = gaffer_node.get_lights()
            direct_light_names = [ctx.get_light_name() for ctx in direct_lights]

            # Get all lights (direct + inherited)
            from .manager import GafferManager
            all_lights_in_gaffer = GafferManager.get_lights_in_gaffer(gaffer_node, include_inherited=True)

            # Add to unique lights set
            for light_info in all_lights_in_gaffer:
                all_lights.add(light_info['name'])

            chain_info.append({
                'name': gaffer_node.get_gaffer_name(),
                'type': gaffer_node.get_gaffer_type(),
                'scope': gaffer_node.get_attribute('scopeCode'),
                'enabled': gaffer_node.is_enabled(),
                'light_count': len(all_lights_in_gaffer),
                'direct_light_count': len(direct_lights),
                'node': gaffer_node.node_name
            })

        return {
            'chain': chain_info,
            'total_lights': len(all_lights),
            'unique_lights': all_lights,
            'chain_length': len(chain)
        }

    @staticmethod
    def find_gaffer_by_name(gaffer_name):
        """Find a gaffer node by its gaffer name.

        Args:
            gaffer_name (str): Gaffer name to search for

        Returns:
            CTXLightGafferNode or None: Found gaffer wrapper, or None if not found

        Raises:
            RuntimeError: If Maya is not available
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        # Search all network nodes
        all_nodes = cmds.ls(type='network')

        for node in all_nodes:
            # Check if it's a CTX_LightGaffer
            if cmds.attributeQuery('ctx_type', node=node, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(node))
                if node_type == 'CTX_LightGaffer':
                    # Check if name matches
                    if cmds.attributeQuery('gafferName', node=node, exists=True):
                        existing_name = cmds.getAttr('{}.gafferName'.format(node))
                        if existing_name == gaffer_name:
                            return CTXLightGafferNode(node)

        return None

    @staticmethod
    def list_all_gaffers():
        """List all gaffer nodes in the scene.

        Returns:
            list: List of dicts with gaffer information:
                [
                    {
                        'name': str,
                        'type': str,
                        'scope': str,
                        'enabled': bool,
                        'node': str,
                        'wrapper': CTXLightGafferNode
                    },
                    ...
                ]

        Raises:
            RuntimeError: If Maya is not available
        """
        if cmds is None:
            raise RuntimeError("Maya is not available")

        gaffers = []

        # Search all network nodes
        all_nodes = cmds.ls(type='network')

        for node in all_nodes:
            # Check if it's a CTX_LightGaffer
            if cmds.attributeQuery('ctx_type', node=node, exists=True):
                node_type = cmds.getAttr('{}.ctx_type'.format(node))
                if node_type == 'CTX_LightGaffer':
                    wrapper = CTXLightGafferNode(node)
                    gaffers.append({
                        'name': wrapper.get_gaffer_name(),
                        'type': wrapper.get_gaffer_type(),
                        'scope': wrapper.get_attribute('scopeCode'),
                        'enabled': wrapper.is_enabled(),
                        'node': node,
                        'wrapper': wrapper
                    })

        return gaffers

