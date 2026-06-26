# Release package validator 遇到目录路径会崩溃

## 现象

如果 `scripts/validate_release_package.py --package` 指向一个目录，validator 会在计算 package sha256 时抛出 `IsADirectoryError`，而不是返回结构化 validation report。

## 原因

`validate_release_package()` 在判断 package path 是否存在后，先调用 `sha256_file(package_path)`。路径存在但不是普通文件时，`Path.read_bytes()` 会抛出异常。

## 修复

在计算 sha256 前先判断 `package_path.exists() and not package_path.is_file()`，返回 `release package is not a file: ...` issue，并保持报告结构一致。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_reports_package_path_not_file -q` 失败，抛出 `IsADirectoryError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_reports_package_path_not_file -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_reports_package_path_not_file tests/test_release_contracts.py::test_validate_release_package_script_rejects_tampered_zip_artifact tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `749 passed`。
