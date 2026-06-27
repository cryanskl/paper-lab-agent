# Export release artifacts left stale handoff files after failure

## 现象

- 触发命令、接口或页面：`scripts/export_release_artifacts.py --output-dir out/release --compact` 复用已有 release artifact 目录，且新一轮导出在 demo 数据准备阶段失败。
- 实际结果：脚本返回 `ok:false`，但上一轮成功生成的 `demo-summary.json` 和 `release-manifest.json` 仍留在输出目录中。
- 期望结果：失败导出不应留下上一轮成功的 handoff 文件，避免调用方误拿 stale demo summary 或 stale manifest 继续交接、打包或人工发布。

## 原因

- 根因：`scripts/export_release_artifacts.py` 允许复用只包含 expected artifact 的输出目录，但生成新一轮 artifact 前没有清理旧文件；失败分支也没有删除依赖本轮成功生成才可信的下游文件。
- 影响范围：release artifact 导出、release package 打包前置流程、发布交接目录的可信度。

## 修复

- 修改文件：`scripts/export_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：输出目录安全检查通过后，生成新一轮 artifact 前先删除旧的 `openapi.json`、`demo-summary.json` 和 `release-manifest.json`；任一后续失败都不会和上一轮成功文件混在同一目录。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_removes_stale_outputs_on_prepare_demo_failure -q` 失败，旧 `demo-summary.json` 仍存在。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_removes_stale_outputs_on_prepare_demo_failure tests/test_release_contracts.py::test_export_release_artifacts_reports_prepare_demo_failure tests/test_release_contracts.py::test_export_release_artifacts_reports_demo_summary_write_failure tests/test_release_contracts.py::test_export_release_artifacts_script_writes_handoff_bundle tests/test_release_contracts.py::test_export_release_artifacts_rejects_dirty_output_dir -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `794 passed`。
