# Schema validator followed symlinked parent directory

## 现象

- 触发命令、接口或页面：调用 `validate_schema()` 或运行 `scripts/validate_schema.py docs/schema.sql`，且 `docs` 父级路径是指向仓库外目录的 symlink。
- 实际结果：validator 会跟随 symlinked parent 读取仓库外 `schema.sql`；只要目标 SQL 满足当前 schema 检查，校验返回成功。
- 期望结果：`docs/schema.sql` 作为数据库模型真理来源时，文件和父级目录都必须来自普通仓库文件树；遇到 symlinked parent 应返回 schema issue。

## 原因

- 根因：`validate_schema()` 只拒绝 schema 文件本身是 symlink 或非普通文件，没有检查父级目录链。
- 影响范围：发布前 schema gate 可能基于仓库边界外的 SQL 内容，削弱数据库模型和当前 checkout 的一致性证明。

## 修复

- 在 `scripts/validate_schema.py` 中增加 schema 路径父级链 symlink 检查。
- 当任一父级目录是 symlink 时，返回 `schema file parent is not a regular directory` issue，不再继续读取目标 schema。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_schema_validator_rejects_symlinked_schema_parent -q` 失败，当前实现返回空列表。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_schema_validator_rejects_symlinked_schema_parent tests/test_release_contracts.py::test_schema_validator_rejects_symlinked_schema_file tests/test_release_contracts.py::test_schema_validator_runs_as_release_script -q` 通过，`3 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "schema_validator"` 通过，`9 passed, 258 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`832 passed`；`bash scripts/release_check.sh` 通过。
