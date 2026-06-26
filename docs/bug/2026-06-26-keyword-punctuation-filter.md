# Keyword filtering missed punctuation variants

## 现象

- 抓取关键词配置为 `plasma chemistry` 时，标题里的 `plasma-chemistry` 不会命中。
- AND 配置中 `ar o2` 也无法命中摘要里的 `Ar/O2`。
- 这会让相关论文在入库前被关键词过滤误剔除，影响 P1 确定性检索层召回。

## 原因

- `matches_keywords` 复用通用 `normalize_text`，只折叠空白并小写。
- 连字符、斜杠等常见论文标题标点不会被视为词边界，导致语义相同的关键词变体无法匹配。

## 修复

- 修改文件：`app/services/crawl.py`、`tests/test_api.py`。
- 关键行为：新增关键词专用 `normalize_keyword_text`，把非字母数字序列折叠为空格；仅用于关键词配置和匹配文本，不改变 DOI/去重等通用归一化行为。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_keyword_matching_treats_punctuation_as_word_boundaries -q` 失败，`plasma chemistry` 未命中 `plasma-chemistry`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_keyword_matching_collapses_internal_whitespace tests/test_api.py::test_crawl_keyword_matching_treats_punctuation_as_word_boundaries tests/test_api.py::test_crawl_keyword_matching_strips_mode_whitespace tests/test_api.py::test_keyword_matching_supports_or_and_and_modes -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`735 passed`。
