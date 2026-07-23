import pandas as pd
import json
from collections import defaultdict

LEVEL_COL = "Level"
PARENT_COL = "Parent"
CHILD_COL = "Child"
TYPE_COL = "child drawing type"

def parse_excel(input_excel, output_json):
    df_full = pd.read_excel(input_excel, engine="openpyxl")
    df_full[LEVEL_COL] = df_full[LEVEL_COL].fillna(0).astype(int)
    for c in (PARENT_COL, CHILD_COL, TYPE_COL):
        df_full[c] = (
            df_full[c]
            .fillna("")
            .astype(str)
            .str.strip()
    )
    roots_full = sorted(
        df_full[df_full[LEVEL_COL] == 1][CHILD_COL]
        .dropna()
        .astype(str)
        .unique()
    )
    children_map = defaultdict(list)
    for _, row in df_full.iterrows():
        children_map[row[PARENT_COL]].append({
            "part_number": row[CHILD_COL],
            "type": row[TYPE_COL],
        })
    def build_tree(part_number, current_level=1):
        node = {
            "part_number": part_number,
            "level": current_level,
            "children": []
        }
        children = children_map.get(part_number, [])
        for child in children:
            child_node = build_tree(
                child["part_number"],
                current_level + 1
            )
            child_node["type"] = child.get("type")
            node["children"].append(child_node)
        return node
    bom_tree_l4 = [
        build_tree(root, 1)
        for root in roots_full
    ]
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(
            bom_tree_l4,
            f,
            ensure_ascii=False,
            indent=2
        )
    return {
        "root_count": len(roots_full),
        "output_json": output_json
    }
if __name__ == "__main__":
    parse_excel(
        "BOM.xlsx",
        "bom_tree_L4.json"
    )
