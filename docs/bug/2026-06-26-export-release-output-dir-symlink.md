# Export release artifacts followed output directory symlinks

## 现象

如果 `scripts/export_release_artifacts.py --output-dir` 指向一个目录 symlink，例如 `release -> ../outside-release`，导出流程会跟随 symlink 写入，可能把 handoff artifacts 输出到指定目录之外。

## 原因

`export_release_artifacts()` 在检查输出路径类型前先调用 `output_dir.resolve()`。目录 symlink 会被解析成目标目录，后续目录检查和 artifact 写入都作用在 symlink 目标上。

## 修复

在解析输出目录前先检查原始 `output_dir.is_symlink()`。命中时返回结构化 `ok:false` report，并报告 `release artifact output directory is not a regular directory`，避免写入 symlink 目标。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_rejects_output_dir_symlink -q` 失败，`report` 没有 `ok:false`，当前实现继续导出。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_output_dir_not_directory tests/test_release_contracts.py::test_export_release_artifacts_rejects_output_dir_symlink tests/test_release_contracts.py::test_export_release_artifacts_rejects_dirty_output_dir tests/test_release_contracts.py::test_export_release_artifacts_reports_expected_artifact_path_not_file tests/test_release_contracts.py::test_export_release_artifacts_rejects_expected_artifact_symlink tests/test_release_contracts.py::test_export_release_artifacts_script_writes_handoff_bundle -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `761 passed`。
