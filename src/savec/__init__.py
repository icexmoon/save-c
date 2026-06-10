"""
save-c — 将 C 盘目录迁移到 D 盘并创建软链接，安全释放 C 盘空间。
"""

__version__ = "1.0.0"

from savec.core import move_and_link, DryRunError
from savec.scan import ScanEntry, scan_and_select_interactive

__all__ = ["move_and_link", "DryRunError", "ScanEntry", "scan_and_select_interactive"]
