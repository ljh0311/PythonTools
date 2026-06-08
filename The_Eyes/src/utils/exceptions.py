#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Custom exceptions for The Eyes project.

This module defines custom exceptions used throughout the project
to provide clear error handling.
"""


class TheEyesError(Exception):
    """Base exception class for all errors in The Eyes project."""
    pass


class CameraError(TheEyesError):
    """Exception raised for errors related to camera operations."""
    pass


class CalibrationError(TheEyesError):
    """Exception raised for errors during camera calibration."""
    pass


class ImageProcessingError(TheEyesError):
    """Exception raised for errors during image processing."""
    pass


class FeatureMatchingError(TheEyesError):
    """Exception raised for errors during feature extraction or matching."""
    pass


class ReconstructionError(TheEyesError):
    """Exception raised for errors during 3D reconstruction."""
    pass


class RenderingError(TheEyesError):
    """Exception raised for errors during 3D rendering."""
    pass


class ConfigurationError(TheEyesError):
    """Exception raised for errors in configuration."""
    pass 