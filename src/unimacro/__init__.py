"""Unimacro __init__

Provides a logger for logging throughout unimacro.  Use this instead of a global logger of the 'natlink' root logger.
This lets us set the levels for unimacro differently for debugging, if desired.
"""
import os
import sys

from .logger import unimacro_logger
__version__ = '4.1.4.2'   
 
