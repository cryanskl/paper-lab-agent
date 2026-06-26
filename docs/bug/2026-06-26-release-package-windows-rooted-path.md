# Release package 未识别 Windows rooted path

## 现象

如果 release package zip 中包含 `\\evil.txt` 这类 Windows rooted path entry，`scripts/validate_release_package.py` 只会报告 artifact mismatch，不会明确报告 unsafe artifact name。

## 原因

`PureWindowsPath("\\evil.txt").is_absolute()` 为 `False`，但它仍带有 Windows root。此前 unsafe 检测只检查 `is_absolute()` 和 `..` 段，没有检查 Windows `drive` 或 `root`。

## 修复

扩展 `is_unsafe_archive_name()`：除 POSIX/Windows absolute 和 `..` 段外，也把 `PureWindowsPath(name).drive` 或 `.root` 非空的 entry 判定为 unsafe。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_windows_rooted_artifact_name -q` 失败，只报告 artifact mismatch。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_windows_rooted_artifact_name -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle tests/test_release_contracts.py::test_validate_release_package_script_rejects_tampered_zip_artifact tests/test_release_contracts.py::test_validate_release_package_reports_package_path_not_file tests/test_release_contracts.py::test_validate_release_package_rejects_windows_traversal_artifact_name tests/test_release_contracts.py::test_validate_release_package_rejects_windows_rooted_artifact_name -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `757 passed`。
