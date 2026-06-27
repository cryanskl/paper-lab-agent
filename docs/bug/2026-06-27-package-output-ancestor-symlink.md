# Package release artifacts followed output ancestor symlinks

## 现象

- 触发命令、接口或页面：`scripts/package_release_artifacts.py --output` 指向祖先目录为 symlink 的 zip 输出路径，例如 `linked-root/nested/paper-lab-agent-release.zip`。
- 实际结果：打包流程跟随 `linked-root` 到外部目录，创建 `nested/` 并写入 release zip，返回 `ok:true`。
- 期望结果：返回结构化 `ok:false` report，并报告 `release package output parent is not a regular directory`，避免把 release package 写到指定路径树之外。

## 原因

- 根因：`package_release_artifacts()` 只在 `output_path.resolve()` 前检查输出文件本身和直接父目录是否为 symlink，没有检查更高层祖先目录；随后 `resolve()` 会跟随任意祖先 symlink。
- 影响范围：release package 生成、handoff zip 落盘路径、发布交接输出边界审计。

## 修复

- 修改文件：`scripts/package_release_artifacts.py`、`tests/test_release_contracts.py`
- 关键行为：在解析 output 路径前复用 `first_symlink_parent()` 扫描原始路径父级链。发现任一非系统根级父目录 symlink 时直接返回 `ok:false`，并且不写入 release zip。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_ancestor_symlink -q` 失败，当前实现返回 `ok:true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_ancestor_symlink tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_parent_symlink tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_symlink tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle tests/test_release_contracts.py::test_validate_release_package_script_rejects_tampered_zip_artifact -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `773 passed`。
