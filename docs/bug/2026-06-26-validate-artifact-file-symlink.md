# Validate release artifacts accepted required artifact symlinks

## 现象

如果 release handoff 目录里的 required artifact 是 symlink，例如 `openapi.json -> ../outside-openapi.json`，`scripts/validate_release_artifacts.py` 会跟随 symlink 读取目录外文件，并把它当成有效 handoff artifact。

## 原因

`read_json()` 只检查路径是否存在，然后直接 `read_text()`；`Path.read_text()` 会跟随 symlink。checksum 校验也使用 `Path.is_file()`，它同样会跟随指向普通文件的 symlink。

## 修复

`read_json()` 在读取前先拒绝 `Path.is_symlink()`，返回结构化 issue。checksum 校验的非普通文件判断也显式包含 symlink，避免后续路径继续按普通文件处理。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_required_artifact_symlink -q` 失败，当前实现返回 `ok:true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_required_artifact_symlink tests/test_release_contracts.py::test_validate_release_artifacts_reports_unreadable_required_artifact tests/test_release_contracts.py::test_validate_release_artifacts_reports_checksum_artifact_not_file tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink tests/test_release_contracts.py::test_validate_release_artifacts_script_accepts_handoff_bundle -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `763 passed`。
