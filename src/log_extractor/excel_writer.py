from typing import List
import pandas as pd
from .parser import ParsedRow

def rows_to_dataframe(rows: List[ParsedRow]) -> pd.DataFrame:
    return pd.DataFrame([{
        "时间戳": r.ts,
        "组件": r.component,
        "数据类型": r.data_type,
        "提取字段1": r.field1,
        "字段1值": r.value1,
        "提取字段2": r.field2,
        "字段2值": r.value2,
        "原始行内容": r.raw,
        "来源文件": r.source_file,
    } for r in rows])

def write_excel(df: pd.DataFrame, out_path: str) -> None:
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
