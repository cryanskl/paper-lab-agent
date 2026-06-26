# Export release artifacts followed expected-name symlinks

## 现象

如果 `scripts/export_release_artifacts.py --output-dir` 目录里已经存在允许的 handoff 文件名，但该路径是 symlink，例如 `openapi.json -> ../outside-openapi.json`，导出流程会跟随 symlink 写入，可能覆盖 release 目录外的文件。

## 原因

`export_release_artifacts()` 只检查允许文件名是否存在且 `Path.is_file()` 为真。`Path.is_file()` 会跟随 symlink，因此指向普通文件的 symlink 被当成安全输出路径。

## 修复

导出前检查同名 artifact 路径时，将 `Path.is_symlink()` 也判定为不安全，并返回结构化 `ok:false` report；普通目录场景保留原有错误文案。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_rejects_expected_artifact_symlink -q` 失败，`report` 没有 `ok:false`，当前实现继续导出。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_expected_artifact_path_not_file tests/test_release_contracts.py::test_export_release_artifacts_rejects_expected_artifact_symlink tests/test_release_contracts.py::test_export_release_artifacts_script_writes_handoff_bundle -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `758 passed`。
