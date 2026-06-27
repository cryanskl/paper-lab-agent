# Academic API contact fields kept surrounding whitespace

## 现象

- 触发命令、接口或页面：直接构造 OpenAlex、Crossref 或 Unpaywall 客户端时传入带首尾空白的联系邮箱，例如 `  lab@example.test  `。
- 实际结果：客户端把空白原样写入 query 参数和 `User-Agent`，例如 `mailto=++lab@example.test++` 或 `paper-lab-agent (mailto:  lab@example.test  )`。
- 期望结果：外部 API polite pool 联系字段应在客户端边界清理首尾空白；纯空白值应视为未配置。

## 原因

- 根因：`app/clients/openalex.py`、`app/clients/crossref.py`、`app/clients/unpaywall.py` 的构造函数直接保存传入值，没有做客户端级 `strip()` 归一化。
- 影响范围：OpenAlex / Crossref polite pool 请求质量、Unpaywall email 参数、请求日志和外部 API 诊断。

## 修复

- 修改文件：`app/clients/openalex.py`、`app/clients/crossref.py`、`app/clients/unpaywall.py`、`tests/test_api.py`、`tests/test_clients.py`。
- 关键行为：三个客户端在构造时将联系邮箱 `strip()`；清理后为空则视为 `None`，保持缺配置 fallback 行为。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_crossref_strips_mailto_whitespace_for_polite_pool tests/test_api.py::test_openalex_client_strips_mailto_whitespace_for_polite_pool tests/test_api.py::test_unpaywall_client_strips_email_whitespace_for_polite_pool -q` 失败，query 参数仍包含首尾空白。
- GREEN 证据：同一 focused pytest 通过，`3 passed`；`.venv/bin/python -m pytest tests/test_api.py -q -k "polite_user_agent or strips_mailto_whitespace or strips_email_whitespace"` 通过，`4 passed, 421 deselected`；`.venv/bin/python -m pytest tests/test_clients.py -q -k "crossref_includes_mailto or strips_mailto_whitespace or unpaywall"` 通过，`15 passed, 66 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`881 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `881 passed`。
