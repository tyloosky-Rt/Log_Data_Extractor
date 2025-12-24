import argparse
import os
from .config_rules import RULES_BY_TYPE
from .parser import parse_file
from .excel_writer import rows_to_dataframe, write_excel

def main():
    ap = argparse.ArgumentParser(description="Log Data Extractor")
    ap.add_argument("--data-type", choices=["liquid","pressure"], required=True)
    ap.add_argument("--components", nargs="+", required=True, help="e.g. S1 S2 ISE R11")
    ap.add_argument("--inputs", nargs="+", required=True, help="log files")
    args = ap.parse_args()

    rules = RULES_BY_TYPE[args.data_type]
    for fp in args.inputs:
        rows = parse_file(fp, rules=rules, components=args.components, data_type=args.data_type)
        df = rows_to_dataframe(rows)
        base = os.path.splitext(os.path.basename(fp))[0]
        for comp in args.components:
            out = f"{base}_{args.data_type}_{comp}.xlsx"
            out_path = os.path.join(os.path.dirname(fp), out)
            write_excel(df[df["组件"]==comp], out_path)
            print("Wrote:", out_path)

if __name__ == "__main__":
    main()
