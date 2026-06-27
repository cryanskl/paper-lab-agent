# 手动 OA 解析成功但无新 raw 时残留旧 Unpaywall 数据

## 现象

`POST /api/v1/papers/{id}/resolve-oa` 本次解析成功并更新 `oa_status`、`oa_pdf_url`，但 adapter 没有返回新的 `raw` payload 时，旧的 `raw_metadata.unpaywall` 仍然残留。结果当前 OA 状态和历史 Unpaywall 原始响应可能不一致。

## 原因

手动 OA 解析成功分支只清理旧 `oa_resolution_error`，只有在本次返回 `raw` 时才覆盖 `raw_metadata.unpaywall`，没有在无新 raw 的成功结果中删除旧 raw。

## 修复

成功分支先清理旧 `raw_metadata.unpaywall`；如果本次结果包含新的 raw payload，再写入新的 `raw_metadata.unpaywall`。这样成功、失败和 adapter error 三类结果都不会残留上一轮 Unpaywall 原始证据。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_resolve_oa_clears_stale_unpaywall_raw_when_success_has_no_raw -q` 失败，旧 `raw_metadata.unpaywall` 仍然存在。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_resolve_oa_clears_stale_unpaywall_raw_when_success_has_no_raw tests/test_api.py::test_resolve_oa_records_unpaywall_raw_metadata tests/test_api.py::test_resolve_oa_clears_stale_unpaywall_raw_on_failure tests/test_api.py::test_resolve_oa_clears_stale_unpaywall_raw_on_adapter_error tests/test_api.py::test_resolve_oa_records_failure_without_server_error -q` 通过，`5 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`893 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `893 passed`。
