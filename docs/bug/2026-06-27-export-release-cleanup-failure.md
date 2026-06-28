# Export release artifacts crashed on stale artifact cleanup failure

## 现象

- 触发命令、接口或页面：`scripts/export_release_artifacts.py --output-dir out/release --compact` 复用已有 release artifact 目录，并在生成新一轮 artifact 前清理旧文件。
- 实际结果：如果旧 `openapi.json`、`demo-summary.json` 或 `release-manifest.json` 删除失败，`Path.unlink()` 抛出的 `OSError` 会直接穿透，CLI 非结构化崩溃。
- 期望结果：清理旧 artifact 失败时返回结构化 `ok:false` report，明确指出 cleanup 失败原因，避免发布脚本在文件系统边界直接崩溃。

## 原因

- 根因：`scripts/export_release_artifacts.py` 在导出前清理旧 expected artifacts 时，没有捕获 `unlink()` 的 `OSError`。
- 影响范围：release artifact 导出、复用输出目录时的发布交接稳定性、发布 gate 的失败诊断。

## 修复

- 修改文件：`scripts/export_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：旧 artifact 清理失败时返回 `ok:false`，`issues` 包含 `release artifact cleanup failed: ...`；成功清理后继续保持原有 OpenAPI、demo summary 和 manifest 生成流程。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_stale_artifact_cleanup_failure -q` 失败，当前实现直接抛出 `OSError("permission denied")`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_stale_artifact_cleanup_failure tests/test_release_contracts.py::test_export_release_artifacts_removes_stale_outputs_on_prepare_demo_failure tests/test_release_contracts.py::test_export_release_artifacts_reports_prepare_demo_failure tests/test_release_contracts.py::test_export_release_artifacts_script_writes_handoff_bundle -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `796 passed`。
