# Unpaywall requested fullwidth DOI text without normalization

## 现象

- 触发命令、接口或页面：直接调用 `UnpaywallClient.resolve()` 或手动 OA 补全链路传入全角 DOI，例如 `ＤＯＩ：１０.５５５５／ＡＢＣ．Ｄｅｆ`。
- 实际结果：客户端只做 `strip()`，会把全角 DOI 文本编码进 Unpaywall 请求路径，无法稳定查询合法 DOI。
- 期望结果：Unpaywall 请求前应与 OpenAlex / Crossref / crawl 入库层一致，先将 DOI 归一化为 `10.5555/abc.def`，再 URL 编码。

## 原因

- 根因：`app/clients/unpaywall.py` 没有独立 DOI 归一化 helper，只在 `resolve()` 内对入参调用 `strip()`。
- 影响范围：OA 链接补全、手动重新解析 OA、外部 API 请求质量和后续 raw metadata 审计。

## 修复

- 修改文件：`app/clients/unpaywall.py`、`tests/test_clients.py`。
- 关键行为：Unpaywall 客户端在请求前执行 Unicode `NFKC`、lower、常见 DOI URL/prefix 移除，并保持空白 DOI 本地拒绝逻辑。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_unpaywall_normalizes_fullwidth_doi_before_request -q` 失败，实际请求路径使用全角 DOI 文本。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_unpaywall_normalizes_fullwidth_doi_before_request -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_clients.py -q -k "unpaywall"` 通过，`13 passed, 67 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`878 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `878 passed`。
