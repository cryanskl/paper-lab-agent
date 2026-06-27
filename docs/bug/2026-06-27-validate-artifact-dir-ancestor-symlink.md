# Validate release artifacts followed artifact directory ancestor symlinks

## 现象

- 触发命令、接口或页面：`scripts/validate_release_artifacts.py --artifact-dir` 指向祖先目录为 symlink 的 artifact 目录，例如 `linked-root/nested/release`。
- 实际结果：validator 跟随 `linked-root` 到外部目录，读取目标 artifact bundle，并返回 `ok:true`。
- 期望结果：返回结构化 `ok:false` report，并报告 `release artifact directory parent is not a regular directory`，避免把 symlink 祖先目录下的目标目录当成用户指定的 release handoff 目录。

## 原因

- 根因：`validate_release_artifacts()` 只在 `resolve()` 前检查 artifact 目录本身和直接父目录是否为 symlink，没有检查更高层祖先目录；随后 `resolve()` 会跟随任意祖先 symlink。
- 影响范围：release artifact 校验、发布交接目录边界审计、后续 package validation 对 artifact bundle 来源的可信度。

## 修复

- 修改文件：`scripts/validate_release_artifacts.py`、`tests/test_release_contracts.py`
- 关键行为：在解析 artifact 目录前扫描原始路径的父级链。任一父级是 symlink 时直接返回 `ok:false` report，并在 issue 中指出命中的 symlink 父级。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink_ancestor -q` 失败，当前实现返回 `ok:true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle tests/test_release_contracts.py::test_validate_release_package_script_rejects_tampered_zip_artifact tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink_ancestor tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink_parent tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink tests/test_release_contracts.py::test_validate_release_artifacts_script_accepts_handoff_bundle -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `769 passed`。
