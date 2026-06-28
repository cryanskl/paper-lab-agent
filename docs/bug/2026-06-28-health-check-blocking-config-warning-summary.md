# Health check hid blocking config warning details

## 现象

- 触发命令、接口或页面：`/api/v1/system/status` 返回 `release_readiness.ready=false`，且 `config_warning_codes` 包含 `unsupported_vector_db_backend` 或 `unsupported_embedding_model`。
- 实际结果：`scripts/health_check.py` 的 compact summary 和 `--require-release-ready` 只暴露泛化的 `ready=false` blocker。
- 期望结果：缺少外部 key 的离线 warning 仍不作为 release blocker；但 unsupported 本地 RAG adapter 应在 release blockers 中显示具体 `config_warning_codes:<code>`，便于发布排障。

## 原因

- 根因：`scripts/health_check.py` 的 `release_readiness_blockers()` 完全忽略 `config_warning_codes`，没有复用系统状态中阻断性本地 adapter warning 的语义。
- 影响范围：发布前 compact summary、`--require-release-ready` 错误信息，以及非默认 RAG adapter 配置下的故障定位。

## 修复

- 修改文件：`scripts/health_check.py`、`tests/test_api.py`。
- 关键行为：仅将 `unsupported_embedding_model` 和 `unsupported_vector_db_backend` 转换为 release blockers；`missing_llm_api_key` 等离线模式 warning 仍只保留在 `config_warning_codes` 和 `config_ready=false` 中。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_summary_surfaces_blocking_config_warnings -q`，确认 summary 只返回泛化 `ready=false`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_summary_surfaces_blocking_config_warnings tests/test_api.py::test_health_check_require_release_ready_runs_combined_gates tests/test_api.py::test_health_check_summary_prefers_api_release_readiness tests/test_api.py::test_health_check_summary_rejects_inconsistent_api_release_readiness tests/test_api.py::test_release_readiness_allows_offline_config_warnings tests/test_api.py::test_release_readiness_blocks_unsupported_local_adapter_warnings -q`，6 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1034 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1034 passed`。
