import pandas as pd
import json
from pathlib import Path
from collections import defaultdict

# ================= 配置 =================
BASE_DIR = Path(__file__).resolve().parent
INPUT_EXCEL = BASE_DIR / "BOM.xlsx"
OUTPUT_JSON = BASE_DIR / "bom_tree_L4.json"

LEVEL_COL = "LEVEL1"
PARENT_COL = "Parent"
CHILD_COL = "Child"
TYPE_COL = "child drawing type"

MAX_LEVEL = 4

# ================= 读取 Excel（全量） =================
df_full = pd.read_excel(INPUT_EXCEL, engine="openpyxl")
df_full = df_full[[LEVEL_COL, PARENT_COL, CHILD_COL, TYPE_COL]].dropna()

df_full[LEVEL_COL] = df_full[LEVEL_COL].astype(int)
for c in (PARENT_COL, CHILD_COL, TYPE_COL):
    df_full[c] = df_full[c].astype(str).str.strip()

# ================= 计算 Root（全量 L1–L5） =================
parents_full = set(df_full[PARENT_COL])
children_full = set(df_full[CHILD_COL])
roots_full = parents_full - children_full  # ≈ 60

# ================= L4 子集 =================
df_l4 = df_full[df_full[LEVEL_COL] <= MAX_LEVEL]

parents_l4 = set(df_l4[PARENT_COL])
children_l4 = set(df_l4[CHILD_COL])
roots_l4 = parents_l4 - children_l4         # ≈ 58

# ================= L5-only Root（关键） =================
l5_only_roots = roots_full - roots_l4

print("📌 L5-only 根节点（全量是 Root，但 L4 中被裁掉）：")
for r in sorted(l5_only_roots):
    print("  -", r)
print(f"✅ 数量：{len(l5_only_roots)}\n")

# ================= Parent → Children（L4） =================
children_map = defaultdict(list)

for _, row in df_l4.iterrows():
    children_map[row[PARENT_COL]].append({
        "part_number": row[CHILD_COL],
        "type": row[TYPE_COL]
    })

# ================= 构建 L4 BOM Tree =================
def build_tree(part_number, current_level):
    node = {
        "part_number": part_number,
        "level": current_level,
        "children": []
    }

    # ✅ 核心标记：这个节点是 L5-only Root
    if part_number in l5_only_roots:
        node["l5_only_root"] = True

    if current_level >= MAX_LEVEL:
        return node

    for child in children_map.get(part_number, []):
        child_node = build_tree(
            child["part_number"],
            current_level + 1
        )
        child_node["type"] = child["type"]
        node["children"].append(child_node)

    return node

# ================= 构建 Forest（L4 Roots） =================
bom_tree_l4 = [build_tree(root, 1) for root in sorted(roots_l4)]

# ================= 输出 JSON =================
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(bom_tree_l4, f, ensure_ascii=False, indent=2)

print(f"✅ L4 BOM 树已生成：{OUTPUT_JSON}")
print(f"✅ L4 Root 数量：{len(roots_l4)}")
print(f"✅ 全量 Root 数量：{len(roots_full)}")