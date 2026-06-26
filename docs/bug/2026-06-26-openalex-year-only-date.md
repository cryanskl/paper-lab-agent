# OpenAlex year-only publications lost published_date

## 现象

- OpenAlex work payload 只有 `publication_year`、没有 `publication_date` 时，客户端保留 `published_year`，但 `published_date` 为 `null`。
- 这会让入库论文在按 `published_date` 排序和审计时缺少 ISO 日期，即使年份信息已经可用。
- 期望结果：`publication_date` 缺失且 `publication_year` 有效时，归一化为 `YYYY-01-01`。

## 原因

- `OpenAlexClient.normalize_publication_date` 只解析 `publication_date` 字符串。
- `OpenAlexClient.normalize` 分别计算 `published_date` 和 `published_year`，没有用有效年份补齐缺失日期。

## 修复

- 修改文件：`app/clients/openalex.py`、`tests/test_clients.py`。
- 关键行为：先归一化 `publication_year`；当 `publication_date` 缺失时，用有效年份生成 `YYYY-01-01`。非法日期字符串仍返回 `None`，不被年份掩盖。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_openalex_expands_missing_publication_date_from_year -q` 失败，当前返回 `None`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_openalex_expands_missing_publication_date_from_year tests/test_clients.py -q` 通过，`75 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`734 passed`。
