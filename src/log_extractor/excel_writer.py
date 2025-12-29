from typing import List
import pandas as pd
from log_extractor.parser import ParsedRow

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
from typing import Dict, Any, List
import pandas as pd


def _to_df(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def write_pressure_report(result: Dict[str, List[Dict[str, Any]]], out_path: str) -> None:
    """
    Export pressure pipeline results to Excel with 3 sheets:
      - 筛选前
      - 筛选后
      - 合并后
    """
    pre = result.get("pre_filter", [])
    post = result.get("post_filter", [])
    merged = result.get("merged", [])

    df_pre = _to_df(pre)
    df_post = _to_df(post)
    df_merged = _to_df(merged)

    # 统一列顺序：把常用列放前面（其余列跟在后面）
    def reorder(df: pd.DataFrame, first_cols: List[str]) -> pd.DataFrame:
        if df.empty:
            return df
        cols = list(df.columns)
        ordered = [c for c in first_cols if c in cols] + [c for c in cols if c not in first_cols]
        return df[ordered]

    df_pre = reorder(df_pre, ["timestamp", "type", "component_id", "reagent_pos", "component_type", "index", "raw_line"])
    df_post = reorder(df_post, ["timestamp", "type", "component_id", "reagent_pos", "component_type", "index", "raw_line"])
    df_merged = reorder(df_merged, ["component_id", "t_p0p", "t_vol", "t_cnt", "dt_vol", "dt_cnt", "reagent_pos"])

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df_pre.to_excel(writer, index=False, sheet_name="筛选前")
        df_post.to_excel(writer, index=False, sheet_name="筛选后")
        df_merged.to_excel(writer, index=False, sheet_name="合并后")
