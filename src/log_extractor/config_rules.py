"""规则配置（可替换/扩展）。

说明：
- 规则以 data_type -> component -> list[rules] 组织。
- 每条 rule:
  - match: 行匹配关键字（contains, case-insensitive）
  - extracts: dict，key 为字段名，value 为提取表达式（regex 或 'after:<token>'）
  - filters: 可选，支持简单比较（> >= < <= == !=）
"""
# =========================
# Pressure rules (V2.2 baseline) - FINAL
# =========================

# ComponentId mapping for pressure logs
PRESSURE_COMPONENT_ID = {
    "S1": 64,
    "S2": 65,
    "ISE": 58,
    "R11": 76,
    "R12": 77,
    "R21": 86,
    "R22": 87,
}

# Log line patterns for pressure extraction
PRESSURE_PATTERNS = {
    "P0P_CLOT": "p0p clot values",
    "REMAIN_VOL": "calcRemainVolume",
    "REMAIN_CNT": "calcRemainTestCount",
}

# Merge window seconds (per V2.2)
PRESSURE_MERGE_WINDOW_SEC = 1.0

LIQUID_RULES = {
    "S1": [
        {
            "match": "SI_S1_Down_Asp_Up levelPos",
            "extracts": {
                "levelPos": {"after": "levelPos =", "type": "float"},
                "verLimitPos": {"after": "verLimitPos =", "type": "float"},
            },
            "filters": [{"field": "verLimitPos", "op": ">", "value": 1900}],
        }
    ],
    "S2": [
        {
            "match": "SI_S2_Down_Asp_Up levelPos",
            "extracts": {
                "levelPos": {"after": "levelPos =", "type": "float"},
                "verLimitPos": {"after": "verLimitPos =", "type": "float"},
            },
            "filters": [{"field": "verLimitPos", "op": ">", "value": 1900}],
        }
    ],
    "ISE": [
        {
            "match": "################ levelPos =",
            "extracts": {
                "levelPos": {"after": "levelPos =", "type": "float"},
                "verLimitPos": {"after": "verLimitPos =", "type": "float"},
            },
            "filters": [{"field": "verLimitPos", "op": ">", "value": 3000}],
        }
    ],
    # 试剂针：V2.0 文档显示 levelHeight 与 chemstryName 往往出现在不同类型的行
    "R11": [
        {
            "match": "calcRemainVolume success, reagentPos: {1-",
            "extracts": {"levelHeight": {"after": "levelHeight:", "type": "float"}},
        },
        {
            "match": "[workflow] calcRemainTestCount success, chemstryName:",
            "extracts": {"chemstryName": {"after": "chemstryName:", "type": "str"}},
        },
    ],
    "R12": [
        {
            "match": "calcRemainVolume success, reagentPos: {1-",
            "extracts": {"levelHeight": {"after": "levelHeight:", "type": "float"}},
        },
        {
            "match": "[workflow] calcRemainTestCount success, chemstryName:",
            "extracts": {"chemstryName": {"after": "chemstryName:", "type": "str"}},
        },
    ],
    "R21": [
        {
            "match": "calcRemainVolume success, reagentPos: {2-",
            "extracts": {"levelHeight": {"after": "levelHeight:", "type": "float"}},
        },
        {
            "match": "[workflow] calcRemainTestCount success, chemstryName:",
            "extracts": {"chemstryName": {"after": "chemstryName:", "type": "str"}},
        },
    ],
    "R22": [
        {
            "match": "calcRemainVolume success, reagentPos: {2-",
            "extracts": {"levelHeight": {"after": "levelHeight:", "type": "float"}},
        },
        {
            "match": "[workflow] calcRemainTestCount success, chemstryName:",
            "extracts": {"chemstryName": {"after": "chemstryName:", "type": "str"}},
        },
    ],
}

# 压力规则：你已说明“检索字段表不是最新”，此处保留占位。
PRESSURE_RULES = {
    "S1": [],
    "S2": [],
    "ISE": [],
    "R11": [],
    "R12": [],
    "R21": [],
    "R22": [],
}

RULES_BY_TYPE = {
    "liquid": LIQUID_RULES,
    "pressure": PRESSURE_RULES,
}
