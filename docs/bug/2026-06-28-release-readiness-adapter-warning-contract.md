# Release readiness adapter warning contract was unclear

## 现象

- 触发命令、接口或页面：阅读 `docs/接口设计文档.md` 的 `/system/status.release_readiness` 说明。
- 实际结果：文档只说明 `config_warning_codes` 中的可选外部能力缺失不阻断默认离线发布，没有说明 `unsupported_embedding_model` 和 `unsupported_vector_db_backend` 会阻断发布就绪。
- 期望结果：接口契约应明确区分非阻断的离线外部能力 warning，以及会导致 `release_readiness.ready=false` 的本地 RAG adapter unsupported warning。

## 原因

- 根因：系统状态代码已把 unsupported 本地 RAG adapter 纳入发布门禁，但接口文档仍停留在“config_warning_codes 不阻断默认离线发布”的旧语义。
- 影响范围：发布前排障、API 使用方对 `/system/status` 的判断，以及后续维护者对配置 warning 的阻断规则理解。

## 修复

- 修改文件：`docs/接口设计文档.md`、`tests/test_release_contracts.py`。
- 关键行为：接口文档明确 `OPENALEX_MAILTO`、`UNPAYWALL_EMAIL`、`LLM_API_KEY` 缺失不阻断默认离线发布；`unsupported_embedding_model` 和 `unsupported_vector_db_backend` 会导致 `release_readiness.ready=false`。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_api_contract_documents_release_readiness_blocking_adapter_warnings -q`，确认接口文档缺少 unsupported adapter 阻断语义。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_api_contract_documents_release_readiness_blocking_adapter_warnings tests/test_api.py::test_release_readiness_blocks_unsupported_local_adapter_warnings tests/test_api.py::test_health_check_summary_surfaces_blocking_config_warnings -q`，3 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1035 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1035 passed`。
