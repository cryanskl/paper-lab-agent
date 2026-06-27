# Streamlit hidden blocking release config warnings

## 现象

- 触发命令、接口或页面：打开 Streamlit 侧边栏查看 `发布就绪`，同时 `/api/v1/system/status.release_readiness` 返回 `ready=false` 且 `config_warning_codes` 包含 `unsupported_vector_db_backend` 或 `unsupported_embedding_model`。
- 实际结果：侧边栏只把 demo data、workflow、storage 三类问题显示成 release blockers；当唯一阻断原因来自本地 RAG adapter 配置警告时，页面只能显示 `release blockers: unknown`。
- 期望结果：阻断发布的配置警告应以 `config_warning_codes:<code>` 出现在 release blockers 中；`missing_llm_api_key` 这类离线可选能力 warning 仍不能阻断默认发布。

## 原因

- 根因：Streamlit 侧边栏为避免离线可选配置 warning 阻断发布，直接把所有 `config_warning_codes` 排除在 release blocker 渲染之外。
- 影响范围：发布前排障、Streamlit 运维视图、unsupported RAG adapter 配置的可见性。

## 修复

- 修改文件：`streamlit_app.py`、`tests/test_api.py`。
- 关键行为：侧边栏新增阻断型配置警告 allowlist，只把 `unsupported_embedding_model` 和 `unsupported_vector_db_backend` 渲染为 `config_warning_codes:<code>` release blockers；普通配置 warning 继续作为非阻断配置提示展示。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_surfaces_blocking_release_config_warnings -q` 失败，缺少 `RELEASE_BLOCKING_CONFIG_WARNING_CODES` 和阻断型配置 warning 渲染逻辑。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_surfaces_blocking_release_config_warnings tests/test_api.py::test_streamlit_sidebar_surfaces_release_readiness tests/test_api.py::test_health_check_summary_surfaces_blocking_config_warnings tests/test_api.py::test_release_readiness_blocks_unsupported_local_adapter_warnings tests/test_api.py::test_release_readiness_allows_offline_config_warnings -q` 通过，`5 passed`。
- 完整 gate：`.venv/bin/python -m pytest` 通过，`1036 passed`；`bash scripts/release_check.sh` 通过，包含全量 pytest `1036 passed`。
