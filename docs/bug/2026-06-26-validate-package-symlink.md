# Validate release package accepted package symlinks

## 现象

如果 `scripts/validate_release_package.py --package` 指向一个 symlink，例如 `paper-lab-agent-release.zip -> ../outside-package.zip`，validator 会跟随 symlink 读取目标 zip，并把目标文件当成有效 release package。

## 原因

`validate_release_package()` 在检查输入路径类型前先调用 `package_path.resolve()`。指向普通 zip 文件的 symlink 会被解析成目标路径，后续 `Path.is_file()` 和 zip 内容验证都作用在目标文件上。

## 修复

在解析输入路径前先检查原始 `package_path.is_symlink()`。命中时返回结构化 `ok:false` report，并报告 `release package is not a regular file`，避免把 symlink 目标误认为用户指定的 handoff package。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_package_symlink -q` 失败，当前实现返回 `ok:true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_reports_package_path_not_file tests/test_release_contracts.py::test_validate_release_package_rejects_package_symlink tests/test_release_contracts.py::test_validate_release_package_rejects_windows_traversal_artifact_name tests/test_release_contracts.py::test_validate_release_package_rejects_windows_rooted_artifact_name tests/test_release_contracts.py::test_validate_release_package_script_rejects_tampered_zip_artifact -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `760 passed`。
