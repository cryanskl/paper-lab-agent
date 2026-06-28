# Keyword matching dropped fullwidth ASCII variants

## 现象

- 触发命令、接口或页面：抓取任务使用 ASCII 关键词配置，例如 `CO2`、`O2`、`Ar O2`，但 OpenAlex / Crossref 元数据或人工配置里出现全角写法，例如 `ＣＯ２`、`Ｏ２`、`Ａｒ`。
- 实际结果：关键词归一化只保留 ASCII 字母数字，全角字符被全部丢弃，`ＣＯ２/Ｏ２` 归一化为空字符串，导致符合条件的文献被过滤。
- 期望结果：全角 ASCII 变体应先规范化为半角 ASCII，再参与既有标点边界和非子串匹配。

## 原因

- 根因：`app/services/crawl.py` 的 `normalize_keyword_text()` 在正则过滤前只处理 Unicode 下标数字，未做 Unicode 兼容归一化。
- 影响范围：确定性检索层的关键词过滤、crawl job 的 `papers_filtered` 统计、真实外部元数据或复制粘贴配置里的化学式召回率。

## 修复

- 修改文件：`app/services/crawl.py`、`tests/test_api.py`。
- 关键行为：关键词和标题/摘要归一化前先执行 Unicode `NFKC` 归一化，将全角 ASCII 变体转为半角形式，再沿用已有下标数字转换、标点边界和词级匹配逻辑。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_keyword_matching_normalizes_fullwidth_ascii_variants -q` 失败，`normalize_keyword_text("ＣＯ２/Ｏ２")` 实际为空字符串。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_keyword_matching_normalizes_fullwidth_ascii_variants -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_api.py -q -k "crawl_keyword_matching"` 通过，`6 passed, 416 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`873 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `873 passed`。
