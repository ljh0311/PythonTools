"""Shared pytest fixtures for SmartAI tests."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fixtures.config import TestConfig, build_config_dict


@pytest.fixture
def navigation_config():
    """Headless navigation config with camera disabled."""
    return TestConfig(enable_camera=False)


@pytest.fixture
def navigation_config_dict(navigation_config):
    """Config dict for pathfinder and robot state."""
    return build_config_dict(navigation_config)
