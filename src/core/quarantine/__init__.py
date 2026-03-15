# ClamUI Quarantine Module
"""
Quarantine management module for ClamUI providing secure threat isolation.
Handles moving detected threats to quarantine, metadata persistence, and restoration.
"""

from .connection_pool import ConnectionPool
from .database import QuarantineDatabase, QuarantineEntry
from .file_handler import (
    FileOperationResult,
    FileOperationStatus,
    SecureFileHandler,
)
from .manager import QuarantineManager, QuarantineResult, QuarantineStatus

__all__ = [
    "ConnectionPool",
    "FileOperationResult",
    "FileOperationStatus",
    "QuarantineDatabase",
    "QuarantineEntry",
    "QuarantineManager",
    "QuarantineResult",
    "QuarantineStatus",
    "SecureFileHandler",
]
