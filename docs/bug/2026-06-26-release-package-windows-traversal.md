# Release package 未识别 Windows 风格 traversal

## 现象

如果 release package zip 中包含 `..\\evil.txt` 这类 Windows 风格 traversal entry，`scripts/validate_release_package.py` 只会报告 artifact mismatch，不会明确报告 unsafe artifact name。

## 原因

unsafe name 检测使用当前系统的 `Path(name)`。在 POSIX 环境下，反斜杠不会被当作路径分隔符，`Path("..\\evil.txt").parts` 不包含 `..`，因此漏掉 Windows 风格 traversal。

## 修复

新增 `is_unsafe_archive_name()`，同时使用 `PurePosixPath` 和 `PureWindowsPath` 检查 zip entry。任一解析方式出现绝对路径或 `..` 段时，都判定为 unsafe。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_windows_traversal_artifact_name -q` 失败，只报告 artifact mismatch。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_windows_traversal_artifact_name -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle tests/test_release_contracts.py::test_validate_release_package_script_rejects_tampered_zip_artifact tests/test_release_contracts.py::test_validate_release_package_reports_package_path_not_file tests/test_release_contracts.py::test_validate_release_package_rejects_windows_traversal_artifact_name -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `756 passed`。
