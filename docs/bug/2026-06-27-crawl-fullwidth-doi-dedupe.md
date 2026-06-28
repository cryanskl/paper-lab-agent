# Crawl dedupe did not normalize fullwidth DOI text

## 现象

- 触发命令、接口或页面：抓取编排或人工数据把 DOI 传入 crawl 入库逻辑，且 DOI 来自复制粘贴的全角写法，例如 `ＤＯＩ：１０.５５５５／ＡＢＣ．Ｄｅｆ`。
- 实际结果：`normalize_doi()` 不做 Unicode 兼容归一化，无法识别全角 `ＤＯＩ：` 前缀、数字、斜杠和句点，去重键会保留异常字符串。
- 期望结果：全角 DOI 文本应归一化为半角 ASCII 后再去前缀和 lower，得到稳定的 `10.5555/abc.def`。

## 原因

- 根因：`app/services/crawl.py` 的 `normalize_text()` 只做 `strip()`、lower 和空白折叠，没有执行 Unicode `NFKC` 归一化。
- 影响范围：确定性抓取入库的 DOI 去重、重复抓取更新路径、Unpaywall 解析前的 DOI 规范化，以及 no-DOI fingerprint 里的标题/日期/URL 文本稳定性。

## 修复

- 修改文件：`app/services/crawl.py`、`tests/test_api.py`。
- 关键行为：crawl 层通用 `normalize_text()` 先执行 Unicode `NFKC` 归一化，再保持原有 lower 和空白折叠逻辑。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_service_normalizes_fullwidth_doi_for_dedupe -q` 失败，`normalize_doi()` 实际返回 `ｄｏｉ：１０.５５５５／ａｂｃ．ｄｅｆ`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_service_normalizes_fullwidth_doi_for_dedupe -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_api.py -q -k "crawl_service_strips_space_after_doi_prefix_for_dedupe or crawl_service_normalizes_fullwidth_doi_for_dedupe or crawl_keyword_matching"` 通过，`8 passed, 415 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`875 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `875 passed`。
