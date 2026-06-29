# Release artifact validator misreported directory artifacts as unreadable

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_release_artifacts.py --artifact-dir <dir>`，且必需 artifact 路径如 `openapi.json` 被错误创建成目录。
- 实际结果：validator 报告 `OpenAPI artifact unreadable: [Errno 21] Is a directory`，把结构性路径错误归类成读取错误。
- 期望结果：validator 应报告 `OpenAPI artifact is not a regular file: <path>`，和 symlink / broken symlink artifact 的诊断语义保持一致。

## 原因

- 根因：`read_json()` 只在路径是 symlink 或缺失时提前返回，未在 `read_text()` 前检查存在路径是否为普通文件。
- 影响范围：发布 handoff artifact 目录损坏时，错误信息不够稳定，CI 或交付检查里定位路径类型问题会变慢。

## 修复

- 修改文件：`scripts/validate_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：`read_json()` 对存在但不是普通文件的 artifact 提前返回 `is not a regular file` issue；非 UTF-8 等真实读取问题仍保留 `unreadable` 诊断。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_directory_required_artifact -q` 失败，当前实现输出 `OpenAPI artifact unreadable: [Errno 21] Is a directory`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_directory_required_artifact tests/test_release_contracts.py::test_validate_release_artifacts_rejects_required_artifact_symlink tests/test_release_contracts.py::test_validate_release_artifacts_rejects_broken_required_artifact_symlink tests/test_release_contracts.py::test_validate_release_artifacts_reports_checksum_artifact_not_file tests/test_release_contracts.py::test_validate_release_artifacts_reports_non_utf8_required_artifact tests/test_release_contracts.py::test_validate_release_artifacts_reports_artifact_dir_not_directory -q` 通过，6 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1249 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1249 passed。
