# Export release artifacts crashed when partial cleanup failed

## 现象

- 触发命令、接口或页面：运行 `scripts/export_release_artifacts.py --output-dir <dir>`，本轮导出已写出 `openapi.json`，随后写 `demo-summary.json` 或 `release-manifest.json` 失败，并且清理半成品 artifact 时也遇到文件系统错误。
- 实际结果：半成品清理阶段的 `Path.unlink()` 抛出 `OSError`，覆盖原本的结构化失败报告，CLI 可能重新出现 traceback。
- 期望结果：半成品清理失败也应返回结构化 `ok:false` report，并明确报告 `release artifact cleanup failed: ...`，让发布 gate 和人工交接能读到稳定失败原因。

## 原因

- 根因：新增半成品清理逻辑后，`remove_artifacts()` 直接调用 `unlink()`，没有把清理阶段的 `OSError` 转成结构化 issue。
- 影响范围：release artifact 导出、demo summary 或 manifest 写失败后的发布诊断、复用交接目录时的失败稳定性。

## 修复

- 修改文件：`scripts/export_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：`remove_artifacts()` 捕获 `OSError` 并返回 `release artifact cleanup failed: ...`；JSON 写失败路径在清理失败时优先报告 cleanup issue，否则继续报告原始写入失败 issue。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_partial_artifact_cleanup_failure -q` 失败，当前实现抛出 `OSError("permission denied")`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_partial_artifact_cleanup_failure tests/test_release_contracts.py::test_export_release_artifacts_reports_demo_summary_write_failure tests/test_release_contracts.py::test_export_release_artifacts_reports_manifest_write_failure tests/test_release_contracts.py::test_export_release_artifacts_reports_stale_artifact_cleanup_failure tests/test_release_contracts.py::test_export_release_artifacts_script_writes_handoff_bundle -q` 通过，`5 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`867 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `867 passed`。
