# Validate release artifacts followed artifact directory parent symlinks

## 现象

如果 `scripts/validate_release_artifacts.py --artifact-dir` 的直接父目录是 symlink，例如 `linked-parent/release` 且 `linked-parent -> ../outside-release-parent`，validator 会跟随父目录 symlink，验证指定路径树之外的 handoff artifacts。

## 原因

`validate_release_artifacts()` 只拒绝 artifact 目录本身是 symlink 的情况，然后调用 `artifact_dir.resolve()`。当直接父目录是 symlink 时，`resolve()` 会把 artifact 目录解析到 symlink 目标目录。

## 修复

在解析 artifact 目录前检查原始 `artifact_dir.parent`，如果直接父目录是 symlink，则返回结构化 `ok:false` report，并报告 `release artifact directory parent is not a regular directory`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink_parent -q` 失败，当前实现返回 `ok:true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink_parent tests/test_release_contracts.py::test_validate_release_artifacts_rejects_required_artifact_symlink tests/test_release_contracts.py::test_validate_release_artifacts_reports_artifact_dir_not_directory tests/test_release_contracts.py::test_validate_release_artifacts_script_accepts_handoff_bundle -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `767 passed`。
