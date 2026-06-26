# Package release artifacts followed output symlinks

## 现象

如果 `scripts/package_release_artifacts.py --output` 指向一个 symlink，例如 `paper-lab-agent-release.zip -> ../outside-package.zip`，打包流程会跟随 symlink 写入，可能覆盖 release 输出路径之外的文件。

## 原因

`package_release_artifacts()` 在检查输出路径类型前先调用 `output_path.resolve()`。指向普通文件的 symlink 会被解析成目标文件路径，后续 `ZipFile(..., mode="w")` 会直接覆盖 symlink 目标。

## 修复

在解析输出路径前先检查原始 `output_path.is_symlink()`。命中时返回结构化 `ok:false` report，并报告 `release package output is not a regular file`，避免写入 symlink 目标。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_symlink -q` 失败，当前实现返回 `ok:true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_reports_output_path_not_file tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_symlink tests/test_release_contracts.py::test_package_release_artifacts_reports_output_parent_not_directory tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_inside_artifact_dir tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `759 passed`。
