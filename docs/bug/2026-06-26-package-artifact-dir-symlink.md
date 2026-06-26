# Package release artifacts followed artifact directory symlinks

## 现象

如果 `scripts/package_release_artifacts.py --artifact-dir` 指向一个目录 symlink，例如 `release -> ../outside-release`，打包流程会跟随 symlink 验证并打包目标目录，把指定目录外的 handoff artifacts 写入 release zip。

## 原因

`package_release_artifacts()` 在调用 `validate_release_artifacts()` 前先执行 `artifact_dir.resolve()`。这会把目录 symlink 转换成目标目录路径，从而绕过 `validate_release_artifacts()` 对原始 artifact-dir symlink 的拒绝逻辑。

## 修复

在解析 artifact 目录前先检查原始 `artifact_dir.is_symlink()`。命中时返回结构化 `ok:false` report，并报告 `release artifact directory is not a regular directory`，避免打包 symlink 目标目录。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_rejects_artifact_dir_symlink -q` 失败，当前实现返回 `ok:true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_rejects_artifact_dir_symlink tests/test_release_contracts.py::test_package_release_artifacts_removes_stale_output_on_validation_failure tests/test_release_contracts.py::test_package_release_artifacts_reports_output_path_not_file tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_symlink tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_parent_symlink tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `766 passed`。
