# Validate release artifacts followed artifact directory symlinks

## 现象

如果 `scripts/validate_release_artifacts.py --artifact-dir` 指向一个目录 symlink，例如 `release -> ../outside-release`，validator 会跟随 symlink 验证目标目录，并把目录外的 handoff artifacts 当成有效交付物。

## 原因

`validate_release_artifacts()` 在检查输入路径类型前先调用 `artifact_dir.resolve()`。目录 symlink 会被解析成目标目录，后续文件枚举、JSON 读取和 checksum 校验都作用在 symlink 目标上。

## 修复

在解析 artifact 目录前先检查原始 `artifact_dir.is_symlink()`。命中时返回结构化 `ok:false` report，并报告 `release artifact directory is not a regular directory`，避免把 symlink 目标误认为用户指定的 release handoff 目录。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink -q` 失败，当前实现返回 `ok:true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_script_accepts_handoff_bundle tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink tests/test_release_contracts.py::test_validate_release_artifacts_reports_artifact_dir_not_directory tests/test_release_contracts.py::test_validate_release_artifacts_rejects_unexpected_handoff_files tests/test_release_contracts.py::test_validate_release_artifacts_reports_unreadable_required_artifact -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `762 passed`。
