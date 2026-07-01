import pandas as pd
import json
import re

file = "HAA29510F_20260515145443.xls"

# ===== 读取 =====
df_input = pd.read_excel(file, sheet_name="Input", header=None)
df_bom = pd.read_excel(file, sheet_name="全BOM", header=0)


# ===== ✅ 1. 处理 Input（参数组合） =====
params = {}
key_parts = set()
bom_parts = set()
for i in range(len(df_input)):
    key = str(df_input.iloc[i, 0]).strip() if pd.notna(df_input.iloc[i, 0]) else None
    key_parts.add(key)

# ===== ✅ 2. 处理 BOM（件号） =====
def normalize_pn(x):
    if pd.isna(x):
        return None
    x = str(x)
    x = re.sub(r"\(.*?\)", "", x)  # ✅ 去括号
    return x.strip()

for pn in df_bom["件号"]:
    clean = normalize_pn(pn)
    if clean:
        bom_parts.add(clean)


# ===== ✅ 输出 JSON =====
output = {
    "input_params": list(key_parts),
    "bom_part_numbers": list(bom_parts)
}

with open("bom_input_map.json", "w") as f:
    json.dump(output, f, indent=2)

print("✅ 已生成 bom_input_map.json")