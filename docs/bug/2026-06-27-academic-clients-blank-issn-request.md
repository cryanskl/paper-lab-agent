# Academic metadata clients requested APIs for blank ISSN

## 现象

- 触发命令、接口或页面：`OpenAlexClient.works_by_issn("   ", ...)` 或 `CrossrefClient.works_by_issn("   ", ...)`。
- 实际结果：客户端会把空白 ISSN 放进 OpenAlex filter 或 Crossref `/journals/{issn}/works` 路径，并发起外部 HTTP 请求。
- 期望结果：OpenAlex/Crossref 只应按有效 ISSN 检索元数据；空白 ISSN 应在本地返回空列表，不产生外部请求。

## 原因

- 根因：`app/clients/openalex.py` 和 `app/clients/crossref.py` 在组装请求前没有检查 `issn.strip()` 是否为空。
- 影响范围：确定性检索层、外部 API 礼貌池请求质量、无效期刊配置的失败诊断。

## 修复

- 修改文件：`app/clients/openalex.py`、`app/clients/crossref.py`、`tests/test_clients.py`。
- 关键行为：两个客户端的 `works_by_issn()` 在发起 HTTP 请求前 trim ISSN；trim 后为空时直接返回 `[]`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_openalex_returns_no_works_for_blank_issn_without_request tests/test_clients.py::test_crossref_returns_no_works_for_blank_issn_without_request -q` 失败，当前实现分别请求了 OpenAlex `/works` 和 Crossref `/journals/%20%20%20/works`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_openalex_returns_no_works_for_blank_issn_without_request tests/test_clients.py::test_crossref_returns_no_works_for_blank_issn_without_request -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_clients.py -q` 通过，`77 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`845 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `845 passed`。
