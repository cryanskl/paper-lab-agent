# System status accepted symlinked vector stores

## 现象

- 触发命令、接口或页面：`GET /api/v1/system/status` 检查本地 JSON vector store 健康状态，且 `VECTOR_DB_PATH` 指向 symlink 文件。
- 实际结果：系统状态接口会跟随 symlink 读取目标 JSON；如果目标是合法 JSON，则报告 `valid_json=true`，release readiness 不产生 storage error。
- 期望结果：系统状态应与 RAG 索引写入规则一致，拒绝 symlinked vector store，把它报告为无效存储健康状态。

## 原因

- 根因：`app/routers/system.py` 的 `vector_store_health()` 直接 `path.read_text()`，没有复用 RAG 服务层的 vector store 路径安全校验。
- 影响范围：系统健康检查、release readiness、RAG 本地索引配置诊断可信度。

## 修复

- 修改文件：`app/routers/system.py`、`tests/test_api.py`。
- 关键行为：读取 vector store JSON 前调用 `assert_safe_vector_store_path()`；如果路径是 symlink 或父目录链不安全，`valid_json=false`，`error` 记录对应路径错误，并进入 `release_readiness.storage_errors`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_status_reports_symlinked_vector_store_health_error -q` 失败，当前实现返回 `valid_json=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_status_reports_symlinked_vector_store_health_error tests/test_api.py::test_system_status_reports_corrupt_vector_store_health tests/test_api.py::test_system_status_reports_vector_db_backend -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `804 passed`。
