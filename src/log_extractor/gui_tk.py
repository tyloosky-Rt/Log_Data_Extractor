import os
import tkinter as tk
from tkinter import filedialog, messagebox
from log_extractor.config_rules import RULES_BY_TYPE
from log_extractor.parser import parse_file
from log_extractor.excel_writer import rows_to_dataframe, write_excel

COMPONENTS = ["S1","S2","ISE","R11","R12","R21","R22"]

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("日志数据提取工具")
        self.geometry("720x420")
        self.files = []

        self.data_type = tk.StringVar(value="liquid")
        self.comp_vars = {c: tk.BooleanVar(value=False) for c in COMPONENTS}

        self._build()

    def _build(self):
        frm = tk.Frame(self)
        frm.pack(fill="both", expand=True, padx=12, pady=12)

        # file controls
        f1 = tk.LabelFrame(frm, text="1) 导入日志")
        f1.pack(fill="x", pady=6)

        tk.Button(f1, text="导入日志文件", command=self.pick_files).pack(side="left", padx=6, pady=6)
        tk.Button(f1, text="导入文件夹", command=self.pick_folder).pack(side="left", padx=6, pady=6)
        tk.Button(f1, text="清空", command=self.clear_files).pack(side="left", padx=6, pady=6)

        self.file_lbl = tk.Label(f1, text="未选择文件")
        self.file_lbl.pack(side="left", padx=10)

        # data type
        f2 = tk.LabelFrame(frm, text="2) 选择数据类型")
        f2.pack(fill="x", pady=6)
        tk.Radiobutton(f2, text="液面高度数据", variable=self.data_type, value="liquid").pack(side="left", padx=6, pady=6)
        tk.Radiobutton(f2, text="压力数据", variable=self.data_type, value="pressure").pack(side="left", padx=6, pady=6)

        # components
        f3 = tk.LabelFrame(frm, text="3) 选择组件（可多选）")
        f3.pack(fill="x", pady=6)
        for c in COMPONENTS:
            tk.Checkbutton(f3, text=c, variable=self.comp_vars[c]).pack(side="left", padx=6, pady=6)

        # run
        f4 = tk.Frame(frm)
        f4.pack(fill="x", pady=12)
        tk.Button(f4, text="开始解析并导出Excel", command=self.run).pack(side="left", padx=6)
        self.status = tk.Label(f4, text="就绪")
        self.status.pack(side="left", padx=12)

        # note
        note = tk.Label(frm, text="提示：压力数据检索规则表待更新（规则为空时将导出空表）。", fg="gray")
        note.pack(anchor="w", pady=6)

    def pick_files(self):
        fps = filedialog.askopenfilenames(title="选择log文件", filetypes=[("Log files","*.log"),("All files","*.*")])
        self.files.extend(list(fps))
        self._refresh_files()

    def pick_folder(self):
        d = filedialog.askdirectory(title="选择包含log的文件夹")
        if not d:
            return
        for fn in sorted(os.listdir(d)):
            if fn.lower().endswith(".log"):
                self.files.append(os.path.join(d, fn))
        self._refresh_files()

    def clear_files(self):
        self.files = []
        self._refresh_files()

    def _refresh_files(self):
        if not self.files:
            self.file_lbl.config(text="未选择文件")
        else:
            self.file_lbl.config(text=f"已选择 {len(self.files)} 个文件")

    def run(self):
        if not self.files:
            messagebox.showerror("错误", "请先导入日志文件或文件夹。")
            return
        comps = [c for c in COMPONENTS if self.comp_vars[c].get()]
        if not comps:
            messagebox.showerror("错误", "请至少勾选一个组件。")
            return

        dt = self.data_type.get()
        rules = RULES_BY_TYPE[dt]

        self.status.config(text="处理中...")
        self.update_idletasks()

        try:
            for fp in self.files:
                rows = parse_file(fp, rules=rules, components=comps, data_type=dt)
                df = rows_to_dataframe(rows)
                base = os.path.splitext(os.path.basename(fp))[0]
                for comp in comps:
                    out_name = f"{base}_{dt}_{comp}.xlsx"
                    out_path = os.path.join(os.path.dirname(fp), out_name)
                    write_excel(df[df["组件"]==comp], out_path)
            self.status.config(text="完成")
            messagebox.showinfo("完成", "解析完成，已导出 Excel。")
        except Exception as e:
            self.status.config(text="失败")
            messagebox.showerror("失败", str(e))

def main():
    App().mainloop()

if __name__ == "__main__":
    main()
