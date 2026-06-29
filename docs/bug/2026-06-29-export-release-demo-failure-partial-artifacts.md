# Export release artifacts left partial files after demo preparation failure

## 现象

- 触发命令、接口或页面：运行 `python scripts/export_release_artifacts.py --output-dir out/release --compact`，且 `prepare_demo_data()` 在 demo 数据准备阶段失败。
- 实际结果：导出流程返回 `ok:false`，但已经写出的 `openapi.json` 和新增的 `release-acceptance-matrix.md` 会留在 artifact 目录中；复用目录时还可能把旧的 handoff 文件和新半成品混在一起。
- 期望结果：demo 准备失败时清理本轮所有 release artifacts，包括 `openapi.json`、`demo-summary.json`、`release-acceptance-matrix.md` 和 `release-manifest.json`，避免交付或打包误用半成品。

## 原因

- 根因：`export_release_artifacts()` 在写完 OpenAPI 和验收矩阵后才调用 `prepare_demo_data()`；该异常分支直接返回失败 report，没有复用已有 `remove_artifacts()` 清理逻辑。
- 影响范围：release handoff artifact 导出、单命令 handoff、复用 `out/release` 目录的发布流程。

## 修复

- 修改文件：`scripts/export_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：demo 准备失败分支现在会清理四个 handoff artifacts；如果清理本身失败，返回 `release artifact cleanup failed: ...` 结构化 issue。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_prepare_demo_failure tests/test_release_contracts.py::test_export_release_artifacts_removes_stale_outputs_on_prepare_demo_failure -q` 失败，`openapi.json` 仍存在。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_prepare_demo_failure tests/test_release_contracts.py::test_export_release_artifacts_removes_stale_outputs_on_prepare_demo_failure -q` 通过，`2 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1252 passed`。
