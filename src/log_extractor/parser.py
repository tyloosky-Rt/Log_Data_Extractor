import re
from log_extractor.config_rules import PRESSURE_PATTERNS, PRESSURE_MERGE_WINDOW_SEC

# ---------- Regex patterns (pressure) ----------
RE_COMPONENT_ID = re.compile(r"componentId:(\d+)")

RE_P0 = re.compile(r"\bp0:(-?\d+)")
RE_PP0 = re.compile(r"\bpp0:(-?\d+)")
RE_PP = re.compile(r"\bpp:(-?\d+)")
RE_PE = re.compile(r"\bpe:(-?\d+)")

RE_REAGENT_POS = re.compile(r"reagentPos:\s*(\{[^}]+\})")
RE_COMPONENT_TYPE = re.compile(r"componentType:\s*([A-Za-z0-9_]+)")
RE_LEVEL_HEIGHT = re.compile(r"levelHeight:\s*(-?\d+)")
RE_NEW_REMAIN_VOL = re.compile(r"newRemainVol:\s*(-?\d+(?:\.\d+)?)")
RE_EXECUTE_RESULT = re.compile(r"executeResult:\s*(-?\d+)")
RE_REMAIN_VOL_DETECT_TYPE = re.compile(r"remainVolDetectType:\s*(-?\d+)")

RE_CHEMISTRY_NAME = re.compile(r"chemstryName:\s*([^,]+)")
RE_REMAIN_TEST_COUNT = re.compile(r"remainTestCount:\s*(-?\d+)")
RE_REMAIN_FACTORY_TEST_NUM = re.compile(r"remainFactoryTestNum:\s*(-?\d+)")
_EPOCH_IN_BRACKETS = re.compile(r"\[(?P<epoch>\d{9,12}(?:\.\d+)?)\]")

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Iterable, Tuple

from typing import Dict, Any, List
from datetime import datetime

_TS_PATTERNS = [
    # 2025-12-29 12:34:56.789
    r"(?P<ts>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?)",
    # 2025/12/29 12:34:56.789
    r"(?P<ts>\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?)",
]

def extract_timestamp(line: str) -> float:
    """
    Extract epoch timestamp like: [1765979990.517]
    If not found, return 0.0
    """
    m = _EPOCH_IN_BRACKETS.search(line)
    if m:
        try:
            return float(m.group("epoch"))
        except ValueError:
            pass
    return 0.0
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


def _try_int(m: Optional[re.Match], default=None):
    if not m:
        return default
    try:
        return int(m.group(1))
    except Exception:
        return default


def _try_float(m: Optional[re.Match], default=None):
    if not m:
        return default
    try:
        return float(m.group(1))
    except Exception:
        return default


def _extract_component_id(line: str) -> Optional[int]:
    """Best effort componentId extraction: componentId:58 -> 58"""
    return _try_int(RE_COMPONENT_ID.search(line), default=None)


def _is_valid_for_post_filter(r: Dict[str, Any]) -> bool:
    """
    Minimal safe 'post_filter' rules:
      - P0P_CLOT: must have component_id and p0/pp0/pp/pe
      - REMAIN_VOL: must include 'success' and executeResult == 0
      - REMAIN_CNT: must include 'success' and have remain_test_count
    You can tighten these later to match V2.2 table exactly.
    """
    t = r.get("type")
    if t == "P0P_CLOT":
        return (
            isinstance(r.get("component_id"), int)
            and all(isinstance(r.get(k), int) for k in ("p0", "pp0", "pp", "pe"))
        )
    if t == "REMAIN_VOL":
        return r.get("success") is True and r.get("execute_result") == 0
    if t == "REMAIN_CNT":
        return r.get("success") is True and isinstance(r.get("remain_test_count"), int)
    return False


