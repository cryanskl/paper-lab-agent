# Package release artifacts followed artifact directory ancestor symlinks

## 现象

- 触发命令、接口或页面：`scripts/package_release_artifacts.py --artifact-dir` 指向祖先目录为 symlink 的 artifact 目录，例如 `linked-root/nested/release`。
- 实际结果：打包流程跟随 `linked-root` 到外部目录，验证并打包目标 artifact bundle，返回 `ok:true`。
- 期望结果：返回结构化 `ok:false` report，并报告 `release artifact directory parent is not a regular directory`，避免把 symlink 祖先目录下的 handoff artifacts 打进 release zip。

## 原因

- 根因：`package_release_artifacts()` 只在 `artifact_dir.resolve()` 前检查 artifact 目录本身是否为 symlink，没有检查更高层父级；随后把已解析的真实目录传给 `validate_release_artifacts()`，绕过了 validator 对原始路径父级 symlink 的拒绝逻辑。
- 影响范围：release package 生成、handoff artifact 来源边界、发布包内容可信度。

## 修复

- 修改文件：`scripts/package_release_artifacts.py`、`tests/test_release_contracts.py`
- 关键行为：在解析 artifact 目录前复用 `first_symlink_parent()` 扫描原始路径父级链。发现任一非系统根级父目录 symlink 时直接返回 `ok:false`，并且不创建输出 zip。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_rejects_artifact_dir_symlink_ancestor -q` 失败，当前实现返回 `ok:true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_rejects_artifact_dir_symlink_ancestor tests/test_release_contracts.py::test_package_release_artifacts_rejects_artifact_dir_symlink tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink_ancestor tests/test_release_contracts.py::test_validate_release_package_script_rejects_tampered_zip_artifact -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `770 passed`。
