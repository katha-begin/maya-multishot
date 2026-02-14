# -*- coding: utf-8 -*-
"""Configuration validation and error handling.

This module provides comprehensive validation for project configuration,
including schema validation, required field checks, and migration support.

Author: Context Variables Pipeline
Date: 2026-02-14
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


class ConfigValidationError(Exception):
    """Exception raised for configuration validation errors."""
    pass


class ConfigValidator(object):
    """Validates project configuration.
    
    This class provides utilities to:
    - Validate JSON schema
    - Check for required fields
    - Validate field values
    - Provide detailed error messages
    - Support config migration
    - Log warnings for deprecated fields
    
    Example:
        >>> from config.config_validator import ConfigValidator
        >>> 
        >>> validator = ConfigValidator()
        >>> is_valid, errors = validator.validate(config_data)
        >>> if not is_valid:
        ...     for error in errors:
        ...         print(error)
    """
    
    # Required top-level keys
    REQUIRED_KEYS = ['version', 'project', 'roots', 'static_paths', 'templates', 'patterns']
    
    # Supported versions
    SUPPORTED_VERSIONS = ['1.0', '1.1']
    
    # Required project fields
    REQUIRED_PROJECT_FIELDS = ['name', 'code']
    
    # Deprecated fields (version -> list of deprecated fields)
    DEPRECATED_FIELDS = {
        '1.0': [],
        '1.1': []
    }
    
    def __init__(self):
        """Initialize validator."""
        self.errors = []
        self.warnings = []
    
    def validate(self, config_data):
        """Validate configuration data.
        
        Args:
            config_data (dict): Configuration dictionary
        
        Returns:
            tuple: (is_valid, errors) where is_valid is bool and errors is list of strings
        """
        self.errors = []
        self.warnings = []
        
        # Validate top-level structure
        self._validate_required_keys(config_data)
        
        # Validate version
        if 'version' in config_data:
            self._validate_version(config_data['version'])
        
        # Validate project section
        if 'project' in config_data:
            self._validate_project(config_data['project'])
        
        # Validate roots section
        if 'roots' in config_data:
            self._validate_roots(config_data['roots'])
        
        # Validate static_paths section
        if 'static_paths' in config_data:
            self._validate_static_paths(config_data['static_paths'])
        
        # Validate templates section
        if 'templates' in config_data:
            self._validate_templates(config_data['templates'])
        
        # Validate patterns section
        if 'patterns' in config_data:
            self._validate_patterns(config_data['patterns'])
        
        # Check for deprecated fields
        if 'version' in config_data:
            self._check_deprecated_fields(config_data, config_data['version'])
        
        return (len(self.errors) == 0, self.errors)
    
    def _validate_required_keys(self, config_data):
        """Validate that all required top-level keys are present.
        
        Args:
            config_data (dict): Configuration dictionary
        """
        for key in self.REQUIRED_KEYS:
            if key not in config_data:
                self.errors.append(
                    "Missing required key: '{}'".format(key)
                )
    
    def _validate_version(self, version):
        """Validate version field.
        
        Args:
            version (str): Version string
        """
        if not isinstance(version, str):
            self.errors.append(
                "Version must be a string, got {}".format(type(version).__name__)
            )
            return
        
        if version not in self.SUPPORTED_VERSIONS:
            self.errors.append(
                "Unsupported version '{}'. Supported versions: {}".format(
                    version, ', '.join(self.SUPPORTED_VERSIONS)
                )
            )
    
    def _validate_project(self, project):
        """Validate project section.
        
        Args:
            project (dict): Project dictionary
        """
        if not isinstance(project, dict):
            self.errors.append(
                "Project must be a dictionary, got {}".format(type(project).__name__)
            )
            return
        
        # Check required fields
        for field in self.REQUIRED_PROJECT_FIELDS:
            if field not in project:
                self.errors.append(
                    "Missing required project field: '{}'".format(field)
                )

        # Validate field types
        if 'name' in project and not isinstance(project['name'], str):
            self.errors.append(
                "Project name must be a string, got {}".format(type(project['name']).__name__)
            )

        if 'code' in project and not isinstance(project['code'], str):
            self.errors.append(
                "Project code must be a string, got {}".format(type(project['code']).__name__)
            )

    def _validate_roots(self, roots):
        """Validate roots section.

        Args:
            roots (dict): Roots dictionary
        """
        if not isinstance(roots, dict):
            self.errors.append(
                "Roots must be a dictionary, got {}".format(type(roots).__name__)
            )
            return

        if len(roots) == 0:
            self.errors.append("Roots section is empty")

        # Validate each root
        for root_name, root_path in roots.items():
            if not isinstance(root_path, str):
                self.errors.append(
                    "Root '{}' must be a string, got {}".format(
                        root_name, type(root_path).__name__
                    )
                )

    def _validate_static_paths(self, static_paths):
        """Validate static_paths section.

        Args:
            static_paths (dict): Static paths dictionary
        """
        if not isinstance(static_paths, dict):
            self.errors.append(
                "Static paths must be a dictionary, got {}".format(type(static_paths).__name__)
            )
            return

        # Validate each static path
        for path_name, path_value in static_paths.items():
            if not isinstance(path_value, str):
                self.errors.append(
                    "Static path '{}' must be a string, got {}".format(
                        path_name, type(path_value).__name__
                    )
                )

    def _validate_templates(self, templates):
        """Validate templates section.

        Args:
            templates (dict): Templates dictionary
        """
        if not isinstance(templates, dict):
            self.errors.append(
                "Templates must be a dictionary, got {}".format(type(templates).__name__)
            )
            return

        # Validate each template
        for template_name, template_value in templates.items():
            if not isinstance(template_value, str):
                self.errors.append(
                    "Template '{}' must be a string, got {}".format(
                        template_name, type(template_value).__name__
                    )
                )
            elif not template_value.strip():
                self.errors.append(
                    "Template '{}' is empty".format(template_name)
                )

    def _validate_patterns(self, patterns):
        """Validate patterns section.

        Args:
            patterns (dict): Patterns dictionary
        """
        if not isinstance(patterns, dict):
            self.errors.append(
                "Patterns must be a dictionary, got {}".format(type(patterns).__name__)
            )
            return

        # Validate each pattern
        import re
        for pattern_name, pattern_value in patterns.items():
            if not isinstance(pattern_value, str):
                self.errors.append(
                    "Pattern '{}' must be a string, got {}".format(
                        pattern_name, type(pattern_value).__name__
                    )
                )
            elif not pattern_value.strip():
                self.errors.append(
                    "Pattern '{}' is empty".format(pattern_name)
                )
            else:
                # Try to compile the pattern
                try:
                    re.compile(pattern_value)
                except re.error as e:
                    self.errors.append(
                        "Pattern '{}' has invalid regex syntax: {}".format(
                            pattern_name, str(e)
                        )
                    )

    def _check_deprecated_fields(self, config_data, version):
        """Check for deprecated fields and log warnings.

        Args:
            config_data (dict): Configuration dictionary
            version (str): Configuration version
        """
        deprecated = self.DEPRECATED_FIELDS.get(version, [])

        for field in deprecated:
            if field in config_data:
                self.warnings.append(
                    "Field '{}' is deprecated in version {}".format(field, version)
                )

    def get_warnings(self):
        """Get validation warnings.

        Returns:
            list: List of warning messages
        """
        return self.warnings

    def migrate_config(self, config_data, target_version):
        """Migrate configuration to target version.

        Args:
            config_data (dict): Configuration dictionary
            target_version (str): Target version

        Returns:
            dict: Migrated configuration

        Raises:
            ConfigValidationError: If migration is not possible
        """
        if target_version not in self.SUPPORTED_VERSIONS:
            raise ConfigValidationError(
                "Cannot migrate to unsupported version '{}'".format(target_version)
            )

        current_version = config_data.get('version', '1.0')

        if current_version == target_version:
            return config_data

        # For now, just update the version field
        # In the future, add migration logic here
        migrated = config_data.copy()
        migrated['version'] = target_version

        return migrated

