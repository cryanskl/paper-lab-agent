# 异步响应契约未校验资源元数据

- 日期：2026-06-27
- 触发命令、接口或页面：运行 `scripts/validate_api_contract.py docs/接口设计文档.md`，但异步接口 OpenAPI schema 只声明 `job_id/status` 时仍可通过。
- 影响范围：`POST /documents/{id}/parse`、`POST /documents/{id}/translate`、`POST /documents/{id}/index`、`POST /documents/{id}/extract-chemistry`、`POST /crawl/run` 的发布契约门禁。

## 现象

接口文档要求异步响应立即返回可轮询资源的元数据，例如 `document_id`、`parse_status`、`target_lang`、`index_status`、`chemistry_status`，抓取任务列表项也包含 `journal_id`、`period`、`date_from`、`date_to`。旧版契约校验只检查 `job_id/status`，因此 OpenAPI 退化为缺少这些字段时不会失败。

## 原因

`scripts/validate_api_contract.py` 使用统一的 `ASYNC_RESPONSE_FIELDS = ("job_id", "status")` 校验所有异步端点，没有按端点区分接口文档中的响应体字段。`AsyncJobResponse` 虽允许 extra 字段透传，但 OpenAPI schema 没有显式声明这些实际返回字段。

## 修复

- 在契约校验脚本中增加按异步端点区分的必需响应字段。
- 在 `AsyncJobResponse` 中显式声明文档导入/解析/翻译/索引/化学抽取/抓取任务返回的资源元数据字段，保证 OpenAPI 与实际 JSON 响应一致。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_api_contract_validator_reports_missing_document_async_metadata -q` 失败，当前实现返回 `[]`。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_api_contract_validator_reports_missing_document_async_metadata tests/test_release_contracts.py::test_api_contract_validator_reports_missing_async_response_field tests/test_release_contracts.py::test_api_contract_async_routes_expose_pending_response_shape -q` 通过，`3 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "api_contract"` 通过，`84 passed, 208 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`868 passed`；`bash scripts/release_check.sh` 通过。
