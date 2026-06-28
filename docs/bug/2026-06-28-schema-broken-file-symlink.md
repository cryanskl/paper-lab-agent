# Schema validator misreported broken schema symlinks as missing

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_schema.py` 或调用 `validate_schema()`，且 schema 文件路径是断开的 symlink。
- 实际结果：validator 返回 `schema not found`。
- 期望结果：validator 应返回 `schema file is not a regular file`，把 schema 文件路径类型错误和真正缺失文件区分开。

## 原因

`validate_schema()` 在 schema 文件普通文件检查前先判断 `schema_path.exists()`。broken symlink 的 `exists()` 为假，函数直接返回 not found，跳过了后续已有的 symlink / regular file 诊断。

## 修复

- 修改文件：`scripts/validate_schema.py`、`tests/test_release_contracts.py`。
- 关键行为：schema 入口只在路径既不存在也不是 symlink 时返回 `schema not found`；broken symlink 会进入普通文件检查并报告 `schema file is not a regular file`。
- 影响范围：只改变断开的 schema 文件 symlink 错误分类；真正缺失 schema、正常 schema、普通 symlink schema、父级异常和 unreadable schema 行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_schema_validator_rejects_broken_symlinked_schema_file -q` 失败，当前实现返回 `schema not found`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_schema_validator_rejects_broken_symlinked_schema_file tests/test_release_contracts.py::test_schema_validator_rejects_symlinked_schema_file tests/test_release_contracts.py::test_schema_validator_rejects_symlinked_schema_parent tests/test_release_contracts.py::test_schema_validator_rejects_file_schema_parent tests/test_release_contracts.py::test_schema_validator_reports_unreadable_schema_file tests/test_release_contracts.py::test_schema_validator_accepts_schema_truth_source tests/test_release_contracts.py::test_schema_validator_runs_as_release_script -q` 通过，`7 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1118 passed`。
