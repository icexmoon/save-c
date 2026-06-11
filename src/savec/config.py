"""
配置管理：数据模型、文件 I/O、GUI 配置窗口。
"""

from __future__ import annotations

import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from dataclasses import dataclass, asdict, field

# 配置文件路径（%APPDATA%\savec\config.json）
CONFIG_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "savec",
)
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


@dataclass
class SavecConfig:
    """应用配置。"""
    scan_dirs: list[str] = field(default_factory=lambda: [os.path.expanduser("~"), os.path.join(os.path.expanduser("~"), "AppData", "Local"), os.path.join(os.path.expanduser("~"), "AppData", "Roaming")])
    cache_ttl: int = 600
    min_size_mb: int = 500
    dest_dir: str = "D:\\moved_from_c"
    skip_dirs: list[str] = field(default_factory=lambda: [os.path.join(os.path.expanduser("~"), "AppData"), os.path.join(os.path.expanduser("~"), "OneDrive")])


def load_config() -> SavecConfig:
    """加载配置，文件不存在或损坏时返回默认值。"""
    if not os.path.isfile(CONFIG_PATH):
        return SavecConfig()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SavecConfig(**data)
    except (json.JSONDecodeError, KeyError, OSError):
        return SavecConfig()


def save_config(cfg: SavecConfig) -> None:
    """保存配置到文件。"""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)


