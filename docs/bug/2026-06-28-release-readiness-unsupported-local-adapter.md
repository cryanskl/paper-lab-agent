# Release readiness allowed unsupported local adapters

## 现象

- 触发命令、接口或页面：设置 `EMBEDDING_MODEL=text-embedding-3-small` 或 `VECTOR_DB_BACKEND=faiss` 等当前本地 registry 不支持的 RAG adapter 后查看 `/api/v1/system/status`。
- 实际结果：`config_warning_codes` 会报告 unsupported 配置，但在 demo data、工作流和存储都正常时，`release_readiness.ready` 仍可能为 `true`。
- 期望结果：缺少 OpenAlex、Unpaywall、LLM key 这类离线模式 warning 不阻断发布；但 unsupported 本地 embedding/vector backend 会让 RAG 索引或查询直接失败，必须阻断 release readiness。

## 原因

- 根因：`app/routers/system.py` 的 `release_readiness_status()` 完全忽略 `config_warning_codes`，没有区分非阻断的外部能力缺失与阻断性的本地 adapter 不支持。
- 影响范围：系统状态发布门禁、health/release summary 的发布就绪判断，以及非默认 RAG adapter 配置下的发布前排障。

## 修复

- 修改文件：`app/routers/system.py`、`tests/test_api.py`。
- 关键行为：新增阻断 warning code 集合，仅将 `unsupported_embedding_model` 和 `unsupported_vector_db_backend` 纳入 `ready=false` 判定；缺少外部 key 的离线 warning 仍保留为非阻断。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_release_readiness_blocks_unsupported_local_adapter_warnings -q`，确认 unsupported 本地 adapter warning 仍返回 `ready=true`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_release_readiness_blocks_unsupported_local_adapter_warnings tests/test_api.py::test_release_readiness_allows_offline_config_warnings tests/test_api.py::test_system_status_reports_normalized_effective_vector_config tests/test_embeddings.py::test_config_warnings_report_unsupported_embedding_model tests/test_embeddings.py::test_config_warnings_report_unsupported_vector_db_backend -q`，5 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1033 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1033 passed`。
