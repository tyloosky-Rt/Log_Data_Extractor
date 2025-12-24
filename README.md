# Log Data Extractor

基于《日志数据提取工具需求文档（V2.1 可交付版）》实现的桌面工具（Tkinter + PyInstaller）。

## 功能
- 导入单个/多个 .log 文件或文件夹
- 选择数据类型：液面/压力
- 选择组件：S1/S2/ISE/R11/R12/R21/R22（可多选）
- 解析匹配行并导出 Excel（每个组件一个 xlsx）

## 运行（开发）
```bash
pip install -r requirements.txt
python -m log_extractor.gui_tk
```

## 打包（exe）
见 build/build_exe.md
