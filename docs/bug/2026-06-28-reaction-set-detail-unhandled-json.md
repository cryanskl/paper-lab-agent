# Reaction set detail exposed malformed reaction JSON as an unhandled error

## 现象

- 触发命令、接口或页面：`GET /api/v1/reaction-sets/{id}`，且该 reaction set 已存在，但库内 `reactants` JSON 损坏。
- 实际结果：`reaction_set_detail()` 抛出的 `JSONDecodeError` 未在路由层转换为语义化 API 错误；测试态直接抛异常，运行态只能进入全局 `internal_server_error`。
- 期望结果：详情接口应返回结构化 `500 reaction_set_detail_failed`，并保留底层 JSON 解析错误，便于发布前排障。

## 原因

- 根因：`app/routers/reactions.py` 的 `GET /reaction-sets/{id}` 在确认 reaction set 存在后直接返回 `reaction_set_detail()`，没有捕获详情序列化阶段的后端数据解析异常。
- 影响范围：化学库详情接口、Streamlit 详情/复核页面和发布前数据损坏排障；损坏反应数据会以未处理异常或泛化 500 暴露。

## 修复

- 修改文件：`app/routers/reactions.py`、`tests/test_api.py`。
- 关键行为：详情路由保留 missing reaction set 的 `404 reaction_set_not_found`；已存在反应集的详情解析失败转换为 `500 reaction_set_detail_failed`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_reaction_set_detail_malformed_reaction_json_returns_backend_error -q` 失败，`JSONDecodeError` 从路由中未处理抛出。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_reaction_set_detail_malformed_reaction_json_returns_backend_error tests/test_api.py::test_reaction_verify_malformed_reaction_json_returns_backend_error tests/test_api.py::test_reaction_export_malformed_reaction_json_returns_backend_error tests/test_api.py::test_reaction_set_detail_reports_review_progress_counts -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1130 passed`。
