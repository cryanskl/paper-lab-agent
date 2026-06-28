# env example validator reported missing when parent was a file

## 现象

- 触发命令、接口或页面：`python scripts/validate_env_example.py <file-parent>/.env.example`，其中 `<file-parent>` 已存在但被误建为普通文件。
- 实际结果：校验返回 `env example not found: <file-parent>/.env.example`。
- 期望结果：校验应返回 `env example parent is not a regular directory: <file-parent>`，明确指出 `.env.example` 父级路径不是目录。

## 原因

- 根因：`scripts/validate_env_example.py` 的 CLI 入口在检查父级路径形态前先执行 `path.exists()`，当父级是普通文件时，目标 `.env.example` 被判断为不存在并提前返回 not found。
- 影响范围：发布 gate 中的环境变量样例校验遇到损坏的 `.env.example` 父路径时，错误信息不够准确，影响发布前排障。

## 修复

- 修改文件：`scripts/validate_env_example.py`、`tests/test_release_contracts.py`
- 关键行为：在 `.env.example` missing 判断前先拒绝父级 symlink 或普通文件，保留真正缺失 `.env.example` 文件时的 `env example not found` 语义。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_file_env_example_parent -q` -> `1 failed`
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_file_env_example_parent tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_env_example_parent tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_env_example tests/test_release_contracts.py::test_env_example_validator_reports_unreadable_env_example -q` -> `4 passed`
- 完整 gate：`bash scripts/release_check.sh` -> `1108 passed`
