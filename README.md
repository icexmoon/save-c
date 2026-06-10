# save-c

将 C 盘目录迁移到 D 盘并创建目录软链接（symlink），安全释放 C 盘空间。

先完整拷贝到 D 盘，确认成功后删除 C 盘原目录，再创建软链接指回 D 盘。
拷贝出错时自动清理残缺文件，不会留下脏数据。

## 安装

```bash
pip install .
```

或开发模式安装（编辑后即时生效）：

```bash
pip install -e .
```

## 用法

### 交互模式

直接执行 `savec`，按提示输入路径：

```bash
savec
```

### 命令行模式

```
savec C:\Users\xxx\AppData\Roaming\SomeApp
```

### 模拟运行（不做任何实际修改）

```
savec C:\Users\xxx\SomeDir --dry-run
```

### 跳过确认

```
savec C:\Users\xxx\SomeDir --force
```

### 自定义 D 盘保存目录

```
savec C:\Users\xxx\SomeDir --dest-dir D:\my_moved
```

## 扫描模式（批量迁移）

扫描用户目录下的所有子目录，统计占用的磁盘空间，交互式选择要迁移的目录。

```bash
savec scan
```

### 扫描指定目录

```bash
savec scan -d C:\Users\xxx\AppData
```

### 扫描并模拟运行

```bash
savec scan --dry-run
```

### Python API

```python
from savec import move_and_link

move_and_link("C:\\Users\\xxx\\SomeDir", dry_run=True)

from savec import scan_and_select_interactive

scan_and_select_interactive("C:\\Users\\xxx", dry_run=True)
```

## 安全说明

- 只允许操作 C 盘目录。
- 禁止迁移 Windows 系统目录。
- 拷贝失败自动回滚删除残缺文件。
- 删除原目录前会二次确认（除非 `--force`）。
- 创建和删除软链接、删除目录需要**管理员身份**运行。

## 许可证

MIT
