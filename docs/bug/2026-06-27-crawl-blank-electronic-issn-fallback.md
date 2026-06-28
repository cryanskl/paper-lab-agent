# Crawl used blank electronic ISSN instead of valid print ISSN

## 现象

- 触发命令、接口或页面：`run_crawl_job()` 处理历史或迁移数据中 `issn_electronic="   "` 且 `issn_print="1111-2222"` 的期刊。
- 实际结果：crawl 编排层把空白电子 ISSN 传给 OpenAlex/Crossref，导致本可按纸质 ISSN 检索的期刊返回空结果或无效请求。
- 期望结果：crawl 编排层应选择第一个非空白 ISSN；电子 ISSN 为空白时应回退到有效纸质 ISSN。

## 原因

- 根因：`app/services/crawl.py` 使用 `journal.get("issn_electronic") or journal.get("issn_print")` 选择 ISSN，未 trim 空白字符串。
- 影响范围：确定性检索层、旧数据/迁移数据兼容性、crawl job 的 found/new 统计和诊断准确性。

## 修复

- 修改文件：`app/services/crawl.py`、`tests/test_api.py`。
- 关键行为：`run_crawl_job()` 选择 ISSN 时复用 `optional_text()`，只让非空白电子 ISSN 优先于纸质 ISSN。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_job_uses_print_issn_when_electronic_issn_is_blank -q` 失败，当前实现传给客户端的是 `'   '` 而不是 `1111-2222`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_job_uses_print_issn_when_electronic_issn_is_blank -q` 通过，`1 passed`；crawl job 相关 focused 测试通过，`11 passed, 401 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`846 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `846 passed`。
