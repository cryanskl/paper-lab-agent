# Export release artifacts crashed on demo preparation failure

## 现象

- 触发命令、接口或页面：`scripts/export_release_artifacts.py --output-dir out/release --compact` 在准备 demo 数据阶段遇到运行时异常。
- 实际结果：`prepare_demo_data()` 抛出的异常会直接穿透 `export_release_artifacts()`，CLI 非结构化崩溃，调用方拿不到 `{ok:false, issues:[...]}` 报告。
- 期望结果：release artifact 导出失败时仍返回结构化报告，明确指出 demo 数据准备失败原因，便于发布 gate 和交接脚本诊断。

## 原因

- 根因：`scripts/export_release_artifacts.py` 只结构化处理 OpenAPI、demo summary 和 manifest 写入失败，没有在 `prepare_demo_data()` 调用边界捕获普通异常。
- 影响范围：发布 artifact 导出、release package 打包前置流程、发布或演示前的失败诊断。

## 修复

- 修改文件：`scripts/export_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：在 demo 数据准备边界捕获异常并返回 `ok:false` report，`issues` 包含 `Demo data preparation failed: ...`；已写出的 `openapi.json` 保留作为诊断产物，`demo-summary.json` 和 `release-manifest.json` 不生成。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_prepare_demo_failure -q` 失败，当前实现直接抛出 `RuntimeError("fixture setup failed")`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_prepare_demo_failure tests/test_release_contracts.py::test_export_release_artifacts_reports_demo_summary_write_failure tests/test_release_contracts.py::test_export_release_artifacts_script_writes_handoff_bundle -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `793 passed`。
