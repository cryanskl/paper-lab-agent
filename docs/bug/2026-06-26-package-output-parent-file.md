# Package release artifacts 输出父路径为文件会崩溃

## 现象

如果 `scripts/package_release_artifacts.py --output` 的父路径已经是普通文件，例如 `out/paper-lab-agent-release.zip` 的 `out` 是文件，打包流程会在创建输出目录时抛出 `FileExistsError`，而不是返回结构化 validation report。

## 原因

`package_release_artifacts()` 在 artifact validation 通过后直接调用 `output_path.parent.mkdir(parents=True, exist_ok=True)`。当父路径存在但不是目录时，`Path.mkdir()` 会抛异常。

## 修复

在 artifact validation 前先判断 `output_path.parent.exists() and not output_path.parent.is_dir()`。命中时直接返回 `release package output parent is not a directory: ...` issue，不创建目录、不写 zip。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_reports_output_parent_not_directory -q` 失败，抛出 `FileExistsError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_reports_output_parent_not_directory -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle tests/test_release_contracts.py::test_package_release_artifacts_removes_stale_output_on_validation_failure tests/test_release_contracts.py::test_package_release_artifacts_reports_output_path_not_file tests/test_release_contracts.py::test_package_release_artifacts_reports_output_parent_not_directory tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_inside_artifact_dir -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `753 passed`。
