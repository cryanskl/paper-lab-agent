# Release artifact validator misreported broken file symlinks as missing

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_release_artifacts.py --artifact-dir <dir>`，且必需发布产物文件（例如 `openapi.json`）是断开的 symlink。
- 实际结果：validator 返回 `OpenAPI artifact missing: <path>`。
- 期望结果：validator 应返回 `OpenAPI artifact is not a regular file: <path>`，把路径类型错误和真正缺失 artifact 区分开。

## 原因

`read_json()` 在检查 artifact 文件是否为 symlink 前先调用 `path.exists()`。broken symlink 的 `exists()` 为假，函数直接报告 missing，跳过了已有的 symlink / regular file 诊断。

## 修复

- 修改文件：`scripts/validate_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：必需 JSON artifact 入口先拒绝 symlink，再判断是否缺失；broken symlink 和普通 symlink 都统一报告 `is not a regular file`。
- 影响范围：只改变断开的必需 artifact 文件 symlink 错误分类；真正缺失 artifact、正常普通文件、普通 symlink artifact、artifact 目录 symlink 行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_broken_required_artifact_symlink -q` 失败，当前实现返回 `OpenAPI artifact missing: <path>`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_broken_required_artifact_symlink tests/test_release_contracts.py::test_validate_release_artifacts_rejects_required_artifact_symlink tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink_parent tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink_ancestor -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1125 passed`。
