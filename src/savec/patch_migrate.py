path = r"D:\workspace\save-c\src\savec\config.py"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

old = """        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SavecConfig(**data)"""

new = """        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Migration: upgrade old single-dir default to three scan dirs
        if data.get("scan_dirs") == [os.path.expanduser("~")]:
            data["scan_dirs"] = [
                os.path.expanduser("~"),
                os.path.join(os.path.expanduser("~"), "AppData", "Local"),
                os.path.join(os.path.expanduser("~"), "AppData", "Roaming"),
            ]

        # Migration: upgrade old skip_dirs (names only) to full paths
        if "skip_dirs" in data:
            data["skip_dirs"] = [
                os.path.join(os.path.expanduser("~"), s) if not os.path.isabs(s) else s
                for s in data["skip_dirs"]
            ]

        return SavecConfig(**data)"""

c = c.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("load_config migration added")