def open_config_gui() -> None:
    """打开 GUI 配置窗口，保存后自动写入文件。"""
    cfg = load_config()
    root = tk.Tk()
    root.title("save-c 配置")
    root.geometry("580x620")
    root.resizable(False, False)

    # ── 扫描目录列表 ──
    tk.Label(root, text="扫描目录（可添加多个）:", anchor="w").pack(fill="x", padx=12, pady=(12, 2))
    dirs_frame = tk.Frame(root)
    dirs_frame.pack(fill="x", padx=12, pady=2)

    listbox = tk.Listbox(dirs_frame, height=5)
    listbox.pack(side="left", fill="x", expand=True)
    scrollbar = tk.Scrollbar(dirs_frame, orient="vertical")
    scrollbar.pack(side="right", fill="y")
    listbox.config(yscrollcommand=scrollbar.set)
    scrollbar.config(command=listbox.yview)
    for d in cfg.scan_dirs:
        listbox.insert("end", d)

    btn_frame = tk.Frame(root)
    btn_frame.pack(fill="x", padx=12, pady=4)

    def add_dir():
        d = filedialog.askdirectory(title="选择要扫描的目录")
        if d:
            listbox.insert("end", os.path.normpath(d))

    def remove_dir():
        sel = listbox.curselection()
        if sel:
            if messagebox.askyesno("确认", f"删除扫描目录:\n{listbox.get(sel[0])}?"):
                listbox.delete(sel[0])

    tk.Button(btn_frame, text="+ 添加目录", command=add_dir, width=12).pack(side="left", padx=(0, 6))
    tk.Button(btn_frame, text="X 删除", command=remove_dir, width=8).pack(side="left")

    # -- 跳过目录列表 --
    tk.Label(root, text="跳过以下目录（不统计容量）:", anchor="w").pack(fill="x", padx=12, pady=(14, 2))
    skip_frame = tk.Frame(root)
    skip_frame.pack(fill="x", padx=12, pady=2)

    skip_listbox = tk.Listbox(skip_frame, height=3)
    skip_listbox.pack(side="left", fill="x", expand=True)
    skip_scrollbar = tk.Scrollbar(skip_frame, orient="vertical")
    skip_scrollbar.pack(side="right", fill="y")
    skip_listbox.config(yscrollcommand=skip_scrollbar.set)
    skip_scrollbar.config(command=skip_listbox.yview)
    for d in cfg.skip_dirs:
        skip_listbox.insert("end", d)

    skip_btn_frame = tk.Frame(root)
    skip_btn_frame.pack(fill="x", padx=12, pady=4)

    def add_skip():
        d = filedialog.askdirectory(title="选择要跳过的目录")
        if d:
            skip_listbox.insert("end", os.path.normpath(d))
            skip_listbox.insert("end", name)

    def remove_skip():
        sel = skip_listbox.curselection()
        if sel:
            if messagebox.askyesno("确认", "删除跳过目录\n" + skip_listbox.get(sel[0]) + "?"):
                skip_listbox.delete(sel[0])

    tk.Button(skip_btn_frame, text="+ 添加目录", command=add_skip, width=12).pack(side="left", padx=(0, 6))
    tk.Button(skip_btn_frame, text="X 删除", command=remove_skip, width=8).pack(side="left")


    # ── 缓存有效时长 ──
    tk.Label(root, text="缓存有效时长:", anchor="w").pack(fill="x", padx=12, pady=(14, 2))
    ttl_frame = tk.Frame(root)
    ttl_frame.pack(fill="x", padx=12)
    ttl_var = tk.IntVar(value=cfg.cache_ttl // 60)
    ttk.Spinbox(ttl_frame, from_=1, to=120, textvariable=ttl_var, width=6).pack(side="left")
    tk.Label(ttl_frame, text="分钟").pack(side="left", padx=6)

    # ── 大小阈值 ──
    tk.Label(root, text="默认大小阈值（小于该值的目录不在扫描结果中显示）:", anchor="w").pack(fill="x", padx=12, pady=(14, 2))
    size_frame = tk.Frame(root)
    size_frame.pack(fill="x", padx=12)
    size_var = tk.IntVar(value=cfg.min_size_mb)
    ttk.Spinbox(size_frame, from_=0, to=100000, textvariable=size_var, width=8).pack(side="left")
    tk.Label(size_frame, text="MB（0 表示显示全部）").pack(side="left", padx=6)

    # ── 迁移目标目录 ──
    tk.Label(root, text="迁移目标目录:", anchor="w").pack(fill="x", padx=12, pady=(14, 2))
    dest_frame = tk.Frame(root)
    dest_frame.pack(fill="x", padx=12)
    dest_var = tk.StringVar(value=cfg.dest_dir)
    dest_entry = tk.Entry(dest_frame, textvariable=dest_var)
    dest_entry.pack(side="left", fill="x", expand=True)

    def browse_dest():
        d = filedialog.askdirectory(title="选择 D 盘目标根目录", initialdir=dest_var.get())
        if d:
            dest_var.set(os.path.normpath(d))

    tk.Button(dest_frame, text="浏览...", command=browse_dest).pack(side="left", padx=6)

    # ── 操作按钮 ──
    btn_bottom = tk.Frame(root)
    btn_bottom.pack(fill="x", padx=12, pady=(20, 12))
    tk.Button(btn_bottom, text="取消", width=10, command=root.destroy).pack(side="right", padx=(6, 0))
    tk.Button(btn_bottom, text="保存", width=10, command=lambda: _do_save(root, listbox, skip_listbox, ttl_var, size_var, dest_var)).pack(side="right")

    root.mainloop()


def _do_save(root: tk.Tk, listbox: tk.Listbox, skip_listbox: tk.Listbox, ttl_var: tk.IntVar,
             size_var: tk.IntVar, dest_var: tk.StringVar) -> None:
    """收集表单数据并保存。"""
    dirs = list(listbox.get(0, "end"))
    if not dirs:
        messagebox.showerror("错误", "请至少添加一个扫描目录。")
        return
    dest = dest_var.get().strip()
    if not dest:
        messagebox.showerror("错误", "请输入迁移目标目录。")
        return
    cfg = SavecConfig(
        scan_dirs=dirs,
        skip_dirs=list(skip_listbox.get(0, "end")),
        cache_ttl=ttl_var.get() * 60,
        min_size_mb=size_var.get(),
        dest_dir=dest,
    )
    save_config(cfg)
    messagebox.showinfo("完成", "配置已保存。")
    root.destroy()





