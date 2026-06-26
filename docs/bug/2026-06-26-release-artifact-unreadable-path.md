# Release artifact validator 遇到不可读路径会崩溃

## 现象

如果 release artifact 目录中的必需文件名实际是目录，例如 `openapi.json/`，`scripts/validate_release_artifacts.py` 会在 `Path.read_text()` 处抛出 `IsADirectoryError`，而不是返回结构化的 validation report。

## 原因

`read_json()` 只捕获 `json.JSONDecodeError`，没有捕获读取文件阶段的 `OSError`。因此路径存在但不可作为文本文件读取时，异常会直接冒泡，发布校验 CLI 不能稳定输出 `{ok:false, issues:[...]}`。

## 修复

`read_json()` 捕获 `OSError` 并记录 `<label> unreadable: ...` issue，再返回空对象继续聚合其他校验结果。同步更新 README 和 release checklist，明确 handoff validator 会检查 artifact 是否可读取。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_reports_unreadable_required_artifact -q` 失败，抛出 `IsADirectoryError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_reports_unreadable_required_artifact -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_script_accepts_handoff_bundle tests/test_release_contracts.py::test_validate_release_artifacts_script_rejects_tampered_artifact -q` 通过，`2 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`746 passed`。
