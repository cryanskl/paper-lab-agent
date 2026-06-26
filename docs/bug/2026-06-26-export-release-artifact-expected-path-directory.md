# Export release artifacts 遇到 artifact 路径目录会崩溃

## 现象

如果 `scripts/export_release_artifacts.py --output-dir` 目录里已经存在允许的 handoff 文件名，但该路径实际是目录，例如 `openapi.json/`，导出流程会在写入 OpenAPI artifact 时抛出 `IsADirectoryError`。

## 原因

`export_release_artifacts()` 已经检查 unexpected 文件，但允许 `openapi.json`、`demo-summary.json` 和 `release-manifest.json` 这三种名称继续存在。它没有进一步判断这些路径是否是普通文件，导致目录路径进入写文件逻辑。

## 修复

在写入任何 artifact 前检查三份 expected artifact 路径。只要路径存在但不是普通文件，立即返回 `release artifact output path is not a file: ...` issue，不写入其他 handoff 文件。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_expected_artifact_path_not_file -q` 失败，抛出 `IsADirectoryError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_expected_artifact_path_not_file -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_script_writes_handoff_bundle tests/test_release_contracts.py::test_export_release_artifacts_reports_output_dir_not_directory tests/test_release_contracts.py::test_export_release_artifacts_rejects_dirty_output_dir tests/test_release_contracts.py::test_export_release_artifacts_reports_expected_artifact_path_not_file tests/test_release_contracts.py::test_validate_release_artifacts_script_accepts_handoff_bundle tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `755 passed`。
