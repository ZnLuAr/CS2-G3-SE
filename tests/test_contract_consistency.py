"""核对设计与源码的公开格式；只需标准库，不运行占位方法或连接数据库。

在仓库根目录运行：python -B -X utf8 -m unittest discover -s tests -p test_contract_consistency.py -v
这些检查只能发现声明漂移，不能证明权限、事务或 SQL 在 MySQL 中执行正确。
"""

from __future__ import annotations

import ast
import copy
from pathlib import Path
import re
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]


def parse_file(path: Path) -> ast.Module:
    """读取 UTF-8 文件并解析语法，不导入依赖、不执行方法。"""
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def parse_document_block(block: str) -> ast.Module | None:
    """解析接口代码块；缩进片段先去除公共缩进，纯教学片段不参与契约比较。"""
    for source in (block, textwrap.dedent(block)):
        try:
            return ast.parse(source)
        except (IndentationError, SyntaxError):
            continue
    return None


def expression(node: ast.AST | None) -> str | None:
    """去掉空白差异，保留类型、默认值和参数顺序。"""
    return ast.dump(node, include_attributes=False) if node is not None else None


def callable_arguments(node: ast.FunctionDef, *, bound: bool = False) -> str:
    """比较调用方可见参数；绑定方法在 fixture 暴露时不包含 self。"""
    args = copy.deepcopy(node.args)
    if bound and args.args and args.args[0].arg == "self":
        args.args = args.args[1:]
    return expression(args) or ""


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
        cls.blocks = []
        cls.block_paths: dict[int, Path] = {}
        cls.block_sources: dict[int, str] = {}
        for block in re.findall(r"```python\n(.*?)\n```", cls.design, re.S):
            if "self.session.commit()" in block:
                continue
            parsed = parse_document_block(block)
            if parsed is None:
                continue
            cls.blocks.append(parsed)
            cls.block_sources[id(parsed)] = block
            declared_paths = set(re.findall(
                r"^\s*#\s*((?:main\.py|src/[^\s：:]+\.py|tests/[^\s：:]+\.py))",
                block,
                re.M,
            ))
            if len(declared_paths) == 1:
                cls.block_paths[id(parsed)] = ROOT / declared_paths.pop()
        cls.documented_classes: dict[str, list[ast.ClassDef]] = {}
        cls.documented_class_paths: dict[int, Path | None] = {}
        for block in cls.blocks:
            for node in block.body:
                if isinstance(node, ast.ClassDef):
                    cls.documented_classes.setdefault(node.name, []).append(node)
                    source_before_class = "\n".join(
                        cls.block_sources[id(block)].splitlines()[:node.lineno - 1]
                    )
                    preceding_paths = re.findall(
                        r"^\s*#\s*((?:main\.py|src/[^\s：:]+\.py|tests/[^\s：:]+\.py))",
                        source_before_class,
                        re.M,
                    )
                    cls.documented_class_paths[id(node)] = (
                        ROOT / preceding_paths[-1]
                        if preceding_paths
                        else cls.block_paths.get(id(block))
                    )

    def test_public_fields_defaults_and_literals_match_design(self) -> None:
        """公共数据类的字段、默认值、修饰器及 Literal 值必须一致。"""
        source_data_classes = {}
        required_documentation_paths = {
            ROOT / "src/models/contracts.py",
            ROOT / "src/config.py",
            ROOT / "src/errors/base.py",
        }
        paths = [ROOT / "main.py", *sorted((ROOT / "src").rglob("*.py"))]
        for path in paths:
            for node in parse_file(path).body:
                if isinstance(node, ast.ClassDef) and node.decorator_list:
                    source_data_classes[node.name] = node
                    if path in required_documentation_paths:
                        self.assertIn(node.name, self.documented_classes, f"设计缺少 {node.name}")
                    if node.name in self.documented_classes:
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

        for name, documented in self.documented_classes.items():
            documented_data_classes = [node for node in documented if node.decorator_list]
            if not documented_data_classes:
                continue
            with self.subTest(documented_data_class=name):
                self.assertIn(name, source_data_classes, f"源码缺少设计中的数据类 {name}")
                for counterpart in documented_data_classes:
                    self.assertEqual(fields(source_data_classes[name]), fields(counterpart))

    def test_service_repository_and_example_signatures_match(self) -> None:
        """服务/仓储方法须完整写入设计，已有示例也不能沿用旧签名。"""
        source_classes: dict[tuple[Path, str], ast.ClassDef] = {}
        source_functions: dict[str, list[tuple[Path, ast.FunctionDef]]] = {}
        source_methods: dict[str, list[tuple[Path, ast.FunctionDef]]] = {}
        paths = [
            ROOT / "main.py",
            *sorted((ROOT / "src").rglob("*.py")),
            ROOT / "tests/conftest.py",
        ]
        for path in paths:
            module = parse_file(path)
            for node in module.body:
                if isinstance(node, ast.FunctionDef):
                    source_functions.setdefault(node.name, []).append((path, node))
            for node in ast.walk(module):
                if isinstance(node, ast.ClassDef):
                    source_classes[(path, node.name)] = node
                    for method in node.body:
                        if isinstance(method, ast.FunctionDef):
                            source_methods.setdefault(method.name, []).append((path, method))

        for name, documented in self.documented_classes.items():
            if not any(any(isinstance(item, ast.FunctionDef) for item in node.body) for node in documented):
                continue
            documented_paths = {
                self.documented_class_paths[id(node)]
                for node in documented
                if self.documented_class_paths[id(node)] is not None
            }
            candidates = [
                (path, node) for (path, class_name), node in source_classes.items()
                if class_name == name and (not documented_paths or path in documented_paths)
            ]
            self.assertTrue(candidates, f"源码缺少设计中对应文件的类 {name}")

        documented_functions: dict[str, list[ast.FunctionDef]] = {}
        for block in self.blocks:
            for node in block.body:
                if isinstance(node, ast.FunctionDef):
                    documented_functions.setdefault(node.name, []).append(node)

        service_methods: dict[str, list[tuple[Path, str, ast.FunctionDef]]] = {}
        for (path, name), node in source_classes.items():
            if path.parent != ROOT / "src/services":
                continue
            matching_classes = [
                counterpart for counterpart in self.documented_classes.get(name, [])
                if self.documented_class_paths[id(counterpart)] == path
            ]
            self.assertTrue(
                matching_classes,
                f"设计缺少 {path.relative_to(ROOT)} 中的 {name}",
            )
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and not method.name.startswith("_"):
                    service_methods.setdefault(method.name, []).append((path, name, method))

        for method_name, implementations in service_methods.items():
            for path, class_name, actual in implementations:
                class_candidates = [
                    method
                    for counterpart in self.documented_classes.get(class_name, [])
                    if self.documented_class_paths[id(counterpart)] == path
                    for method in counterpart.body
                    if isinstance(method, ast.FunctionDef) and method.name == method_name
                ]
                top_level_candidates = (
                    documented_functions.get(method_name, [])
                    if len(implementations) == 1
                    else []
                )
                candidates = [*class_candidates, *top_level_candidates]
                with self.subTest(service=class_name, method=method_name):
                    self.assertTrue(
                        candidates,
                        f"设计缺少 {class_name}.{method_name}",
                    )
                    self.assertTrue(
                        any(
                            expression(actual.args) == expression(counterpart.args)
                            and expression(actual.returns) == expression(counterpart.returns)
                            for counterpart in candidates
                        ),
                        f"设计接口 {class_name}.{method_name} 的签名与源码不一致",
                    )

        for (path, name), node in source_classes.items():
            documented = self.documented_classes.get(name, [])
            actual_methods = {m.name: m for m in node.body if isinstance(m, ast.FunctionDef)}
            declared_methods = {}
            for counterpart in documented:
                documented_path = self.documented_class_paths[id(counterpart)]
                if documented_path is not None and documented_path != path:
                    continue
                for method in counterpart.body:
                    if isinstance(method, ast.FunctionDef):
                        declared_methods.setdefault(method.name, []).append(method)
            if path.parent.name == "db" and declared_methods:
                self.assertTrue(
                    set(declared_methods) <= set(actual_methods),
                    f"{name} 缺少设计中声明的方法",
                )
            for method_name, variants in declared_methods.items():
                with self.subTest(class_name=name, method=method_name):
                    self.assertIn(method_name, actual_methods)
                    for counterpart in variants:
                        actual = actual_methods[method_name]
                        typed_parameters = all(
                            arg.annotation is not None for arg in counterpart.args.args[1:]
                        )
                        if typed_parameters or counterpart.returns:
                            self.assertEqual(expression(actual.args), expression(counterpart.args))
                            if counterpart.returns is not None:
                                self.assertEqual(expression(actual.returns), expression(counterpart.returns))

        for block in self.blocks:
            documented_path = self.block_paths.get(id(block))
            for node in block.body:
                if not isinstance(node, ast.FunctionDef):
                    continue
                is_typed = any(arg.annotation for arg in node.args.args) or node.returns
                if not is_typed:
                    continue
                is_method = bool(node.args.args and node.args.args[0].arg == "self")
                candidates = source_methods.get(node.name, []) if is_method else [
                    *source_functions.get(node.name, []), *source_methods.get(node.name, []),
                ]
                if documented_path is not None:
                    candidates = [
                        (path, candidate) for path, candidate in candidates
                        if path == documented_path
                    ]
                with self.subTest(documented_callable=node.name):
                    self.assertTrue(candidates, f"源码缺少设计中的接口 {node.name}")
                    self.assertTrue(
                        any(
                            callable_arguments(
                                actual,
                                bound=not is_method and bool(
                                    actual.args.args and actual.args.args[0].arg == "self"
                                ),
                            ) == callable_arguments(node)
                            and expression(actual.returns) == expression(node.returns)
                            for _, actual in candidates
                        ),
                        f"设计接口 {node.name} 的签名与源码不一致",
                    )

    def test_storage_fields_types_and_nullability_match_sql(self) -> None:
        """逐表核对存储字段与 SQL 的列、基础类型、可空性和枚举值。"""
        design_tables = dict(re.findall(
            r"CREATE TABLE (\w+) \((.*?)\) ENGINE=InnoDB", self.design, re.S,
        ))
        sql_source = (ROOT / "sql/001_initial_schema.sql").read_text(encoding="utf-8")
        tables = dict(re.findall(
            r"CREATE TABLE (\w+) \((.*?)\) ENGINE=InnoDB", sql_source, re.S,
        ))
        self.assertTrue(
            set(design_tables) <= set(tables),
            "架构中展示的核心表必须存在于完整 SQL 脚本",
        )
        for table in design_tables:
            with self.subTest(design_vs_sql=table):
                self.assertEqual(sql_columns(design_tables[table]), sql_columns(tables[table]))
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

    def test_current_guidance_uses_stable_architecture_titles(self) -> None:
        """当前实现导航应引用稳定标题，不应沿用已删除的章节编号。"""
        current_paths = [
            ROOT / "docs/README.md",
            ROOT / "docs/feature-list.csv",
            ROOT / "src/models/contracts.py",
            ROOT / "src/errors/base.py",
            ROOT / "src/services/__init__.py",
            ROOT / "src/db/booking_repo.py",
            ROOT / "src/db/measurement_repo.py",
            *sorted((ROOT / "src/services").glob("*.py")),
        ]
        stale = re.compile(r"(?:设计|架构|设计文档)第\s*\d+(?:\.\d+)?\s*节")
        for path in current_paths:
            with self.subTest(path=path.relative_to(ROOT)):
                source = path.read_text(encoding="utf-8-sig")
                self.assertIsNone(stale.search(source), "请改用架构文档的稳定标题")

    def test_identity_revalidation_has_a_single_ordered_lock_contract(self) -> None:
        """身份复核与账号变更必须共用账号优先、编号升序的事务锁契约。"""
        account_repo = (ROOT / "src/db/account_repo.py").read_text(encoding="utf-8")
        auth_service = (ROOT / "src/services/auth_service.py").read_text(encoding="utf-8")

        self.assertIn(
            "def lock_many(self, account_ids: tuple[int, ...]) -> tuple[Account, ...]",
            account_repo,
        )
        self.assertIn("tuple[Member | None, Coach | None]", account_repo)
        self.assertIn("一条带 ORDER BY id 的锁定当前读", account_repo)
        self.assertIn("指定账号与全部启用管理员的并集", account_repo)
        self.assertIn("先锁当前账号，再通过 lock_profile_links 锁定并读取", auth_service)
        self.assertIn("以锁内记录复核关联和 is_active", auth_service)
        self.assertIn("锁持有到调用方事务结束", auth_service)
        self.assertIn("操作者、旧账号和目标账号去重后按编号升序统一锁定", auth_service)

        concurrency = re.search(
            r"\*\*身份复核与账号变更\*\*：(.*?)(?=\n\*\*只锁需要的资源\*\*：)",
            self.design,
            re.S,
        )
        self.assertIsNotNone(concurrency)
        contract = concurrency.group(1)
        self.assertIn("直到业务提交或回滚", contract)
        self.assertIn("操作者、旧账号和目标账号去重", contract)
        self.assertIn("停用或移交提交后", contract)
        self.assertLess(contract.index("锁当前账号"), contract.index("锁该账号关联"))

    def test_current_schema_version_is_shared_by_all_consumers(self) -> None:
        """应用、seed 和 MySQL fixture 必须引用同一个当前结构版本常量。"""
        connection = parse_file(ROOT / "src/db/connection.py")
        version_assignments = [
            node for node in connection.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "CURRENT_SCHEMA_VERSION"
                for target in node.targets
            )
        ]
        self.assertEqual(len(version_assignments), 1)
        self.assertEqual(ast.literal_eval(version_assignments[0].value), 2)

        for relative_path in ("src/app.py", "src/cmd/db.py", "tests/conftest.py"):
            module = parse_file(ROOT / relative_path)
            checks = [
                node for node in ast.walk(module)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "check_schema"
            ]
            with self.subTest(consumer=relative_path):
                self.assertTrue(checks, "当前结构版本消费者必须调用 check_schema")
                self.assertTrue(
                    all(
                        any(
                            keyword.arg == "required_version"
                            and isinstance(keyword.value, ast.Name)
                            and keyword.value.id == "CURRENT_SCHEMA_VERSION"
                            for keyword in call.keywords
                        )
                        for call in checks
                    ),
                    "check_schema 必须使用 CURRENT_SCHEMA_VERSION",
                )
        self.assertIn("CURRENT_SCHEMA_VERSION = 2", self.design)

    def test_booking_checks_duplicate_before_capacity_everywhere(self) -> None:
        """预约详细流程和规则摘要都必须先检查重复预约，再检查容量。"""
        sections = [
            re.search(
                r"\*\*预约课次\*\*：(.*?)(?=\*\*核实预约操作结果\*\*)",
                self.design,
                re.S,
            ),
            re.search(
                r"### 预约规则(.*?)(?=### 签到与消课规则)",
                self.design,
                re.S,
            ),
        ]
        for index, match in enumerate(sections):
            with self.subTest(section=index):
                self.assertIsNotNone(match)
                section = match.group(1)
                duplicate_anchor = (
                    "已有预约（任何状态）"
                    if "已有预约（任何状态）" in section
                    else "同一会员已预约同一课次（任何状态）"
                )
                self.assertLess(section.index(duplicate_anchor), section.index("已满员"))


if __name__ == "__main__":
    unittest.main()
