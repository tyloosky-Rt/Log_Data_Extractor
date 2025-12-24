import re
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Iterable, Tuple

TS_RE = re.compile(r"\[(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\](?:\[(\d+\.\d{3})\])?")

@dataclass
class ParsedRow:
    ts: str
    component: str
    data_type: str
    field1: str
    value1: Any
    field2: str
    value2: Any
    raw: str
    source_file: str

def _contains(line: str, needle: str) -> bool:
    return needle.lower() in line.lower()

def _extract_after(line: str, token: str) -> Optional[str]:
    idx = line.lower().find(token.lower())
    if idx < 0:
        return None
    s = line[idx + len(token):].strip()
    # 截断到行尾或下一个空格/逗号/分号（尽量稳健）
    m = re.match(r"([-+]?\d*\.?\d+|[^,;\s]+)", s)
    return m.group(1) if m else None

def _coerce(val: Optional[str], typ: str):
    if val is None:
        return None
    if typ == "float":
        try:
            return float(val)
        except Exception:
            return None
    if typ == "int":
        try:
            return int(float(val))
        except Exception:
            return None
    return val.strip()

def _pass_filters(extracted: Dict[str, Any], filters: List[Dict[str, Any]]) -> bool:
    if not filters:
        return True
    for f in filters:
        field, op, target = f["field"], f["op"], f["value"]
        v = extracted.get(field, None)
        if v is None:
            return False
        try:
            if op == ">":
                ok = v > target
            elif op == ">=":
                ok = v >= target
            elif op == "<":
                ok = v < target
            elif op == "<=":
                ok = v <= target
            elif op == "==":
                ok = v == target
            elif op == "!=":
                ok = v != target
            else:
                return False
        except Exception:
            return False
        if not ok:
            return False
    return True

def parse_lines(
    lines: Iterable[str],
    *,
    rules_for_component: List[Dict[str, Any]],
    component: str,
    data_type: str,
    source_file: str,
) -> List[ParsedRow]:
    out: List[ParsedRow] = []
    for line in lines:
        ts_m = TS_RE.search(line)
        if not ts_m:
            continue  # 无时间戳行忽略（需求约束）
        ts = ts_m.group(1)
        for rule in rules_for_component:
            if not _contains(line, rule["match"]):
                continue
            extracted: Dict[str, Any] = {}
            for k, spec in rule.get("extracts", {}).items():
                raw = _extract_after(line, spec["after"])
                extracted[k] = _coerce(raw, spec.get("type", "str"))
            if not _pass_filters(extracted, rule.get("filters", [])):
                continue
            # 映射到固定两列（field1/value1/field2/value2），不足则为空
            keys = list(extracted.keys())
            field1 = keys[0] if len(keys) > 0 else ""
            value1 = extracted.get(field1) if field1 else None
            field2 = keys[1] if len(keys) > 1 else ""
            value2 = extracted.get(field2) if field2 else None

            out.append(
                ParsedRow(
                    ts=ts,
                    component=component,
                    data_type=data_type,
                    field1=field1,
                    value1=value1,
                    field2=field2,
                    value2=value2,
                    raw=line.rstrip("\n"),
                    source_file=source_file,
                )
            )
    return out

def parse_file(
    filepath: str,
    *,
    rules: Dict[str, List[Dict[str, Any]]],
    components: List[str],
    data_type: str,
    encoding: str = "utf-8",
) -> List[ParsedRow]:
    # 逐行读取，避免大文件内存暴涨
    try:
        f = open(filepath, "r", encoding=encoding, errors="replace")
    except Exception:
        # 兜底：有些日志可能不是utf-8，仍尽量可读
        f = open(filepath, "r", encoding="utf-8", errors="replace")
    with f:
        lines = f
        all_rows: List[ParsedRow] = []
        for comp in components:
            comp_rules = rules.get(comp, [])
            all_rows.extend(
                parse_lines(
                    lines=open(filepath, "r", encoding=encoding, errors="replace"),
                    rules_for_component=comp_rules,
                    component=comp,
                    data_type=data_type,
                    source_file=filepath,
                )
            )
        # 已按文件内顺序输出；如需跨规则严格排序，可基于 ts 再排序
        all_rows.sort(key=lambda r: r.ts)
        return all_rows