def _merge_pressure(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge within [t0, t0 + window] for same component_id.
    Anchor: each P0P_CLOT row (t0)
    Find nearest REMAIN_VOL and REMAIN_CNT rows in window.

    Note: if REMAIN_* rows don't have component_id, they will not be merged
    (to avoid false positive merges).
    """
    # group by type
    p0ps = [r for r in rows if r.get("type") == "P0P_CLOT" and isinstance(r.get("component_id"), int)]
    vols = [r for r in rows if r.get("type") == "REMAIN_VOL" and isinstance(r.get("component_id"), int)]
    cnts = [r for r in rows if r.get("type") == "REMAIN_CNT" and isinstance(r.get("component_id"), int)]

    # index by component_id
    vols_by_cid: Dict[int, List[Dict[str, Any]]] = {}
    cnts_by_cid: Dict[int, List[Dict[str, Any]]] = {}

    for r in vols:
        vols_by_cid.setdefault(r["component_id"], []).append(r)
    for r in cnts:
        cnts_by_cid.setdefault(r["component_id"], []).append(r)

    # sort
    p0ps.sort(key=lambda x: x.get("timestamp", 0.0))
    for cid in vols_by_cid:
        vols_by_cid[cid].sort(key=lambda x: x.get("timestamp", 0.0))
    for cid in cnts_by_cid:
        cnts_by_cid[cid].sort(key=lambda x: x.get("timestamp", 0.0))

    def pick_nearest(cands: List[Dict[str, Any]], t0: float) -> Optional[Dict[str, Any]]:
        best = None
        best_dt = None
        for c in cands:
            t = float(c.get("timestamp", 0.0) or 0.0)
            dt = t - t0
            if dt < 0 or dt > PRESSURE_MERGE_WINDOW_SEC:
                continue
            if best is None or dt < best_dt:
                best = c
                best_dt = dt
        return best

    merged: List[Dict[str, Any]] = []
    for p in p0ps:
        cid = p["component_id"]
        t0 = float(p.get("timestamp", 0.0) or 0.0)

        v = pick_nearest(vols_by_cid.get(cid, []), t0)
        c = pick_nearest(cnts_by_cid.get(cid, []), t0)

        if not (v and c):
            continue

        merged.append({
            "component_id": cid,

            "t_p0p": t0,
            "t_vol": float(v.get("timestamp", 0.0) or 0.0),
            "t_cnt": float(c.get("timestamp", 0.0) or 0.0),
            "dt_vol": float(v.get("timestamp", 0.0) or 0.0) - t0,
            "dt_cnt": float(c.get("timestamp", 0.0) or 0.0) - t0,

            # p0p values
            "p0": p.get("p0"),
            "pp0": p.get("pp0"),
            "pp": p.get("pp"),
            "pe": p.get("pe"),

            # join helpful fields
            "reagent_pos": v.get("reagent_pos") or c.get("reagent_pos"),
            "component_type": v.get("component_type") or c.get("component_type"),

            # remain vol
            "level_height": v.get("level_height"),
            "new_remain_vol": v.get("new_remain_vol"),
            "remain_vol_detect_type": v.get("remain_vol_detect_type"),
            "execute_result": v.get("execute_result"),

            # remain cnt
            "chemistry_name": c.get("chemistry_name"),
            "remain_test_count": c.get("remain_test_count"),
            "remain_factory_test_num": c.get("remain_factory_test_num"),
        })

    return merged


def parse_pressure_logs(lines: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Pressure pipeline (V2.2):
      - pre_filter: all matched lines (including ungrouped but valid logs)
      - post_filter: minimal validity filter (safe, can be tightened later)
      - merged: 3-line join within 1 second window (P0P_CLOT anchor)
    """
    pre_filter: List[Dict[str, Any]] = []

    for idx, line in enumerate(lines):
        line_lower = line.lower()

        # 1) match type by keyword
        matched_type = None
        for k, pattern in PRESSURE_PATTERNS.items():
            if pattern in line_lower:
                matched_type = k
                break
        if not matched_type:
            continue

        # 2) timestamp (epoch inside brackets) - you already implemented extract_timestamp()
        ts = extract_timestamp(line)  # ensure this exists in parser.py

        # 3) field extraction
        fields: Dict[str, Any] = {}

        # best effort component_id extraction (only guaranteed on p0p line in your sample)
        cid = _extract_component_id(line)
        if cid is not None:
            fields["component_id"] = cid

        if matched_type == "P0P_CLOT":
            # component_id must exist for p0p; if missing it's still kept in pre_filter for audit
            fields["p0"] = _try_int(RE_P0.search(line), default=None)
            fields["pp0"] = _try_int(RE_PP0.search(line), default=None)
            fields["pp"] = _try_int(RE_PP.search(line), default=None)
            fields["pe"] = _try_int(RE_PE.search(line), default=None)

        elif matched_type == "REMAIN_VOL":
            mp = RE_REAGENT_POS.search(line)
            if mp:
                fields["reagent_pos"] = mp.group(1)
            mt = RE_COMPONENT_TYPE.search(line)
            if mt:
                fields["component_type"] = mt.group(1)
            fields["level_height"] = _try_int(RE_LEVEL_HEIGHT.search(line), default=None)
            fields["new_remain_vol"] = _try_float(RE_NEW_REMAIN_VOL.search(line), default=None)
            fields["execute_result"] = _try_int(RE_EXECUTE_RESULT.search(line), default=None)
            fields["remain_vol_detect_type"] = _try_int(RE_REMAIN_VOL_DETECT_TYPE.search(line), default=None)
            fields["success"] = ("success" in line_lower)

        elif matched_type == "REMAIN_CNT":
            mp = RE_REAGENT_POS.search(line)
            if mp:
                fields["reagent_pos"] = mp.group(1)
            mt = RE_COMPONENT_TYPE.search(line)
            if mt:
                fields["component_type"] = mt.group(1)
            mn = RE_CHEMISTRY_NAME.search(line)
            if mn:
                fields["chemistry_name"] = mn.group(1).strip()
            fields["remain_test_count"] = _try_int(RE_REMAIN_TEST_COUNT.search(line), default=None)
            fields["remain_factory_test_num"] = _try_int(RE_REMAIN_FACTORY_TEST_NUM.search(line), default=None)
            fields["success"] = ("success" in line_lower)

        row = {
            "index": idx,
            "timestamp": ts,
            "type": matched_type,
            "raw_line": line.rstrip(),
        }
        row.update(fields)
        pre_filter.append(row)

    # post_filter (D: keep all in pre_filter; only subset enters post_filter)
    post_filter = [r for r in pre_filter if _is_valid_for_post_filter(r)]

    # merged (V2.2: 1 second join window; only merges rows that have component_id on all 3)
    merged = _merge_pressure(post_filter)

    return {
        "pre_filter": pre_filter,
        "post_filter": post_filter,
        "merged": merged,
    }

def parse_file(
    filepath: str,
    *,
    rules: Dict[str, List[Dict[str, Any]]],
    components: List[str],
    data_type: str,
    encoding: str = "utf-8",
):
    # ✅ Pressure: use dedicated pipeline (V2.2)
    if data_type == "pressure":
        return parse_pressure_file(filepath, encoding=encoding)

    # ---- 原逻辑保持不变（液面等）----
    try:
        f = open(filepath, "r", encoding=encoding, errors="replace")
    except Exception:
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
        all_rows.sort(key=lambda r: r.ts)
        return all_rows

 

def parse_pressure_file(filepath: str, *, encoding: str = "utf-8") -> Dict[str, List[Dict[str, Any]]]:
    """
    Pressure parsing pipeline (V2.2):
      returns {
        "pre_filter": [rowdict...],
        "post_filter": [rowdict...],
        "merged": [rowdict...],
      }
    """
    try:
        f = open(filepath, "r", encoding=encoding, errors="replace")
    except Exception:
        f = open(filepath, "r", encoding="utf-8", errors="replace")

    with f:
        lines = list(f)  # 先简单落地；后面优化为流式也行
    return parse_pressure_logs(lines)

