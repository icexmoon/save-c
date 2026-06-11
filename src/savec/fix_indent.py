path = r"D:\workspace\save-c\src\savec\scan.py"
lines = open(path, "r", encoding="utf-8").readlines()

fixes = {
    231: "    hidden_count = 0\n",
    232: "    hidden_total = 0\n",
    233: "    filtered: list[ScanEntry] = []\n",
    234: "    for e in to_scan:\n",
    235: "        if e.size_bytes < min_size:\n",
    236: "            hidden_count += 1\n",
    237: "            hidden_total += e.size_bytes\n",
    238: "        else:\n",
    239: "            filtered.append(e)\n",
    240: "    to_scan = filtered\n",
    242: "    if hidden_count:\n",
    243: '        print(f"  \u5df2\u5ffd\u7565 {hidden_count} \u4e2a\u5c0f\u4e8e {format_size(min_size)} \u7684\u76ee\u5f55(\u5408\u8ba1 {format_size(hidden_total)})")\n',
    245: "    if not to_scan:\n",
    246: '        print("\u6240\u6709\u76ee\u5f55\u5747\u5c0f\u4e8e\u9608\u503c\uff0c\u65e0\u9700\u5904\u7406。")\n',
    247: "        return 0\n",
    249: "    # \u2500\u2500 5. \u5c55\u793a\u7ed3\u679c \u2500\u2500\n",
    250: "        print()\n",
}

for idx, content in fixes.items():
    if idx <= len(lines):
        lines[idx-1] = content

open(path, "w", encoding="utf-8").writelines(lines)
print("fixed")
