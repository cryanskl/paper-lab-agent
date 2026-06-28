# 关键词过滤会误命中词内子串

- 日期：2026-06-27
- 触发命令、接口或页面：抓取任务执行关键词过滤时，期刊关键词包含短词，例如 `ion`。
- 影响范围：确定性抓取层的入库前关键词过滤，可能把不相关论文写入 `papers` 并影响 crawl job 的 filtered/new 统计。

## 现象

旧逻辑把规范化后的关键词当普通子串查找。关键词 `ion` 会命中 `simulation`，导致标题或摘要只包含 `simulation` 的论文被视为命中 `ion`。

## 原因

`matches_keywords()` 使用 `term in haystack`，没有区分完整词、短语边界和词内子串。虽然标点会被归一为空格，多词短语可用，但短词会在较长单词内部误命中。

## 修复

- 继续保留现有的大小写、空白和标点归一化。
- 将 haystack 包裹空格后，用 ` f" {term} " in padded_haystack ` 做完整词/短语匹配。
- 保持 AND/OR 语义不变，`plasma simulation`、`ar o2` 这类短语仍可命中规范化后的文本。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_keyword_matching_does_not_match_inside_words -q` 失败，`ion` 误命中 `simulation`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_keyword_matching_does_not_match_inside_words tests/test_api.py::test_crawl_keyword_matching_collapses_internal_whitespace tests/test_api.py::test_crawl_keyword_matching_treats_punctuation_as_word_boundaries tests/test_api.py::test_crawl_keyword_matching_strips_mode_whitespace tests/test_api.py::test_keyword_matching_supports_or_and_and_modes -q` 通过，`5 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`869 passed`；`bash scripts/release_check.sh` 通过。
