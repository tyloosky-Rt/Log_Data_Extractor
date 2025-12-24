from log_extractor.config_rules import RULES_BY_TYPE
from log_extractor.parser import parse_file

def test_basic_parse(tmp_path):
    p = tmp_path / "t.log"
    p.write_text("[12-17 13:59:59][1765979990.826] SI_S1_Down_Asp_Up levelPos levelPos = 123 verLimitPos = 2000\n", encoding="utf-8")
    rows = parse_file(str(p), rules=RULES_BY_TYPE["liquid"], components=["S1"], data_type="liquid")
    assert len(rows) == 1
    assert rows[0].value1 == 123.0
