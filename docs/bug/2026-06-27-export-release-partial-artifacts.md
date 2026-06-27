# Export release artifacts left partial files after JSON write failure

## 现象

- 触发命令、接口或页面：运行 `scripts/export_release_artifacts.py --output-dir <dir>`，且本轮导出在写 `demo-summary.json` 或 `release-manifest.json` 时遇到文件系统错误。
- 实际结果：脚本返回结构化 `ok:false`，但输出目录中仍保留本轮已经写出的 `openapi.json`，manifest 写失败时还会留下 `demo-summary.json`。
- 期望结果：release handoff 导出失败时不留下任何本轮半成品 artifact，避免人工或后续脚本误拿不完整交接目录继续发布。

## 原因

- 根因：`export_release_artifacts()` 只在新一轮开始前清理旧 artifact；后续 JSON 写失败后直接返回错误，没有清理本轮已写出的前序文件。
- 影响范围：release artifact 导出、release package 打包前置目录、人工交接目录检查。

## 修复

- 修改文件：`scripts/export_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：新增本轮 artifact 清理 helper；`demo-summary.json` 或 `release-manifest.json` 写失败时删除 `openapi.json`、`demo-summary.json` 和 `release-manifest.json`，同时保留原有结构化错误信息。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_demo_summary_write_failure tests/test_release_contracts.py::test_export_release_artifacts_reports_manifest_write_failure -q` 失败，失败导出仍留下 `openapi.json`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_demo_summary_write_failure tests/test_release_contracts.py::test_export_release_artifacts_reports_manifest_write_failure -q` 通过，`2 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`866 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `866 passed`。
