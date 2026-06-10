"""
扫描 C 盘用户目录，统计可迁移的目录及空间占用。
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from savec.core import DryRunError, move_and_link

# 扫描时忽略的特殊目录（用户主目录下的系统级目录）
SKIP_DIRS = frozenset({"appdata", "onedrive", "documents"})


@dataclass
class ScanEntry:
    """单个扫描结果。"""
    name: str
    path: str
    size_bytes: int
    is_symlink: bool


def format_size(size_bytes: int) -> str:
    """将字节格式化为可读尺寸。"""
    if size_bytes == 0:
        return "    0 B"
    b = float(abs(size_bytes))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024.0:
            return f"{b:>6.1f} {unit}"
        b /= 1024.0
    return f"{b:>6.1f} PB"


def _list_dirs(base_dir: str) -> tuple[list[ScanEntry], int]:
    """列出 base_dir 下的所有子目录，分辨软链接。

    Returns:
        (entries, symlink_count)
    """
    entries: list[ScanEntry] = []
    symlink_count = 0

    try:
        with os.scandir(base_dir) as it:
            for entry in it:
                if not entry.is_dir(follow_symlinks=False):
                    continue
                is_link = os.path.islink(entry.path)
                entries.append(ScanEntry(
                    name=entry.name,
                    path=entry.path,
                    size_bytes=0,
                    is_symlink=is_link,
                ))
                if is_link:
                    symlink_count += 1
    except PermissionError:
        print(f"  [WARN] 无权限访问: {base_dir}")
    except FileNotFoundError:
        print(f"  [X] 目录不存在: {base_dir}")

    return entries, symlink_count


def _calc_dir_size(dirpath: str, *, report_name: str = "") -> int:
    """递归计算目录大小。

    跳过内部软链接子目录，避免重复计算和无限递归。
    """
    total = 0
    try:
        for root, dirs, files in os.walk(dirpath, followlinks=False):
            dirs[:] = [d for d in dirs
                       if not os.path.islink(os.path.join(root, d))]
            for f in files:
                fpath = os.path.join(root, f)
                try:
                    if not os.path.islink(fpath):
                        total += os.path.getsize(fpath)
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


def scan_and_select_interactive(
    base_dir: str,
    *,
    dest_dir: str = "D:\\moved_from_c",
    dry_run: bool = False,
    min_size: int = 500 * 1024 * 1024,
) -> int:
    """扫描、展示、交互式选择并迁移目录。

    Returns:
        0 正常结束；1 出错。
    """
    base_dir = base_dir.rstrip("\\/")
    if not os.path.isdir(base_dir):
        print(f"[X] 目录不存在: {base_dir}")
        return 1

    # ── 1. 列出所有子目录 ──
    print(f"正在扫描 {base_dir} ...")
    all_entries, symlink_count = _list_dirs(base_dir)

    if not all_entries:
        print("  未发现任何子目录。")
        return 0

    # ── 过滤掉不需要扫描的特殊目录 ──
    skip_count = 0
    filtered: list[ScanEntry] = []
    for e in all_entries:
        if e.name.lower() in SKIP_DIRS:
            skip_count += 1
            continue
        filtered.append(e)
    all_entries = filtered

    # ── 额外扫描 AppData\Local 和 AppData\Roaming 下的子目录 ──
    appdata_extra = 0
    for rel in ("AppData\\Local", "AppData\\Roaming"):
        sub_dir = os.path.join(base_dir, rel)
        if os.path.isdir(sub_dir):
            sub_entries, sub_links = _list_dirs(sub_dir)
            for e in sub_entries:
                if not e.is_symlink:
                    e.name = f"{rel}\\{e.name}"
            all_entries.extend(sub_entries)
            symlink_count += sub_links
            appdata_extra += len(sub_entries)

    if not all_entries:
        if skip_count and not appdata_extra:
            print(f"  扫描完成，仅剩余 {skip_count} 个已过滤的目录，无需处理。")
            return 0
        elif not skip_count and not appdata_extra:
            print("  未发现任何子目录。")
            return 0

    if skip_count:
        print(f"  已过滤 {skip_count} 个特殊目录（AppData / OneDrive / Documents）")
    if appdata_extra:
        print(f"  额外从 AppData\\Local 和 AppData\\Roaming 扫描到 {appdata_extra} 个子目录")

    # ── 2. 分离已迁移（软链接）和待扫描目录 ──
    # ── 2. 分离已迁移（软链接）和待扫描目录 ──
    to_scan = [e for e in all_entries if not e.is_symlink]
    if not to_scan:
        print(f"  所有子目录均已迁移（共 {symlink_count} 个软链接），无需处理。")
        return 0

    print(f"  共 {len(all_entries)} 个子目录，已跳过 {symlink_count} 个已迁移目录（软链接）")

    # ── 3. 计算每个目录大小 ──
    total_dirs = len(to_scan)
    print(f"  正在统计目录大小 ...   0/{total_dirs}", end="", flush=True)
    for i, entry in enumerate(to_scan, 1):
        entry.size_bytes = _calc_dir_size(entry.path, report_name=entry.name)
        sys.stdout.write(f"\r  正在统计目录大小 ...   {i}/{total_dirs}  {entry.name}  {format_size(entry.size_bytes)}  ")
        sys.stdout.flush()
    print()

    # ── 4. 按大小降序排列 ──
    to_scan.sort(key=lambda e: e.size_bytes, reverse=True)

    # ── 过滤小于 min_size 的目录 ──
    hidden_count = 0
    hidden_total = 0
    filtered: list[ScanEntry] = []
    for e in to_scan:
        if e.size_bytes < min_size:
            hidden_count += 1
            hidden_total += e.size_bytes
        else:
            filtered.append(e)
    to_scan = filtered

    if hidden_count:
        print(f"  已忽略 {hidden_count} 个小于 {format_size(min_size)} 的目录(合计 {format_size(hidden_total)})")

    if not to_scan:
        print("  所有目录均小于阈值，无需处理。")
        return 0

    # ── 5. 展示结果 ──
    print()
    print(f"  {'':>4} {'大小':>10}  目录")
    print(f"  {'':─>4} {'─'*10}  {'─'*50}")
    for idx, entry in enumerate(to_scan, 1):
        size_str = format_size(entry.size_bytes)
        print(f"  {idx:>3}  {size_str}  {entry.name}")

    total_size = sum(e.size_bytes for e in to_scan)
    print(f"  {'':─>4} {'─'*10}  {'─'*50}")
    print(f"       {format_size(total_size)}  合计")
    print()

    # ── 6. 用户选择 ──
    chosen = _select_entries(to_scan)
    if not chosen:
        print("[CANCEL] 未选择任何目录，退出。")
        return 0

    # ── 7. 逐个迁移 ──
    success = 0
    fail = 0
    chosen_size = sum(e.size_bytes for e in chosen)
    print(f"\n开始迁移 {len(chosen)} 个目录（合计 {format_size(chosen_size)}）...\n")
    for entry in chosen:
        print(f"{'='*60}")
        print(f"  处理: {entry.path}")
        try:
            move_and_link(entry.path, dst_dir=dest_dir, dry_run=dry_run, skip_confirm=True)
            success += 1
        except DryRunError:
            success += 1
        except (ValueError, PermissionError, OSError) as exc:
            print(f"  [X] 跳过: {exc}")
            fail += 1
        print()

    # ── 8. 汇总 ──
    if dry_run:
        print(f"\n[DONE] 模拟完成。成功: {success}, 失败: {fail}")
    else:
        print(f"\n[DONE] 迁移完成。成功: {success}, 失败: {fail}")
    return 0


def _select_entries(entries: list[ScanEntry]) -> list[ScanEntry]:
    """交互式选择目录编号，返回选中的条目列表。"""
    prompt = "输入编号（空格分隔，如 1 3 5），a=全部，q=取消: "
    try:
        raw = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return []

    if not raw or raw == "q":
        return []
    if raw == "a":
        return list(entries)

    indices: set[int] = set()
    for part in raw.replace(",", " ").split():
        if "-" in part:
            try:
                a, b = part.split("-", 1)
                start = int(a.strip())
                end = int(b.strip())
                indices.update(range(start, end + 1))
            except ValueError:
                continue
        else:
            try:
                indices.add(int(part))
            except ValueError:
                continue

    result: list[ScanEntry] = []
    for idx in sorted(indices):
        if 1 <= idx <= len(entries):
            result.append(entries[idx - 1])
    return result

