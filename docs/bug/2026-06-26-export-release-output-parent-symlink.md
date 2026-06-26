# Export release artifacts followed output directory parent symlinks

## 现象

如果 `scripts/export_release_artifacts.py --output-dir` 的直接父目录是 symlink，例如 `linked-parent/release` 且 `linked-parent -> ../outside-release-parent`，导出流程会跟随父目录 symlink，把 handoff artifacts 写到指定路径树之外。

## 原因

`export_release_artifacts()` 只拒绝最终 `output_dir` 自身是 symlink 的情况，然后调用 `output_dir.resolve()`。当任一父目录是 symlink 时，`resolve()` 会把输出路径解析到 symlink 目标目录。

## 修复

在解析输出目录前检查原始 `output_dir.parent`，如果直接父目录是 symlink，则返回结构化 `ok:false` report，并报告 `release artifact output directory parent is not a regular directory`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_rejects_output_dir_symlink_parent -q` 失败，`report` 没有 `ok:false`，当前实现继续导出。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_output_dir_not_directory tests/test_release_contracts.py::test_export_release_artifacts_rejects_output_dir_symlink tests/test_release_contracts.py::test_export_release_artifacts_rejects_output_dir_symlink_parent tests/test_release_contracts.py::test_export_release_artifacts_rejects_dirty_output_dir tests/test_release_contracts.py::test_export_release_artifacts_script_writes_handoff_bundle -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `764 passed`。
