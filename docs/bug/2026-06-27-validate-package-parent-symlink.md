# Validate release package followed package parent symlinks

## 现象

- 触发命令、接口或页面：`scripts/validate_release_package.py --package` 指向父目录为 symlink 的 zip 路径，例如 `linked-parent/paper-lab-agent-release.zip`。
- 实际结果：validator 跟随 `linked-parent` 到外部目录，读取目标 zip，并返回 `ok:true`。
- 期望结果：返回结构化 `ok:false` report，并报告 `release package parent is not a regular directory`，避免把 symlink 父目录下的目标 zip 当成用户指定的 handoff package。

## 原因

- 根因：`validate_release_package()` 只在 `resolve()` 前检查 package 路径本身是否为 symlink，没有检查原始 `package_path.parent` 是否为 symlink；随后 `resolve()` 会跟随父目录 symlink。
- 影响范围：发布交接包校验、release package 边界审计、`--require-clean-source` 等后续校验的路径可信度。

## 修复

- 修改文件：`scripts/validate_release_package.py`、`tests/test_release_contracts.py`
- 关键行为：在解析 package 路径前检查原始父目录。父目录是 symlink 时直接返回 `ok:false` report，并保留未解析的请求父目录在 issue 中。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_package_parent_symlink -q` 失败，当前实现返回 `ok:true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_package_parent_symlink tests/test_release_contracts.py::test_validate_release_package_rejects_package_symlink tests/test_release_contracts.py::test_validate_release_package_reports_package_path_not_file tests/test_release_contracts.py::test_validate_release_package_script_rejects_tampered_zip_artifact tests/test_release_contracts.py::test_validate_release_package_rejects_windows_traversal_artifact_name tests/test_release_contracts.py::test_validate_release_package_rejects_windows_rooted_artifact_name -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `768 passed`。
