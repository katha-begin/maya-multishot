"""
Schema definition for CTX_Asset node.

The asset node stores asset-specific metadata and file paths for a particular
asset instance in a shot.
"""

from ..base import NodeSchema


class CTXAssetSchema(NodeSchema):
    """Schema for CTX_Asset node.
    
    An asset node provides:
    - Asset identification (type, name, variant)
    - File path and version tracking
    - Namespace management
    - Parent shot connection
    """
    
    NODE_TYPE = "network"
    NODE_PREFIX = "CTX_Asset"
    CATEGORY = "Context"
    DESCRIPTION = "Asset metadata and file path management"
    
    ATTRIBUTES = {
        # Node identification
        'ctx_type': {
            'type': 'string',
            'default': 'CTX_Asset',
            'description': 'CTX node type identifier'
        },
        
        # Asset identity
        'asset_type': {
            'type': 'string',
            'default': '',
            'description': 'Asset type (e.g., "CHAR", "PROP", "CAM")'
        },
        
        'asset_name': {
            'type': 'string',
            'default': '',
            'description': 'Asset name (e.g., "CatStompie")'
        },
        
        'variant': {
            'type': 'string',
            'default': '001',
            'description': 'Asset variant (e.g., "001")'
        },
        
        # Maya namespace
        'namespace': {
            'type': 'string',
            'default': '',
            'description': 'Maya namespace for this asset instance'
        },
        
        # File information
        'file_path': {
            'type': 'string',
            'default': '',
            'description': 'Path to asset file (resolved/cached path)'
        },

        'template': {
            'type': 'string',
            'default': '',
            'description': 'Path template with tokens (e.g., "$projRoot$project/$sceneBase/...")'
        },

        'extension': {
            'type': 'string',
            'default': '',
            'description': 'File extension (e.g., "abc", "ma", "mb")'
        },

        'version': {
            'type': 'string',
            'default': '',
            'description': 'Asset version (e.g., "v003")'
        },

        # Status
        'is_loaded': {
            'type': 'bool',
            'default': False,
            'description': 'Whether asset is currently loaded in scene'
        },
    }

    CONNECTIONS = {
        # NOTE: parentShot removed - redundant with unidirectional pattern
        # To query parent shot: cmds.listConnections("asset.message", source=False, destination=True, type='network')
        # Then filter for ctx_type == 'CTX_Shot'
    }

