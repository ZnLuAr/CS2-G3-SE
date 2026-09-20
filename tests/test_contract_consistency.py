"""核对设计与源码的公开格式；只需标准库，不运行占位方法或连接数据库。

在仓库根目录运行：python -B -X utf8 -m unittest discover -s tests -p test_contract_consistency.py -v
这些检查只能发现声明漂移，不能证明权限、事务或 SQL 在 MySQL 中执行正确。
"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def parse_file(path: Path) -> ast.Module:
    """读取 UTF-8 文件并解析语法，不导入依赖、不执行方法。"""
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def expression(node: ast.AST | None) -> str | None:
    """去掉空白差异，保留类型、默认值和参数顺序。"""
    return ast.dump(node, include_attributes=False) if node is not None else None


def fields(node: ast.ClassDef) -> dict[str, tuple[str | None, str | None]]:
    """提取类中显式声明的字段、类型和默认值。"""
    return {
        item.target.id: (expression(item.annotation), expression(item.value))
        for item in node.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }


def sql_columns(body: str) -> dict[str, tuple[str, bool]]:
    """解析本文固定 DDL 格式中的列类型和可空性；不充当 SQL 执行器。"""
    body = re.sub(r"--[^\n]*", "", body)
    # 只匹配列声明，跳过外键、索引和 CHECK 表达式。
    pattern = (
        r"(?:^|,)\s*(\w+)\s+"
        r"(BIGINT|INT|BOOLEAN|VARCHAR\(\d+\)|CHAR\(\d+\)|"
        r"DECIMAL\(\d+,\d+\)|DATETIME\(6\)|DATE)(?=\s|,|$)"
    )
    result = {}
    for match in re.finditer(pattern, body):
        remainder = body[match.end():].split(",", 1)[0]
        nullable = "NOT NULL" not in remainder and "PRIMARY KEY" not in remainder
        result[match[1]] = (match[2], nullable)
    return result


class ContractConsistencyTests(unittest.TestCase):
    """对照三个独立来源，防止只改文档、源码或表结构中的一个。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.design = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")
        cls.blocks = [
            ast.parse(block)
            for block in re.findall(r"```python\n(.*?)\n```", cls.design, re.S)
        ]
        cls.documented_classes: dict[str, list[ast.ClassDef]] = {}
        for block in cls.blocks:
            for node in block.body:
                if isinstance(node, ast.ClassDef):
                    cls.documented_classes.setdefault(node.name, []).append(node)

    def test_public_fields_defaults_and_literals_match_design(self) -> None:
        """公共数据类的字段、默认值、修饰器及 Literal 值必须一致。"""
        for relative in ["src/models/contracts.py", "src/config.py", "src/errors/base.py"]:
            for node in parse_file(ROOT / relative).body:
                if isinstance(node, ast.ClassDef) and node.decorator_list:
                    with self.subTest(data_class=node.name):
                        documented = self.documented_classes[node.name]
                        for counterpart in documented:
                            self.assertEqual(fields(node), fields(counterpart))
                            self.assertEqual(
                                list(map(expression, node.decorator_list)),
                                list(map(expression, counterpart.decorator_list)),
                            )
                elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Subscript):
                    if ast.unparse(node.value.value) != "Literal":
                        continue
                    name = ast.unparse(node.targets[0])
                    matches = [
                        item for block in self.blocks for item in block.body
                        if isinstance(item, ast.Assign)
                        and ast.unparse(item.targets[0]) == name
                    ]
                    with self.subTest(literal=name):
                        self.assertTrue(matches, f"设计缺少 {name}")
                        for counterpart in matches:
                            self.assertEqual(expression(node.value), expression(counterpart.value))

    def test_service_repository_and_example_signatures_match(self) -> None:
        """服务/仓储方法须完整写入设计，已有示例也不能沿用旧签名。"""
        source_classes = {}
        source_functions = {}
        for path in [ROOT / "main.py", *sorted((ROOT / "src").rglob("*.py"))]:
            for node in parse_file(path).body:
                if isinstance(node, ast.ClassDef):
                    source_classes[node.name] = (path, node)
                elif isinstance(node, ast.FunctionDef):
                    source_functions[node.name] = node

        for name, (path, node) in source_classes.items():
            documented = self.documented_classes.get(name, [])
            actual_methods = {m.name: m for m in node.body if isinstance(m, ast.FunctionDef)}
            declared_methods = {}
            for counterpart in documented:
                for method in counterpart.body:
                    if isinstance(method, ast.FunctionDef):
                        declared_methods.setdefault(method.name, []).append(method)
            if path.parent.name in {"services", "db"}:
                self.assertEqual(set(actual_methods), set(declared_methods), name)
            for method_name, variants in declared_methods.items():
                with self.subTest(class_name=name, method=method_name):
                    self.assertIn(method_name, actual_methods)
                    for counterpart in variants:
                        actual = actual_methods[method_name]
                        self.assertEqual(expression(actual.args), expression(counterpart.args))
                        self.assertEqual(expression(actual.returns), expression(counterpart.returns))

        for block in self.blocks:
            for node in block.body:
                if isinstance(node, ast.FunctionDef) and node.name in source_functions:
                    with self.subTest(function=node.name):
                        actual = source_functions[node.name]
                        self.assertEqual(expression(actual.args), expression(node.args))
                        self.assertEqual(expression(actual.returns), expression(node.returns))

    def test_storage_fields_types_and_nullability_match_sql(self) -> None:
        """逐表核对存储字段与 SQL 的列、基础类型、可空性和枚举值。"""
        tables = dict(re.findall(
            r"CREATE TABLE (\w+) \((.*?)\) ENGINE=InnoDB", self.design, re.S,
        ))
        contracts = parse_file(ROOT / "src/models/contracts.py")
        literals = {
            node.targets[0].id: (
                [value]
                if isinstance((value := ast.literal_eval(node.value.slice)), str)
                else value
            )
            for node in contracts.body
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Subscript)
            and ast.unparse(node.value.value) == "Literal"
        }
        covered = set()
        for path in sorted((ROOT / "src/models").glob("*.py")):
            for node in parse_file(path).body:
                if not isinstance(node, ast.ClassDef):
                    continue
                table_match = re.search(r"对应 (\w+) 表", ast.get_docstring(node) or "")
                if not table_match:
                    continue
                table = table_match[1]
                covered.add(table)
                with self.subTest(table=table):
                    columns = sql_columns(tables[table])
                    self.assertEqual(set(fields(node)), set(columns))
                    for item in node.body:
                        if not isinstance(item, ast.AnnAssign):
                            continue
                        column = item.target.id
                        sql_type, nullable = columns[column]
                        python_type = ast.unparse(item.annotation)
                        self.assertEqual(python_type.endswith(" | None"), nullable, column)
                        base = python_type.removesuffix(" | None")
                        expected = (
                            "int" if sql_type in {"INT", "BIGINT"}
                            else "bool" if sql_type == "BOOLEAN"
                            else "Decimal" if sql_type.startswith("DECIMAL")
                            else "datetime" if sql_type.startswith("DATETIME")
                            else "date" if sql_type == "DATE"
                            else "str"
                        )
                        self.assertEqual("str" if base in literals else base, expected, column)
                        if base in literals:
                            body = tables[table]
                            values = set(re.findall(rf"\b{column}\s*=\s*'([^']+)'", body))
                            for group in re.findall(rf"\b{column}\s+IN\s*\(([^)]+)\)", body):
                                values.update(re.findall(r"'([^']+)'", group))
                            self.assertEqual(set(literals[base]), values, column)
        self.assertEqual(covered, set(tables) - {"schema_versions"})


if __name__ == "__main__":
    unittest.main()
