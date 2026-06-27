# Export release artifacts followed output directory ancestor symlinks

## 现象

- 触发命令、接口或页面：`scripts/export_release_artifacts.py --output-dir` 指向祖先目录为 symlink 的输出目录，例如 `linked-root/nested/release`。
- 实际结果：导出流程跟随 `linked-root` 到外部目录，写入 `openapi.json`、`demo-summary.json` 和 `release-manifest.json`，并返回 manifest。
- 期望结果：返回结构化 `ok:false` report，并报告 `release artifact output directory parent is not a regular directory`，避免把 release handoff artifacts 写到指定路径树之外。

## 原因

- 根因：`export_release_artifacts()` 只在 `output_dir.resolve()` 前检查输出目录本身和直接父目录是否为 symlink，没有检查更高层祖先目录；随后 `resolve()` 会跟随任意祖先 symlink。
- 影响范围：release artifact 导出、handoff 文件落盘路径、发布交接目录边界审计。

## 修复

- 修改文件：`scripts/export_release_artifacts.py`、`tests/test_release_contracts.py`
- 关键行为：在解析输出目录前复用 `first_symlink_parent()` 扫描原始路径父级链。发现任一非系统根级父目录 symlink 时直接返回 `ok:false`，并且不写入 handoff 文件。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_rejects_output_dir_symlink_ancestor -q` 失败，当前实现返回 manifest 且缺少 `ok` 字段。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_rejects_output_dir_symlink_ancestor tests/test_release_contracts.py::test_export_release_artifacts_rejects_output_dir_symlink_parent tests/test_release_contracts.py::test_export_release_artifacts_rejects_output_dir_symlink tests/test_release_contracts.py::test_export_release_artifacts_script_writes_handoff_bundle tests/test_release_contracts.py::test_validate_release_artifacts_script_accepts_handoff_bundle -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `771 passed`。
