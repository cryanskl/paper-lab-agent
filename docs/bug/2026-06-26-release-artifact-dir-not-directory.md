# Release artifact validator 遇到非目录 artifact path 会崩溃

## 现象

如果把 `scripts/validate_release_artifacts.py --artifact-dir` 指向一个普通文件，validator 会在枚举顶层文件时抛出 `NotADirectoryError`，而不是返回结构化 validation report。

## 原因

`validate_release_artifacts()` 只判断 `artifact_dir.exists()`，随后直接调用 `artifact_dir.iterdir()`。当路径存在但不是目录时，`iterdir()` 会抛出异常，发布校验 CLI 无法稳定输出 `{ok:false, issues:[...]}`。

## 修复

在枚举 artifact 目录之前检查 `artifact_dir.is_dir()`。路径存在但不是目录时，记录 `release artifact directory is not a directory` issue，并跳过顶层文件枚举，让后续缺失 artifact 校验继续聚合结果。同步更新 README 和 release checklist，明确 handoff validator 会校验 artifact path 本身是目录。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_reports_artifact_dir_not_directory -q` 失败，抛出 `NotADirectoryError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_reports_artifact_dir_not_directory -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_reports_unreadable_required_artifact tests/test_release_contracts.py::test_validate_release_artifacts_reports_non_utf8_required_artifact tests/test_release_contracts.py::test_validate_release_artifacts_script_accepts_handoff_bundle -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`748 passed`。
