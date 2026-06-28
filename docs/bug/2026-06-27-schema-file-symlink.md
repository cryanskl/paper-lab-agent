# Schema validator accepted symlinked schema file

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_schema.py docs/schema.sql` 或直接调用 `validate_schema()`，且 schema 路径是指向仓库外 SQL 文件的 symlink。
- 实际结果：只要 symlink 目标文件包含有效 schema，validator 会跟随 symlink 并返回成功。
- 期望结果：数据模型真理来源检查应拒绝 symlinked schema 文件，避免 release gate 使用仓库边界外的数据模型定义。

## 原因

- 根因：`validate_schema()` 只检查 schema 路径是否存在，然后直接 `read_text()` 执行 SQL，没有拒绝 symlink 或非普通文件。
- 影响范围：schema 表、列、索引、触发器、seed 数据和 FTS 验证的输入可信度。

## 修复

- 在 `scripts/validate_schema.py` 的 `validate_schema()` 入口增加普通文件检查。
- 当 schema 路径是 symlink 或非普通文件时，返回 `schema file is not a regular file` issue，不再继续读取目标内容。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_schema_validator_rejects_symlinked_schema_file -q` 失败，当前实现返回空列表。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_schema_validator_rejects_symlinked_schema_file -q` 通过，`1 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "schema_validator"` 通过，`8 passed, 252 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`825 passed`；`bash scripts/release_check.sh` 通过。
