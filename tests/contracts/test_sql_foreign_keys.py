"""核对架构承诺的数据库归属和来源约束。"""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def _tables(source: str) -> dict[str, str]:
    return dict(re.findall(r"CREATE TABLE (\w+) \((.*?)\) ENGINE=InnoDB", source, re.S))


def _foreign_keys(body: str) -> set[tuple[tuple[str, ...], str, tuple[str, ...]]]:
    """按字段顺序核对复合外键，忽略排版和约束名称。"""
    return {
        (tuple(re.findall(r"\w+", source)), target_table, tuple(re.findall(r"\w+", target)))
        for source, target_table, target in re.findall(
            r"FOREIGN KEY\s*\(([^)]+)\)\s*REFERENCES\s*(\w+)\s*\(([^)]+)\)",
            body,
            re.S,
        )
    }


def test_initial_schema_preserves_documented_foreign_keys():
    """发卡、赠卡和课包来源须按销售项、会员、产品及规则版本共同约束。"""
    designed = _tables((ROOT / "docs/architecture/backend.md").read_text(encoding="utf-8"))
    actual = _tables((ROOT / "sql/001_initial_schema.sql").read_text(encoding="utf-8"))

    assert designed.keys() <= actual.keys()
    for name, body in designed.items():
        assert _foreign_keys(body) == _foreign_keys(actual[name]), f"{name} 外键与架构不一致"
