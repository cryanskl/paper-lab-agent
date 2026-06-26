# OpenAPI tag metadata was dropped

## 现象

- 触发命令、接口或页面：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_api_contract_openapi_tags_have_metadata_descriptions -q`
- 实际结果：测试失败，`openapi_tag_metadata_issues()` 报告 `OpenAPI tag metadata missing: categories, crawl, documents, journals, papers, rag, reactions, system`。
- 期望结果：所有 `/api/v1` operation 使用的 tags 都应在 OpenAPI 顶层 `tags` 元数据中声明，并带有非空 description，便于 Swagger/Redoc 发布展示。

## 原因

- 根因：`app/errors.py` 的 `install_openapi_error_schema()` 使用自定义 `get_openapi()` 生成 schema 时只传入 `title`、`version` 和 `routes`，没有传递 FastAPI app 上配置的 tag metadata。
- 影响范围：OpenAPI JSON 中 operation tags 仍存在，但顶层 tag metadata 缺失，接口文档分组没有发布说明。

## 修复

- 修改文件：`app/main.py`、`app/errors.py`、`scripts/validate_api_contract.py`、`tests/test_release_contracts.py`
- 关键行为：`app/main.py` 声明 `OPENAPI_TAGS` 并传给 FastAPI；`app/errors.py` 在自定义 schema 生成时通过 `tags=app.openapi_tags` 保留 metadata；API contract validator 新增 tag metadata gate。

## 验证

- RED 证据：新增 `test_api_contract_openapi_tags_have_metadata_descriptions` 后，当前实现失败并报告 8 个 tag metadata 缺失。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_api_contract_openapi_tags_have_metadata_descriptions tests/test_release_contracts.py::test_api_contract_validator_reports_missing_openapi_tag_metadata tests/test_release_contracts.py::test_api_contract_validator_reports_openapi_tag_metadata_missing_description -q` 返回 `3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 返回 `630 passed`。
