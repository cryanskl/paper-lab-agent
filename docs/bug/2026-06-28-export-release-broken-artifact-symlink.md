# Export release artifacts ignored broken artifact symlinks

## 现象

- 触发命令、接口或页面：运行 `scripts/export_release_artifacts.py --output-dir <dir>`，且输出目录中已存在允许的 handoff 文件名，但该路径是断开的 symlink，例如 `openapi.json -> missing-openapi.json`。
- 实际结果：导出流程会跳过 symlink 拒绝逻辑，随后清理该路径并继续生成新的 handoff artifacts。
- 期望结果：输出目录中的 handoff artifact 路径只要是 symlink，无论目标是否存在，都应返回 `ok:false` 并报告 `release artifact output path is not a regular file`。

## 原因

`export_release_artifacts()` 检查 expected artifact 路径时先判断 `path.exists()` 再判断 `path.is_symlink()`。broken symlink 的 `exists()` 为假，因此不会进入已有 symlink 拒绝分支，后续 `unlink(missing_ok=True)` 会删除 symlink 并继续导出。

## 修复

- 修改文件：`scripts/export_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：expected artifact 路径检查先拒绝 `path.is_symlink()`，再处理普通非文件路径。
- 影响范围：只改变断开的 stale artifact symlink 行为；普通 artifact symlink、普通目录、真正缺失 artifact 和正常导出行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_rejects_broken_expected_artifact_symlink -q` 失败，当前实现继续导出成功并返回 manifest。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_rejects_broken_expected_artifact_symlink tests/test_release_contracts.py::test_export_release_artifacts_rejects_expected_artifact_symlink tests/test_release_contracts.py::test_export_release_artifacts_reports_expected_artifact_path_not_file tests/test_release_contracts.py::test_export_release_artifacts_script_writes_handoff_bundle -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1126 passed`。
