# Package release artifacts followed output parent symlinks

## 现象

如果 `scripts/package_release_artifacts.py --output` 的直接父目录是 symlink，例如 `linked-parent/paper-lab-agent-release.zip` 且 `linked-parent -> ../outside-package-parent`，打包流程会跟随父目录 symlink，把 release zip 写到指定路径树之外。

## 原因

`package_release_artifacts()` 只拒绝输出文件本身是 symlink 的情况，然后调用 `output_path.resolve()`。当直接父目录是 symlink 时，`resolve()` 会把输出路径解析到 symlink 目标目录。

## 修复

在解析输出路径前检查原始 `output_path.parent`，如果直接父目录是 symlink，则返回结构化 `ok:false` report，并报告 `release package output parent is not a regular directory`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_parent_symlink -q` 失败，当前实现返回 `ok:true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_reports_output_path_not_file tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_symlink tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_parent_symlink tests/test_release_contracts.py::test_package_release_artifacts_reports_output_parent_not_directory tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_inside_artifact_dir tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `765 passed`。
