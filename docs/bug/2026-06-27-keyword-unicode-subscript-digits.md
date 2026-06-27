# Keyword matching dropped Unicode subscript digits

## 现象

- 触发命令、接口或页面：抓取任务使用关键词 `O2`、`CO2`、`N2` 或组合词过滤 OpenAlex / Crossref 元数据时，论文标题或摘要里写作 `O₂`、`CO₂`、`N₂`。
- 实际结果：关键词归一化把 Unicode 下标数字丢掉，例如 `CO₂/O₂` 变成 `co o`，导致符合条件的文献被过滤。
- 期望结果：常见化学式下标数字应归一化为 ASCII 数字，`CO₂/O₂/N₂` 能被配置里的 `co2`、`o2`、`n2` 命中。

## 原因

- 根因：`app/services/crawl.py` 的 `normalize_keyword_text()` 只保留 ASCII 字母数字，未先把 Unicode 下标数字转换为普通数字。
- 影响范围：确定性检索层的关键词过滤、crawl job 的 `papers_filtered` 统计、白名单期刊真实论文召回率。

## 修复

- 修改文件：`app/services/crawl.py`、`tests/test_api.py`。
- 关键行为：关键词和标题/摘要归一化前，先把 `₀₁₂₃₄₅₆₇₈₉` 转成 `0123456789`，再保持原有标点边界和非子串匹配逻辑。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_keyword_matching_normalizes_unicode_subscript_digits -q` 失败，`normalize_keyword_text("CO₂/O₂")` 实际为 `co o`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_keyword_matching_normalizes_unicode_subscript_digits -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_api.py -q -k "crawl_keyword_matching"` 通过，`5 passed, 416 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`872 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `872 passed`。
