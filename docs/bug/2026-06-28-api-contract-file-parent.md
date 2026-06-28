# api contract validator reported missing when parent was a file

## 现象

- 触发命令、接口或页面：`python scripts/validate_api_contract.py <file-parent>/接口设计文档.md`，其中 `<file-parent>` 已存在但被误建为普通文件。
- 实际结果：校验返回 `api contract file not found: <file-parent>/接口设计文档.md`。
- 期望结果：校验应返回 `api contract file parent is not a regular directory: <file-parent>`，明确指出接口文档父级路径不是目录。

## 原因

- 根因：`scripts/validate_api_contract.py` 的 CLI 入口在检查父级路径形态前先执行 `contract_path.exists()`，当父级是普通文件时，目标接口文档被判断为不存在并提前返回 not found。
- 影响范围：发布 gate 中的接口契约校验遇到损坏的接口文档父路径时，错误信息不够准确，影响发布前排障。

## 修复

- 修改文件：`scripts/validate_api_contract.py`、`tests/test_release_contracts.py`
- 关键行为：在 contract missing 判断前先拒绝父级 symlink 或普通文件，保留真正缺失接口文档时的 `api contract file not found` 语义。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_api_contract_validator_rejects_file_contract_parent -q` -> `1 failed`
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_api_contract_validator_rejects_file_contract_parent tests/test_release_contracts.py::test_api_contract_validator_rejects_symlinked_contract_parent tests/test_release_contracts.py::test_api_contract_validator_rejects_symlinked_contract_file tests/test_release_contracts.py::test_api_contract_validator_reports_unreadable_contract_file tests/test_release_contracts.py::test_api_contract_validator_runs_as_release_script -q` -> `5 passed`
- 完整 gate：`bash scripts/release_check.sh` -> `1107 passed`
