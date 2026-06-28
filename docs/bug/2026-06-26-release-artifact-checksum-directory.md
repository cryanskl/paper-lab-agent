# Release artifact checksum 遇到目录会崩溃

## 现象

如果 release artifact 目录中的必需文件名实际是目录，例如 `openapi.json/`，并且 `release-manifest.json` 里包含 checksums，`scripts/validate_release_artifacts.py` 会在 checksum 比对阶段抛出 `IsADirectoryError`。

## 原因

`read_json()` 已能把目录路径报告为 unreadable，但后续 checksum 比对仍然只判断 `artifact_path.exists()`，然后调用 `sha256_file(artifact_path)`。目录存在但不是普通文件时，`Path.read_bytes()` 会抛异常。

## 修复

在 checksum 比对前增加普通文件校验：路径存在但不是文件时记录 `checksum unavailable: ... is not a file: ...`，并跳过 sha256 计算。普通文件仍继续执行 checksum mismatch 校验。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_reports_checksum_artifact_not_file -q` 失败，抛出 `IsADirectoryError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_reports_checksum_artifact_not_file -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_reports_unreadable_required_artifact tests/test_release_contracts.py::test_validate_release_artifacts_reports_checksum_artifact_not_file tests/test_release_contracts.py::test_validate_release_artifacts_reports_non_utf8_required_artifact tests/test_release_contracts.py::test_validate_release_artifacts_script_rejects_tampered_artifact tests/test_release_contracts.py::test_validate_release_artifacts_script_accepts_handoff_bundle -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `752 passed`。
