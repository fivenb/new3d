from unicodedata import name
import tkinter as tk
import pandas as pd
import re
from tkinter import Tk, filedialog,messagebox
from pathlib import Path
from collections import defaultdict

# ================= SCS Formula & Linkup 列定义（已定死） =================
ID_COL = 0                 # A 列
TARGET_COL = 1             # B 列

CONDITION_START_COL = 4    # E 列
CONDITION_END_COL = 17     # R 列

FORMULA_START_COL = 18     # S 列
FORMULA_END_COL = 28       # AC 列

PARAM_COL = 35             # AJ 列（仅用于 Input / Output 定义区）


def cell_str(v):
    if pd.isna(v):
        return ""
    return str(v).strip()


def select_excel_file():
    root = Tk()
    root.withdraw()
    return filedialog.askopenfilename(
        title="Select SCS Excel",
        filetypes=[("Excel files", "*.xlsx *.xls")]
    )


# ================= 1. Input / Output（AJ 列） =================
def extract_input_output_properties(df):
    input_props, output_props = [], []

    for i in range(len(df)):
        row_text = " ".join(cell_str(v) for v in df.iloc[i])

        # ---- Input ----
        if "Input Parameter" in row_text and "Value List" in row_text:
            j = i + 1
            while j < len(df):
                name = cell_str(df.iloc[j, PARAM_COL])
                if not name:
                    break
                
                if name == "Property Name":
                    j += 1
                    continue
                input_props.append(name)
                j += 1

        # ---- Output ----
        if "Internal Parameter" in row_text and "Value List" in row_text:
            j = i + 1
            while j < len(df):
                name = cell_str(df.iloc[j, PARAM_COL])
                if not name:
                    break
                
                if name == "Property Name":
                    j += 1
                    continue    
                output_props.append(name)
                j += 1

    return input_props, output_props


# ================= 2. Formula & Linkup 区域 =================
def extract_formula_rules(df):
    start_idx = None
    for i in range(len(df)):
        if cell_str(df.iloc[i, 0]) == "Formula & Linkup":
            start_idx = i
            break

    if start_idx is None:
        raise Exception("Cannot find Formula & Linkup section")

    return df.iloc[start_idx + 1:]


# ================= 3. 解析依赖（与 CODS 同逻辑） =================
def extract_dependencies(df_rules, input_props, output_props):
    input_set = set(input_props)
    output_set = set(output_props)

    dep_map = defaultdict(lambda: {"inputs": set(), "outputs": set()})
    used_targets = set()

    rows = list(df_rules.iterrows())
    total = len(rows)
    i = 0

    while i < total:
        _, row = rows[i]
        rule_id = cell_str(row[ID_COL]).replace(".0", "")
        if not rule_id:
            i += 1
            continue

        target = cell_str(row[TARGET_COL])

        # ✅ 只接受真正的 Output 参数作为 Target
        if target not in output_set:
            i += 1
            continue

        if not re.fullmatch(r"[A-Za-z0-9_]+", target):
            i += 1
            continue

        used_targets.add(target)

        # ===== Condition：只看第一行（E~R）=====
        for c in range(CONDITION_START_COL, CONDITION_END_COL + 1):
            param = cell_str(row[c])
            if not param:
                continue

            if not re.fullmatch(r"[A-Za-z0-9_]+", param):
                continue

            if param in output_set and param != target:
                dep_map[target]["outputs"].add(param)
            elif param in input_set:
                dep_map[target]["inputs"].add(param)

        # ===== Formula：扫整个 ID block（S~AC）=====
        j = i + 1
        while j < total:
            _, r = rows[j]
            rid = cell_str(r[ID_COL]).replace(".0", "")
            if rid:
                break

            for c in range(FORMULA_START_COL, FORMULA_END_COL + 1):
                txt = cell_str(r[c])
                if not txt:
                    continue

                for op in output_set:
                    if op != target and re.search(rf"\b{re.escape(op)}\b", txt):
                        dep_map[target]["outputs"].add(op)

                for ip in input_set:
                    if ip != target and re.search(rf"\b{re.escape(ip)}\b", txt):
                        dep_map[target]["inputs"].add(ip)

            j += 1

        i = j

    return dep_map, used_targets

# ================= 4. 构建输出 =================
def build_dependency_df(dep_map, used_targets):
    rows = []

    for t in sorted(used_targets):
        deps = dep_map.get(t, {"inputs": set(), "outputs": set()})
        
        # ✅ 过滤：input / output 都为空的
        if not deps["inputs"] and not deps["outputs"]:
            continue

        rows.append({
            "TargetProperty": t,
            "UsedInputs": ", ".join(sorted(deps["inputs"])),
            "UsedOutputs": ", ".join(sorted(deps["outputs"]))
        })

    return pd.DataFrame(rows)

import tkinter as tk
from tkinter import filedialog, messagebox

def run_with_gui():
    root = tk.Tk()
    root.title("SCS Formula Dependency Parser")
    root.geometry("600x220")
    root.resizable(False, False)

    input_paths = []
    entry_var = tk.StringVar()

    def choose_input():
        nonlocal input_paths
        paths = filedialog.askopenfilenames(
            title="Select SCS Excel file(s)",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if paths:
            input_paths = list(paths)
            entry_var.set("; ".join(input_paths))

    def run_process():
        if not input_paths:
            messagebox.showwarning(
                "Missing input",
                "Please select at least one SCS file."
            )
            return

        success, failed = [], []

        for src in input_paths:
            try:
                out_file = Path(src).with_name(
                    Path(src).stem + "_Formula_Dependency.xlsx"
                )

                df = pd.read_excel(src, sheet_name=0, header=None)
                input_props, output_props = extract_input_output_properties(df)
                df_rules = extract_formula_rules(df)
                dep_map, used_targets = extract_dependencies(
                    df_rules, input_props, output_props
                )
                dep_df = build_dependency_df(dep_map, used_targets)

                with pd.ExcelWriter(out_file, engine="openpyxl") as writer:
                    dep_df.to_excel(writer, sheet_name="Formula_Dependency", index=False)
                    pd.DataFrame({"InputProperty": input_props}).to_excel(
                        writer, sheet_name="Input_Properties", index=False
                    )
                    pd.DataFrame({"OutputProperty": output_props}).to_excel(
                        writer, sheet_name="Output_Properties", index=False
                    )

                success.append(Path(src).name)

            except Exception as e:
                failed.append(f"{Path(src).name}: {e}")

        msg = f"Processed {len(success)} SCS file(s) successfully."
        if failed:
            msg += "\n\nFailed files:\n" + "\n".join(failed)

        messagebox.showinfo("Done", msg)

    tk.Label(root, text="Input SCS file(s):").place(x=20, y=20)
    tk.Entry(root, textvariable=entry_var, width=70).place(x=20, y=45)
    tk.Button(root, text="Browse...", command=choose_input).place(x=500, y=41)

    tk.Button(root, text="Run", width=15, height=2, command=run_process)\
        .place(x=240, y=130)

    root.mainloop()

if __name__ == "__main__":
    run_with_gui()