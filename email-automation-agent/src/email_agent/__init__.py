"""
Email Automation Agent Package

This package contains the core components for the email automation agent.
"""

from .agent import EmailAgent
from .email_client import EmailClient
from .ai_processor import AIProcessor
from .config import Config

__version__ = "0.1.0"
__author__ = "Email Automation Agent"

__all__ = [
    "EmailAgent",
    "EmailClient", 
    "AIProcessor",
    "Config"
]