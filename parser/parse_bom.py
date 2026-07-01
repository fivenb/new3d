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
CATEGORY_COL = "Category"

MAX_LEVEL = 4

# ================= 读取 Excel（全量） =================
df_full = pd.read_excel(INPUT_EXCEL, engine="openpyxl")

df_full[LEVEL_COL] = df_full[LEVEL_COL].astype(int)
for c in (PARENT_COL, CHILD_COL, TYPE_COL, CATEGORY_COL):
    df_full[c] = df_full[c].astype(str).str.strip()

# ================= 计算 Root（全量 L1–L5） =================
parents_full = set(df_full[PARENT_COL])
children_full = set(df_full[CHILD_COL])
roots_full = sorted(
    df_full[df_full[LEVEL_COL] == 1][CHILD_COL]
    .dropna()
    .astype(str)
    .unique()
)

# ================= Parent → Children（L4） =================
children_map = defaultdict(list)

for _, row in df_full.iterrows():
    children_map[row[PARENT_COL]].append({
        "part_number": row[CHILD_COL],
        "type": row[TYPE_COL],
        "category": row[CATEGORY_COL]
    })

part_category_map = dict(
    zip(df_full[CHILD_COL], df_full[CATEGORY_COL])
)
# ================= 构建 L4 BOM Tree =================
def build_tree(part_number, current_level):
    node = {
        "part_number": part_number,
        "level": current_level,
        "category": part_category_map.get(part_number, "UNKNOWN"),
        "children": []
    }

    for child in children_map.get(part_number, []):
        child_node = build_tree(
            child["part_number"],
            current_level + 1
        )
        child_node["type"] = child["type"]
        child_node["category"] = child["category"]
        node["children"].append(child_node)

    return node

# ================= 构建 Forest（L4 Roots） =================
bom_tree_l4 = [build_tree(root, 1) for root in sorted(roots_full)]

# ================= 输出 JSON =================
with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
    json.dump(bom_tree_l4, f, ensure_ascii=False, indent=2)

print(f"✅ L4 BOM 树已生成：{OUTPUT_JSON}")
print(f"✅ Root 数量：{len(roots_full)}")
