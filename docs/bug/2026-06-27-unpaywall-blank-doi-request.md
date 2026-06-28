# Unpaywall lookup requested API for blank DOI

## 现象

- 触发命令、接口或页面：`UnpaywallClient.resolve("   ")` 或其他把空白 DOI 传入 Unpaywall 客户端的调用路径。
- 实际结果：客户端会把空白 DOI 编码成空路径段，并请求 `https://api.unpaywall.org/v2/?email=...`。
- 期望结果：Unpaywall 只应按有效 DOI 查 OA；空白 DOI 应在本地返回 `oa_status=unknown` 和明确 error，不产生外部请求。

## 原因

- 根因：`app/clients/unpaywall.py` 只检查 `UNPAYWALL_EMAIL` 是否配置，没有在 URL 编码前检查 `doi.strip()` 是否为空。
- 影响范围：OA 链接补全、手动重新解析 OA、外部 API 礼貌池请求质量和失败诊断。

## 修复

- 修改文件：`app/clients/unpaywall.py`、`tests/test_clients.py`。
- 关键行为：`resolve()` 在发起 HTTP 请求前拒绝空白 DOI，返回 `{"oa_status":"unknown","oa_pdf_url":null,"error":"DOI is required for Unpaywall lookup"}`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_unpaywall_returns_unknown_for_blank_doi_without_request -q` 失败，当前实现请求了 `https://api.unpaywall.org/v2/?email=dev%40example.test`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_unpaywall_returns_unknown_for_blank_doi_without_request -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_clients.py -q -k "unpaywall"` 通过，`12 passed, 63 deselected`；Unpaywall API 扩展组通过，`10 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`843 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `843 passed`。
