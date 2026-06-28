# 手动 OA 解析失败后残留旧 Unpaywall 原始数据

## 现象

`POST /api/v1/papers/{id}/resolve-oa` 在 Unpaywall 请求失败或 adapter 返回错误时，会把论文 `oa_status` 更新为 `unknown` 并写入 `oa_resolution_error`，但旧的 `raw_metadata.unpaywall` 仍然保留。结果同一条论文同时显示当前 OA 解析失败和旧的 green OA 原始响应，排障证据不一致。

## 原因

手动 OA 解析的失败路径只写入 `oa_resolution_error`，没有删除上一轮成功解析时保存的 `raw_metadata.unpaywall`。

## 修复

在 Unpaywall adapter 返回 `error` 或抛出异常时，先清理 `raw_metadata.unpaywall`，再保留当前失败原因；成功路径保持写入新的 Unpaywall raw payload，并清除旧失败原因。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_resolve_oa_clears_stale_unpaywall_raw_on_failure tests/test_api.py::test_resolve_oa_clears_stale_unpaywall_raw_on_adapter_error -q` 失败，两个场景都残留旧 `raw_metadata.unpaywall`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_resolve_oa_clears_stale_unpaywall_raw_on_failure tests/test_api.py::test_resolve_oa_clears_stale_unpaywall_raw_on_adapter_error tests/test_api.py::test_resolve_oa_records_failure_without_server_error tests/test_api.py::test_resolve_oa_records_unpaywall_raw_metadata tests/test_api.py::test_resolve_oa_normalizes_adapter_oa_status_before_storing tests/test_api.py::test_resolve_oa_rejects_adapter_non_web_pdf_url_before_storing tests/test_api.py::test_resolve_oa_uses_and_stores_normalized_doi -q` 通过，`7 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`892 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `892 passed`。
