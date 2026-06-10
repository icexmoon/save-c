import os
import shutil
import traceback

def safe_copy_dir(src: str, dst: str) -> bool:
    """
    安全完整拷贝目录，出错则回滚删除目标
    """
    # 目标已存在直接失败
    if os.path.exists(dst):
        print(f"❌ 目标目录已存在: {dst}")
        return False

    try:
        # 递归拷贝整个目录
        shutil.copytree(src, dst, dirs_exist_ok=False)
        print(f"✅ 目录拷贝完成: {dst}")
        return True
    except Exception as e:
        print(f"❌ 拷贝过程出错: {str(e)}")
        # 出错则清理已拷贝的残缺目录
        if os.path.exists(dst):
            try:
                shutil.rmtree(dst)
                print(f"🧹 已清理残缺拷贝目录: {dst}")
            except:
                print(f"⚠️  清理残缺目录失败，请手动删除: {dst}")
        return False

def move_and_link(src: str, dst_dir: str = "D:\\moved_from_c"):
    """
    流程：校验 -> 拷贝 -> 删原目录 -> 创建软链接
    异常自动回滚，提升安全性
    """
    src = src.rstrip("\\/")
    # 源路径检查
    if not os.path.exists(src):
        print(f"❌ 源目录不存在：{src}")
        return

    if not os.path.isdir(src):
        print(f"❌ 不是有效目录：{src}")
        return

    # 仅允许 C 盘
    if not src.startswith("C:\\"):
        print("❌ 仅支持转移 C 盘目录！")
        return

    # 禁止移动系统核心目录
    forbidden_prefix = [
        "C:\\Windows",
        "C:\\Program Files",
        "C:\\Program Files (x86)",
        "C:\\System",
        "C:\\Boot",
        "C:\\PerfLogs"
    ]
    src_lower = src.lower()
    for fp in forbidden_prefix:
        if src_lower.startswith(fp.lower()):
            print(f"❌ 禁止转移系统关键目录: {src}")
            return

    # 构造 D 盘目标路径
    rel_path = os.path.relpath(src, "C:\\")
    dst_full = os.path.join(dst_dir, rel_path)

    print("=" * 60)
    print(f"源目录: {src}")
    print(f"目标目录: {dst_full}")
    print("=" * 60)

    # 二次确认
    confirm = input("确认执行拷贝+迁移？(y/n)：").strip().lower()
    if confirm != "y":
        print("🚫 操作已取消")
        return

    try:
        # 1. 创建 D 盘总目录
        os.makedirs(dst_dir, exist_ok=True)

        # 2. 完整拷贝，失败自动回滚
        print("\n📦 开始完整拷贝文件...")
        copy_ok = safe_copy_dir(src, dst_full)
        if not copy_ok:
            print("❌ 拷贝失败，终止流程")
            return

        # 3. 拷贝成功后，删除原 C 盘目录
        print("\n🗑️  删除原 C 盘目录...")
        shutil.rmtree(src)
        print(f"✅ 原目录已删除: {src}")

        # 4. 创建目录软链接
        print("\n🔗 创建软链接...")
        os.symlink(dst_full, src, target_is_directory=True)
        print(f"✅ 软链接创建成功: {src}  ->  {dst_full}")

        print("\n🎉 全部操作完成，C 盘空间已释放！")

    except PermissionError:
        print("\n❌ 权限不足！请【以管理员身份】运行此脚本。")
    except Exception as e:
        print(f"\n❌ 执行异常: {str(e)}")
        traceback.print_exc()
        # 全局异常兜底：如果已经拷贝完成但后续出错，保留 D 盘文件，提示手动处理
        if os.path.exists(dst_full) and not os.path.exists(src):
            print(f"⚠️  异常中断，请手动检查：\n   源目录: {src}\n   备份目录: {dst_full}")

if __name__ == "__main__":
    print("===== C盘目录 先拷贝再迁移 + 软链接（安全增强版） =====")
    print("说明：先完整复制，成功后再删原目录，异常自动清理残缺文件\n")

    raw_path = input("请输入要迁移的 C 盘完整目录路径：").strip().strip('"')
    move_and_link(raw_path)