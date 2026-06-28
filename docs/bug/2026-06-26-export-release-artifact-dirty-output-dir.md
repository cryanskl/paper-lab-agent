# Export release artifacts 会写入脏输出目录

## 现象

如果 `scripts/export_release_artifacts.py --output-dir` 指向一个已经包含额外文件的目录，例如 `old-demo-summary.json`，导出命令仍会返回成功并写入新的 handoff 文件。后续 `scripts/validate_release_artifacts.py` 才会发现 unexpected file，导致错误暴露得太晚。

## 原因

`export_release_artifacts()` 只检查输出路径是否是目录，没有在写入 artifact 前检查目录内是否已有非 handoff 文件。

## 修复

在写入 `openapi.json`、`demo-summary.json` 和 `release-manifest.json` 前检查输出目录。目录存在且包含三份允许 handoff 文件以外的文件时，立即返回 `release artifact output directory contains unexpected files: ...`，不覆盖或新增 artifact。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_rejects_dirty_output_dir -q` 失败，返回 manifest 且没有 `ok:false`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_rejects_dirty_output_dir -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_script_writes_handoff_bundle tests/test_release_contracts.py::test_export_release_artifacts_reports_output_dir_not_directory tests/test_release_contracts.py::test_export_release_artifacts_rejects_dirty_output_dir tests/test_release_contracts.py::test_validate_release_artifacts_script_accepts_handoff_bundle tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `754 passed`。
