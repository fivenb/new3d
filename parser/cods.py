import pandas as pd
import re
from tkinter import Tk, filedialog, messagebox
from pathlib import Path
from collections import defaultdict
import tkinter as tk

ID_COL = 1                 # B 列
TARGET_COL = 2             # C 列
CONDITION_START_COL = 7    # H 列
CONDITION_END_COL = 30     # AE 列
FORMULA_START_COL = 31     # AF 列

def cell_str(v):
    if pd.isna(v):
        return ""
    return str(v).strip()

def extract_input_output_properties(df):
    input_props, output_props = [], []

    for i in range(len(df)):
        # Input Parameter & Value List
        if cell_str(df.iloc[i, 1]) == "Input Parameter & Value List":
            j = i + 2
            while j < len(df):
                name = cell_str(df.iloc[j, 2])
                if not name:
                    break
                input_props.append(name)
                j += 1

        # Internal Parameter & Value List
        if cell_str(df.iloc[i, 1]) == "Internal Parameter & Value List":
            j = i + 2
            while j < len(df):
                name = cell_str(df.iloc[j, 2])
                if not name:
                    break
                output_props.append(name)
                j += 1

    return input_props, output_props

def extract_formula_rules(df):
    start_idx = df.index[df[1] == "Internal Parameter & Value List"].max()
    return df.iloc[start_idx + 1:]

def extract_dependencies(df_rules, input_props, output_props):
    input_set = set(input_props)
    output_set = set(output_props)

    dep_map = defaultdict(lambda: {"inputs": set(), "outputs": set()})

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

        # ---------- Condition（只看第一行） ----------
        for c in range(CONDITION_START_COL, CONDITION_END_COL + 1):
            param = cell_str(row[c])
            if not param:
                continue

            if param in output_set and param != target:
                dep_map[target]["outputs"].add(param)
            elif param in input_set:
                dep_map[target]["inputs"].add(param)

        # ---------- Formula（整个 ID block） ----------
        j = i
        while j < total:
            _, r = rows[j]
            rid = cell_str(r[ID_COL]).replace(".0", "")
            if j != i and rid:
                break

            for c in range(FORMULA_START_COL, len(r)):
                txt = cell_str(r[c])
                if not txt:
                    continue

                for op in output_set:
                    if op != target and re.search(rf"\b{re.escape(op)}\b", txt):
                        dep_map[target]["outputs"].add(op)

                for ip in input_set:
                    if re.search(rf"\b{re.escape(ip)}\b", txt):
                        dep_map[target]["inputs"].add(ip)
            j += 1
        i = j
    return dep_map

def run_with_gui():
    root = tk.Tk()
    root.title("CODS Formula Dependency Parser")
    root.geometry("600x220")
    root.resizable(False, False)

    input_paths = []
    entry_var = tk.StringVar()

    def choose_input():
        nonlocal input_paths
        paths = filedialog.askopenfilenames(
            title="Select CODS Excel file(s)",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if paths:
            input_paths = list(paths)
            entry_var.set("; ".join(input_paths))

    def run_process():
        if not input_paths:
            messagebox.showwarning(
                "Missing input",
                "Please select at least one CODS file."
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
                dep_map = extract_dependencies(df_rules, input_props, output_props)

                rows = []
                for target, deps in dep_map.items():
                    used_inputs = deps.get("inputs", set())
                    used_outputs = deps.get("outputs", set())

                    if not used_inputs and not used_outputs:
                        continue

                    rows.append({
                        "TargetProperty": target,
                        "TargetTypex": "Output",
                        "UsedInputs": ", ".join(sorted(used_inputs)),
                        "UsedOutputs": ", ".join(sorted(used_outputs)),
                    })

                dep_df = pd.DataFrame(rows)

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

        msg = f"Processed {len(success)} CODS file(s) successfully."
        if failed:
            msg += "\n\nFailed files:\n" + "\n".join(failed)

        messagebox.showinfo("Done", msg)

    tk.Label(root, text="Input CODS file(s):").place(x=20, y=20)
    tk.Entry(root, textvariable=entry_var, width=70).place(x=20, y=45)
    tk.Button(root, text="Browse...", command=choose_input).place(x=500, y=41)

    tk.Button(root, text="Run", width=15, height=2, command=run_process)\
        .place(x=240, y=130)

    root.mainloop()

if __name__ == "__main__":
    run_with_gui()
