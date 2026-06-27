# Schema validator crashed on unreadable schema

## 现象

- 触发命令、接口或页面：运行 `python scripts/validate_schema.py docs/schema.sql` 或调用 `validate_schema(schema_path)`，且 `schema.sql` 不是 UTF-8 文本或读取阶段抛出 `OSError`。
- 实际结果：校验器在执行 schema SQL 前读取文件时抛出底层异常，例如 `UnicodeDecodeError` traceback。
- 期望结果：schema gate 应返回稳定 issue，指出 schema 文件不可读，而不是中断整个 release gate。

## 原因

- 根因：`scripts/validate_schema.py` 的 `validate_schema()` 在确认 schema 路径存在、父级不是 symlink、文件本身是普通文件后，直接在 `conn.executescript(schema_path.read_text(...))` 表达式中读取文件；读取和解码错误没有转换为可诊断 issue。
- 影响范围：schema 真理源校验、release gate、CI 数据模型契约检查。

## 修复

- 修改文件：`scripts/validate_schema.py`、`tests/test_release_contracts.py`。
- 关键行为：schema regular-file 检查通过后、执行 SQL 前，先用 UTF-8 读取 schema；读取或解码失败时返回 `schema file unreadable: ...` issue，不再继续执行 SQL。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_schema_validator_reports_unreadable_schema_file -q` 失败，函数抛出 `UnicodeDecodeError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "schema_validator"` 通过，`10 passed, 294 deselected`；`.venv/bin/python -m py_compile scripts/validate_schema.py` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`911 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `911 passed`。
