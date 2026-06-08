#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logging utilities for The Eyes project.

This module provides functions for setting up and configuring logging.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logger(name: str, level: int = logging.INFO, 
                 log_file: Optional[str] = None, 
                 max_size: int = 10*1024*1024,  # 10 MB
                 backup_count: int = 5) -> logging.Logger:
    """
    Set up a logger with console and optionally file output.
    
    Args:
        name: Name of the logger
        level: Logging level
        log_file: Path to log file (optional)
        max_size: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates when reconfiguring
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatters
    console_format = logging.Formatter('%(asctime)s - %(levelname)-8s - %(name)s - %(message)s')
    file_format = logging.Formatter('%(asctime)s - %(levelname)-8s - %(name)s - %(filename)s:%(lineno)d - %(message)s')
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_format)
    console_handler.setLevel(level)
    logger.addHandler(console_handler)
    
    # Create file handler if log file is specified
    if log_file:
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        # Create rotating file handler
        file_handler = RotatingFileHandler(
            log_file, maxBytes=max_size, backupCount=backup_count)
        file_handler.setFormatter(file_format)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)
    
    return logger


def add_file_handler(logger: logging.Logger, 
                    log_file: str, 
                    level: int = logging.INFO,
                    max_size: int = 10*1024*1024,  # 10 MB
                    backup_count: int = 5) -> None:
    """
    Add a file handler to an existing logger.
    
    Args:
        logger: Logger to add handler to
        log_file: Path to log file
        level: Logging level for the file handler
        max_size: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
    """
    # Create directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        
    # Create formatter
    file_format = logging.Formatter('%(asctime)s - %(levelname)-8s - %(name)s - %(filename)s:%(lineno)d - %(message)s')
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_size, backupCount=backup_count)
    file_handler.setFormatter(file_format)
    file_handler.setLevel(level)
    
    # Add handler to logger
    logger.addHandler(file_handler)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get a logger with the specified name and level.
    
    Args:
        name: Name of the logger
        level: Logging level
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # If logger has no handlers, add a console handler
    if not logger.handlers:
        console_format = logging.Formatter('%(asctime)s - %(levelname)-8s - %(name)s - %(message)s')
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_format)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)
    
    return logger 