"""
扫描 C 盘用户目录，统计可迁移的目录及空间占用。
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass

from savec.core import DryRunError, move_and_link

# 扫描时忽略的特殊目录（用户主目录下的系统级目录）
# skip_dirs is now configured via SavecConfig.skip_dirs or skip_dirs parameter

CACHE_DIR = os.path.join(os.environ.get("TEMP", os.environ.get("TMPDIR", "/tmp")), "savec-scan-cache")
CACHE_TTL = 600


def _cache_path(cache_key: str) -> str:
    h = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()[:16]
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{h}.json")


def _load_cache(cache_key: str, ttl: int = CACHE_TTL):
    cpath = _cache_path(cache_key)
    if not os.path.isfile(cpath):
        return None
    try:
        with open(cpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if time.time() - data["created_at"] > ttl:
            return None
        entries = [ScanEntry(**e) for e in data["entries"]]
        return entries, data["symlink_count"]
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def _save_cache(cache_key: str, entries, symlink_count):
    cpath = _cache_path(cache_key)
    data = {
        "cache_key": cache_key,
        "created_at": time.time(),
        "symlink_count": symlink_count,
        "entries": [
            {"name": e.name, "path": e.path, "size_bytes": e.size_bytes, "is_symlink": e.is_symlink}
            for e in entries
        ],
    }
    try:
        with open(cpath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except OSError:
        pass


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
    """递归计算目录大小。"""
    total = 0
    try:
        stack = [dirpath]
        while stack:
            current = stack.pop(0)
            try:
                with os.scandir(current) as it:
                    for entry in it:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                        elif entry.is_file(follow_symlinks=False):
                            total += entry.stat().st_size
            except (OSError, PermissionError):
                pass
    except (OSError, PermissionError):
        pass
    return total


def scan_and_select_interactive(
    base_dir: str | list[str],
    *,
    dest_dir: str = "D:\\moved_from_c",
    dry_run: bool = False,
    min_size: int = 500 * 1024 * 1024,
    no_cache: bool = False,
    skip_dirs: list[str] | None = None,
    cache_ttl: int | None = None,
) -> int:
    """扫描、展示、交互式选择并迁移目录。

    Returns:
        0 正常结束；1 出错。
    """
    # base_dir validation is per-directory in the loop

    # -- 0. 尝试读取缓存 --
    if isinstance(base_dir, str):
        base_dirs = [base_dir]
    else:
        base_dirs = list(base_dir)
    cache_key = "|".join(sorted(base_dirs))
    ttl = cache_ttl if cache_ttl is not None else CACHE_TTL

    skip_set = frozenset(os.path.basename(s).lower() for s in skip_dirs) if skip_dirs is not None else frozenset({"appdata", "onedrive"})

    loaded_from_cache = False
    if not no_cache:
        cached = _load_cache(cache_key, ttl=ttl)
        if cached is not None:
            all_entries, symlink_count = cached
            loaded_from_cache = True
            print("  使用缓存结果（10分钟内有效）")

    if not loaded_from_cache:
        all_entries = []
        symlink_count = 0

        for _dir in base_dirs:
            _dir = _dir.rstrip("\\/")
            if not os.path.isdir(_dir):
                print(f"  [WARN] 扫描目录不存在，跳过: {_dir}")
                continue

            print(f"正在扫描 {_dir} ...")
            entries, sl = _list_dirs(_dir)
            if not entries:
                continue

            skip_count = 0
            filtered = []
            for e in entries:
                if e.path in skip_dirs:
                    skip_count += 1
                    continue
                filtered.append(e)
            entries = filtered

            appdata_extra = 0

            if skip_count:
                print(f"  已过滤 {skip_count} 个特殊目录")
            # if appdata_extra:
            #     print(f"  额外从 AppData\\Local 和 AppData\\Roaming 扫描到 {appdata_extra} 个子目录")

            all_entries.extend(entries)
            symlink_count += sl

        if not all_entries:
            print("  未发现任何子目录。")
            return 0

        to_scan = [e for e in all_entries if not e.is_symlink]
        if not to_scan:
            print(f"  所有子目录均已迁移（共 {symlink_count} 个软链接），无需处理。")
            return 0
        
        for i, entry in enumerate(to_scan, 1):
            entry.size_bytes = _calc_dir_size(entry.path)
            sys.stdout.write(f"\r  正在统计目录大小 ...   {i}/{len(to_scan)}  {entry.name}  {format_size(entry.size_bytes)}  ")
            sys.stdout.flush()
        print()
        print(f"  共 {len(all_entries)} 个子目录，已跳过 {symlink_count} 个已迁移目录（软链接）")

        total_dirs = len(to_scan)
    else:
        to_scan = [e for e in all_entries if not e.is_symlink]
        if not to_scan:
            print("  所有子目录均已迁移，无需处理。")
            return 0
        print(f"  共 {len(all_entries)} 个子目录，已跳过 {symlink_count} 个已迁移目录（软链接）")

        print(f"  正在统计目录大小 ...   0/{total_dirs}", end="", flush=True)    # -- 4. 按大小降序排列 --
    # ── 4. 按大小降序排列 ──
    to_scan.sort(key=lambda e: e.size_bytes, reverse=True)

    # ── 过滤小于 min_size 的目录 ──
    total_before = len(to_scan)
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
        print(f"  共扫描到 {total_before} 个目录，均小于 {format_size(min_size)}，全部忽略（使用 --min-size 0 查看所有目录）")
        return 0

    # ── 5. 展示结果 ──
    print()
    print(f"  {'':>4} {'大小':>10}  目录")
    print(f"  {'':─>4} {'─'*10}  {'─'*50}")
    for idx, entry in enumerate(to_scan, 1):
        size_str = format_size(entry.size_bytes)
        print(f"  {idx:>3}  {size_str}  {entry.path}")

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



