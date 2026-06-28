# Release artifact validator 遇到非 UTF-8 文件会崩溃

## 现象

如果 release artifact 中的必需 JSON 文件存在但内容不是 UTF-8 文本，例如 `openapi.json` 是二进制内容，`scripts/validate_release_artifacts.py` 会抛出 `UnicodeDecodeError`，而不是返回结构化的 validation report。

## 原因

`read_json()` 已经捕获了文件读取阶段的 `OSError` 和 JSON 解析阶段的 `json.JSONDecodeError`，但没有捕获 UTF-8 解码阶段的 `UnicodeDecodeError`。发布校验 CLI 因此在坏 artifact 上直接崩溃。

## 修复

`read_json()` 将 `UnicodeDecodeError` 与 `OSError` 一起归类为 `<label> unreadable: ...` issue，继续返回 `{ok:false, issues:[...]}` 形式的校验结果。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_reports_non_utf8_required_artifact -q` 失败，抛出 `UnicodeDecodeError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_reports_non_utf8_required_artifact tests/test_release_contracts.py::test_validate_release_artifacts_reports_unreadable_required_artifact -q` 通过，`2 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_script_accepts_handoff_bundle tests/test_release_contracts.py::test_validate_release_artifacts_script_rejects_tampered_artifact -q` 通过，`2 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`747 passed`。
