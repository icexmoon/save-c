"""
命令行入口：``savec`` 或 ``python -m savec``。
"""

from __future__ import annotations

import argparse
import sys

from savec import __version__
from savec.core import DryRunError, move_and_link


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="savec",
        description="将 C 盘目录迁移到 D 盘并创建软链接，安全释放 C 盘空间。",
        epilog=(
            "不传参时进入交互模式，由程序提示输入路径。\n"
            "注意：创建和删除软链接、删除目录需要管理员权限。"
        ),
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="C 盘待迁移的目录完整路径（如 C:\\Users\\xxx\\AppData\\Roaming\\SomeApp）。",
    )
    parser.add_argument(
        "--dest-dir",
        default="D:\\moved_from_c",
        help="D 盘目标根目录（默认: D:\\moved_from_c）。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模拟运行，打印动作日志但不做任何实际修改。",
    )
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        help="跳过二次确认提示。",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"save-c {__version__}",
        help="显示版本信息并退出。",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI 入口。

    Returns:
        0 表示正常退出；1 表示错误退出。
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # ── 没有传参 -> 进入交互模式 ──
    if args.path is None:
        print("===== save-c: C盘目录迁移 + 软链接（安全增强版）=====")
        print("说明：先完整复制，成功后再删原目录，异常自动清理残缺文件\n")

        raw = input("请输入要迁移的 C 盘完整目录路径: ").strip().strip('"')
        if not raw:
            print("[CANCEL] 未输入路径，退出。")
            return 0
        args.path = raw

    try:
        move_and_link(
            args.path,
            dst_dir=args.dest_dir,
            dry_run=args.dry_run,
            skip_confirm=args.force,
        )
        return 0
    except DryRunError:
        # dry-run 的预期退出
        return 0
    except PermissionError:
        return 1
    except (ValueError, OSError) as exc:
        print(f"错误: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
