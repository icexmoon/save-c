"""
命令行入口：``savec`` | ``savec scan`` | ``python -m savec``。
"""

from __future__ import annotations

import argparse
import os
import sys

from savec import __version__
from savec.core import DryRunError, move_and_link
from savec.scan import scan_and_select_interactive


def _build_move_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="savec",
        description="将 C 盘目录迁移到 D 盘并创建软链接，安全释放 C 盘空间。",
        epilog=(
            "不传参时进入交互模式，由程序提示输入路径。\n"
            "注意：创建和删除软链接、删除目录需要管理员权限。\n"
            "子命令: savec scan  — 扫描用户目录并交互式迁移"
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


def _build_scan_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="savec scan",
        description="扫描目录，统计可迁移的空间并交互式选择迁移。",
    )
    parser.add_argument(
        "-d", "--dir",
        default=os.path.expanduser("~"),
        help="要扫描的目录（默认: 当前用户主目录）。",
    )
    parser.add_argument(
        "--dest-dir",
        default="D:\\moved_from_c",
        help="D 盘目标根目录（默认: D:\\moved_from_c）。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模拟运行，不做实际修改。",
    )
    return parser


def _run_move(argv: list[str]) -> int:
    """迁移模式：处理单个目录迁移。"""
    parser = _build_move_parser()
    args = parser.parse_args(argv)

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
        return 0
    except PermissionError:
        return 1
    except (ValueError, OSError) as exc:
        print(f"错误: {exc}")
        return 1


def _run_scan(argv: list[str]) -> int:
    """扫描模式：交互式扫描、选择并迁移。"""
    parser = _build_scan_parser()
    args = parser.parse_args(argv)
    return scan_and_select_interactive(
        args.dir,
        dest_dir=args.dest_dir,
        dry_run=args.dry_run,
    )


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if argv and argv[0] == "scan":
        return _run_scan(argv[1:])
    elif argv and argv[0] == "--help":
        _build_move_parser().print_help()
        return 0
    elif argv and argv[0] in ("-V", "--version"):
        _build_move_parser().parse_args(argv)
        return 0
    else:
        return _run_move(argv)


if __name__ == "__main__":
    sys.exit(main())
