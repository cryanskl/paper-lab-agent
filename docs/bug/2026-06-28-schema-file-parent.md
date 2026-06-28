# schema validator reported missing when parent was a file

## 现象

- 触发命令、接口或页面：`python scripts/validate_schema.py <repo>/docs/schema.sql` 或调用 `validate_schema(schema_path)`，其中 `<repo>/docs` 已存在但被误建为普通文件。
- 实际结果：校验返回 `schema not found: <repo>/docs/schema.sql`。
- 期望结果：校验应返回 `schema file parent is not a regular directory: <repo>/docs`，明确指出 schema 父级路径不是目录。

## 原因

- 根因：`validate_schema` 在检查父级路径形态前先执行 `schema_path.exists()`，当 `docs` 是普通文件时，`docs/schema.sql` 被判断为不存在并提前返回 missing。
- 影响范围：发布 gate 中的 schema 校验遇到损坏的 `docs` 路径时，错误信息不够准确，影响发布前排障。

## 修复

- 修改文件：`scripts/validate_schema.py`、`tests/test_release_contracts.py`
- 关键行为：在 schema missing 判断前先拒绝父级 symlink 或普通文件，保留真正缺失 schema 文件时的 `schema not found` 语义。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_schema_validator_rejects_file_schema_parent -q` -> `1 failed`
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_schema_validator_rejects_file_schema_parent tests/test_release_contracts.py::test_schema_validator_rejects_symlinked_schema_parent tests/test_release_contracts.py::test_schema_validator_rejects_symlinked_schema_file tests/test_release_contracts.py::test_schema_validator_reports_unreadable_schema_file tests/test_release_contracts.py::test_schema_validator_runs_as_release_script -q` -> `5 passed`
- 完整 gate：`bash scripts/release_check.sh` -> `1105 passed`
