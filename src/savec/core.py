"""
核心逻辑：目录安全拷贝、删除、软链接创建。
"""

from __future__ import annotations

import os
import shutil
import traceback


class DryRunError(RuntimeError):
    """Dry-run 模式下触发的中止信号，不会真正写入磁盘。"""


# 禁止移动的系统核心目录前缀
FORBIDDEN_PREFIXES = [
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\System",
    "C:\\Boot",
    "C:\\PerfLogs",
]


def safe_copy_dir(src: str, dst: str, *, dry_run: bool = False) -> bool:
    """安全完整拷贝目录，出错则回滚删除目标。

    Args:
        src: 源目录路径。
        dst: 目标目录路径。
        dry_run: 仅打印模拟信息，不实际拷贝。

    Returns:
        True 拷贝成功；False 目标已存在或拷贝失败。

    Raises:
        DryRunError: dry_run 模式下触发，调用方据此跳过后续实际写入。
    """
    if os.path.exists(dst):
        print(f"  [X] 目标目录已存在: {dst}")
        return False

    if dry_run:
        print(f"  [DRY] 模拟拷贝: {src}  ->  {dst}")
        return True

    try:
        shutil.copytree(src, dst, dirs_exist_ok=False)
        print(f"  [OK] 目录拷贝完成: {dst}")
        return True
    except Exception as e:
        print(f"  [X] 拷贝过程出错: {e}")
        if os.path.exists(dst):
            try:
                shutil.rmtree(dst)
                print(f"  [CLEAN] 已清理残缺拷贝目录: {dst}")
            except Exception:
                print(f"  [WARN] 清理残缺目录失败，请手动删除: {dst}")
        return False


def move_and_link(
    src: str,
    *,
    dst_dir: str = "D:\\moved_from_c",
    dry_run: bool = False,
    skip_confirm: bool = False,
) -> None:
    """流程：校验 -> 拷贝 -> 删原目录 -> 创建软链接。

    异常自动回滚，提升安全性。

    Args:
        src: C 盘源目录完整路径。
        dst_dir: D 盘目标根目录，默认 ``D:\\moved_from_c``。
        dry_run: 仅打印模拟动作，不实际写入磁盘。
        skip_confirm: 跳过二次确认提示。

    Raises:
        ValueError: 路径校验失败（非 C 盘、系统目录等）。
        DryRunError: dry_run 模式完成全部模拟后抛出，表示流程正常中止。
        PermissionError: 权限不足（需要管理员身份）。
    """
    src = src.rstrip("\\/")

    # ── 源路径检查 ──
    if not os.path.exists(src):
        raise ValueError(f"源目录不存在: {src}")
    if not os.path.isdir(src):
        raise ValueError(f"不是有效目录: {src}")
    if not src.startswith("C:\\"):
        raise ValueError("仅支持转移 C 盘目录！")

    src_lower = src.lower()
    for fp in FORBIDDEN_PREFIXES:
        if src_lower.startswith(fp.lower()):
            raise ValueError(f"禁止转移系统关键目录: {src}")

    # ── 构造目标路径 ──
    rel_path = os.path.relpath(src, "C:\\")
    dst_full = os.path.join(dst_dir, rel_path)

    print("=" * 60)
    print(f"  源目录: {src}")
    print(f"  目标目录: {dst_full}")
    print("=" * 60)

    # ── 二次确认 ──
    if not skip_confirm:
        try:
            answer = input("确认执行拷贝+迁移？(y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            print("[CANCEL] 操作已取消")
            return
        if answer != "y":
            print("[CANCEL] 操作已取消")
            return

    # ── 执行流程 ──
    try:
        # 1. 创建 D 盘总目录
        if not dry_run:
            os.makedirs(dst_dir, exist_ok=True)
        else:
            print(f"  [DRY] 创建目录: {dst_dir}")

        # 2. 完整拷贝，失败自动回滚
        print("\n[PACK] 开始完整拷贝文件...")
        copy_ok = safe_copy_dir(src, dst_full, dry_run=dry_run)
        if not copy_ok:
            print("[X] 拷贝失败，终止流程")
            return

        # 3. 拷贝成功后，删除原 C 盘目录
        if dry_run:
            print(f"  [DRY] 删除原目录: {src}")
        else:
            print("\n[DEL] 删除原 C 盘目录...")
            shutil.rmtree(src)
            print(f"  [OK] 原目录已删除: {src}")

        # 4. 创建目录软链接
        if dry_run:
            print(f"  [DRY] 创建软链接: {src}  ->  {dst_full}")
            raise DryRunError("Dry-run 完成，未做任何实际修改")
        else:
            print("\n[LINK] 创建软链接...")
            os.symlink(dst_full, src, target_is_directory=True)
            print(f"  [OK] 软链接创建成功: {src}  ->  {dst_full}")

        print("\n[DONE] 全部操作完成，C 盘空间已释放！")

    except PermissionError:
        print("\n[X] 权限不足！请以管理员身份运行。")
        raise
    except DryRunError:
        raise
    except Exception as e:
        print(f"\n[X] 执行异常: {e}")
        traceback.print_exc()
        if os.path.exists(dst_full) and not os.path.exists(src):
            # 已经转移成功，原始目录被删除，但没有成功创建软链接
            print(f"[WARN] 异常中断，创建软链接失败:\n   源目录: {src}\n   备份目录: {dst_full}")
            print(f"请尝试在管理员权限下手动创建软链接：mklink /D \"{src}\" \"{dst_full}\"")
        raise
