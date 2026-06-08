#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration utilities for The Eyes project.

This module provides functions for loading and validating configuration files.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

from src.utils.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dictionary containing configuration parameters
        
    Raises:
        ConfigurationError: If the configuration file cannot be loaded or is invalid
    """
    try:
        if not os.path.exists(config_path):
            logger.warning(f"Configuration file not found: {config_path}")
            return create_default_config(config_path)
            
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        if config is None:
            config = {}
            
        # Ensure basic structure exists
        if 'appearance' not in config:
            config['appearance'] = {'dark_mode': False, 'theme': 'clam'}
        if 'cameras' not in config:
            config['cameras'] = {}
        if 'display' not in config:
            config['display'] = {
                'show_fps': True,
                'default_layout': 'grid',
                'default_resolution': '640x480'
            }
        if 'system' not in config:
            config['system'] = {
                'fps_limit': 30,
                'gc_interval': 60,
                'log_level': 'INFO'
            }
        if 'paths' not in config:
            config['paths'] = {
                'screenshots': 'screenshots',
                'models': 'models',
                'data': 'data',
                'logs': 'logs'
            }
            
        return config
        
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return create_default_config(config_path)


def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate the configuration dictionary.
    
    Args:
        config: Configuration dictionary to validate
        
    Raises:
        ConfigurationError: If the configuration is invalid
    """
    logger = logging.getLogger("the_eyes.config")
    
    # Check for required sections
    required_sections = ['cameras', 'image_processing', 'feature_matching', 'reconstruction', 'rendering']
    for section in required_sections:
        if section not in config:
            logger.warning(f"Missing required configuration section: {section}, using defaults")
            config[section] = {}
    
    # Validate camera configuration
    if not config['cameras']:
        logger.warning("No cameras configured, adding default webcam configuration")
        config['cameras'] = {
            'cam0': {'type': 'webcam', 'id': 0, 'width': 640, 'height': 480, 'fps': 30}
        }


def create_default_config(config_path: str) -> Dict[str, Any]:
    """
    Create a default configuration file.
    
    Args:
        config_path: Path where to save the configuration
        
    Returns:
        Dictionary containing default configuration parameters
    """
    logger.info("Creating default configuration")
    
    config = {
        'appearance': {
            'dark_mode': False,
            'theme': 'clam'
        },
        'cameras': {
            'cam0': {
                'type': 'webcam',
                'id': 0,
                'width': 640,
                'height': 480,
                'fps': 30
            }
        },
        'display': {
            'show_fps': True,
            'default_layout': 'grid',
            'default_resolution': '640x480'
        },
        'system': {
            'fps_limit': 30,
            'gc_interval': 60,
            'log_level': 'INFO'
        },
        'paths': {
            'screenshots': 'screenshots',
            'models': 'models',
            'data': 'data',
            'logs': 'logs'
        },
        'calibration': {
            'pattern_size': [9, 6],
            'square_size': 0.025,  # in meters
            'num_images': 10
        },
        'image_processing': {
            'resize': {'width': 640, 'height': 480},
            'grayscale': True,
            'blur': {'kernel_size': 3},
            'clahe': {'clip_limit': 2.0, 'tile_grid_size': [8, 8]}
        },
        'feature_matching': {
            'detector': 'sift',
            'descriptor': 'sift',
            'matcher': 'flann',
            'max_features': 2000,
            'min_matches': 10,
            'lowe_ratio': 0.7
        },
        'reconstruction': {
            'method': 'sfm',  # structure from motion
            'triangulation': 'opencv',
            'bundle_adjustment': True,
            'min_depth': 0.1,
            'max_depth': 10.0
        },
        'rendering': {
            'mesh_method': 'poisson',
            'point_size': 2.0,
            'mesh_resolution': 8,
            'texture_mapping': True,
            'viewer': 'open3d'
        }
    }
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Save default configuration
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2, default=str)
            
        logger.info(f"Created default configuration at {config_path}")
        
    except Exception as e:
        logger.error(f"Error creating default configuration: {e}")
        
    return config


def save_config(config: Dict[str, Any], config_path: str) -> None:
    """
    Save configuration to a JSON file.
    
    Args:
        config: Configuration dictionary to save
        config_path: Path to save the configuration file
        
    Raises:
        ConfigurationError: If the configuration cannot be saved
    """
    logger = logging.getLogger("the_eyes.config")
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Save configuration
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2, default=str)
            
        logger.info(f"Saved configuration to {config_path}")
        
    except Exception as e:
        logger.error(f"Error saving configuration to {config_path}: {e}")
        raise ConfigurationError(f"Failed to save configuration: {e}")


def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two configuration dictionaries, with override taking precedence.
    
    Args:
        base_config: Base configuration dictionary
        override_config: Configuration dictionary to override base values
        
    Returns:
        Merged configuration dictionary
    """
    merged = base_config.copy()
    
    for key, value in override_config.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            # Recursively merge nested dictionaries
            merged[key] = merge_configs(merged[key], value)
        else:
            # Override or add value
            merged[key] = value
            
    return merged 