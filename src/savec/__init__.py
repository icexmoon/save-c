"""
save-c — 将 C 盘目录迁移到 D 盘并创建软链接，安全释放 C 盘空间。
"""

__version__ = "1.1.0"

from savec.core import move_and_link, DryRunError
from savec.scan import ScanEntry, scan_and_select_interactive
from savec.config import SavecConfig, load_config, save_config, open_config_gui

__all__ = [
    "move_and_link", "DryRunError",
    "ScanEntry", "scan_and_select_interactive",
    "SavecConfig", "load_config", "save_config", "open_config_gui",
]
