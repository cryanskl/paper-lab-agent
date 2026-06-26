# Package release artifacts 输出路径为目录会崩溃

## 现象

如果 `scripts/package_release_artifacts.py --output` 指向一个已经存在的目录，打包流程会在清理旧输出或写 zip 时抛出异常，而不是返回结构化 validation report。

## 原因

`package_release_artifacts()` 只校验输出路径是否位于 artifact 目录内，没有先判断输出路径是否是普通文件。artifact validation 失败时会对目录执行 `Path.unlink()`，导致 `PermissionError` 或 `IsADirectoryError`。

## 修复

在 artifact validation 前增加输出路径类型校验：当 `output_path.exists() and not output_path.is_file()` 时，直接返回 `release package output is not a file: ...` issue，并保留原目录不被破坏。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_reports_output_path_not_file -q` 失败，抛出 `PermissionError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_reports_output_path_not_file -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle tests/test_release_contracts.py::test_package_release_artifacts_removes_stale_output_on_validation_failure tests/test_release_contracts.py::test_package_release_artifacts_reports_output_path_not_file tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_inside_artifact_dir -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `750 passed`。
