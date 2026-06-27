# Validate release package followed package ancestor symlinks

## 现象

- 触发命令、接口或页面：`scripts/validate_release_package.py --package` 指向祖先目录为 symlink 的 zip 路径，例如 `linked-root/nested/paper-lab-agent-release.zip`。
- 实际结果：validator 跟随 `linked-root` 到外部目录，读取目标 zip，并返回 `ok:true`。
- 期望结果：返回结构化 `ok:false` report，并报告 `release package parent is not a regular directory`，避免把 symlink 祖先目录下的目标 zip 当成用户指定的 handoff package。

## 原因

- 根因：`validate_release_package()` 只在 `resolve()` 前检查 package 路径本身和直接父目录是否为 symlink，没有检查更高层祖先目录；随后 `resolve()` 会跟随任意祖先 symlink。
- 影响范围：release package 校验、handoff package 来源边界、`--require-clean-source` 等后续校验的路径可信度。

## 修复

- 修改文件：`scripts/validate_release_package.py`、`tests/test_release_contracts.py`
- 关键行为：在解析 package 路径前复用 `first_symlink_parent()` 扫描原始路径父级链。发现任一非系统根级父目录 symlink 时直接返回 `ok:false`，并在 issue 中指出命中的 symlink 父级。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_package_ancestor_symlink -q` 失败，当前实现返回 `ok:true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_package_ancestor_symlink tests/test_release_contracts.py::test_validate_release_package_rejects_package_parent_symlink tests/test_release_contracts.py::test_validate_release_package_rejects_package_symlink tests/test_release_contracts.py::test_validate_release_package_script_rejects_tampered_zip_artifact tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `772 passed`。
