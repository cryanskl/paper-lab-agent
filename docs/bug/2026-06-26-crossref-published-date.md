# Crossref published date was ignored

## 现象

- Crossref work payload 中只有通用 `published` 日期字段，或 `published` 比 `issued` 更具体时，客户端不会读取 `published`。
- 归一化会直接回退到 `issued`，导致 `published_date` 和 `published_year` 可能早于真实发表日期。
- 这会影响抓取入库后的日期排序、年份过滤和 crawl job 审计。

## 原因

- `CrossrefClient.first_publication_date` 的候选字段只有 `published-print`、`published-online` 和 `issued`。
- Crossref 常见的 `published` 字段没有进入日期优先级列表。

## 修复

- 修改文件：`app/clients/crossref.py`、`tests/test_clients.py`。
- 关键行为：日期归一化优先级改为 `published-print`、`published-online`、`published`、`issued`，保留既有字段容错和部分日期扩展逻辑。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_crossref_uses_published_date_before_issued_date -q` 失败，当前返回 `2026-01-01`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_crossref_uses_published_date_before_issued_date tests/test_clients.py -q` 通过，`74 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`733 passed`。
