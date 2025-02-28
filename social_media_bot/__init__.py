"""
Social Media Bot package for autonomous content curation and posting.
"""

__version__ = "0.1.0"

from .agents import get_database_manager, get_content_curator, get_content_creator
from .main import main

__all__ = [
    'get_database_manager',
    'get_content_curator', 
    'get_content_creator',
    'main'
] 