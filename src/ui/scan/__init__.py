# Scan View Components
"""
Scan UI components for ClamUI.

This package contains the modular scan interface:
- ProfileSelector: Profile dropdown and management
- TargetSelector: File/folder selection with drag-drop
- ScanController: Scan orchestration logic
- ScanProgressWidget: Progress bar and live stats
- ScanResultsWidget: View results button
- ScanView: Main composition root
"""

from .scan_view import ScanView

__all__ = ["ScanView"]
