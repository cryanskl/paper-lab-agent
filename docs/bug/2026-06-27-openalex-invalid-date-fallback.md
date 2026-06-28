# OpenAlex invalid publication date dropped fallback year

## 现象

- 触发命令、接口或页面：`OpenAlexClient().normalize(...)` 处理包含非法 `publication_date` 但同时包含有效 `publication_year` 的 OpenAlex work，例如 `publication_date="2026-00-00"`、`publication_year=2026`。
- 实际结果：`published_date` 被归一化为 `null`。
- 期望结果：非法完整日期不可采用时，应保留 OpenAlex 给出的有效年份线索，回退为 `YYYY-01-01`，并继续输出 `published_year`。

## 原因

- 根因：`app/clients/openalex.py` 只在 `publication_date is None` 时使用 `publication_year` fallback；当 `publication_date` 是非 ISO 字符串时直接返回 `None`。
- 影响范围：确定性抓取入库、发布日期筛选结果展示、后续审计和导出里的文献时间线完整性。

## 修复

- 修改文件：`app/clients/openalex.py`、`tests/test_api.py`、`tests/test_clients.py`。
- 关键行为：`normalize_publication_date()` 遇到非法日期字符串时，如果已有合法 `publication_year`，回退输出 `YYYY-01-01`；没有合法年份时仍返回 `None`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_openalex_client_falls_back_to_year_when_publication_date_is_invalid -q` 失败，`published_date` 实际为 `None`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_openalex_client_falls_back_to_year_when_publication_date_is_invalid -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_api.py -q -k openalex_client` 通过，`6 passed, 414 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`871 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `871 passed`。
