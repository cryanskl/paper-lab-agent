# Crawl failure diagnostics dropped the OpenAlex error when Crossref also failed

## 现象

- 触发命令、接口或页面：运行 `/api/v1/crawl/run` 创建抓取任务，OpenAlex 失败后 Crossref fallback 也失败。
- 实际结果：`crawl_jobs.error` 只记录 Crossref 的失败原因，例如 `Crossref 503`，丢失最先失败的 OpenAlex 诊断。
- 期望结果：两个元数据源都失败时，抓取任务应记录 OpenAlex 和 Crossref 两个错误，便于判断是单源故障、fallback 故障还是配置/网络共同问题。

## 原因

- 根因：`app/services/crawl.py` 的 `fetch_metadata_works()` 捕获 OpenAlex 异常后直接调用 Crossref；如果 Crossref 再抛异常，该异常未包装 OpenAlex 上下文就向外传播。
- 影响范围：确定性检索层、crawl job 失败排障、P1 外部元数据源可诊断性。

## 修复

- 修改文件：`app/services/crawl.py`、`tests/test_api.py`。
- 关键行为：当 OpenAlex 已失败且 Crossref fallback 也失败时，抛出包含 `OpenAlex failed: ...; Crossref failed: ...` 的错误；Crossref fallback 成功时仍保持既有 `OpenAlex failed; used Crossref fallback: ...` 诊断。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_job_failure_reports_openalex_and_crossref_errors -q` 失败，`crawl_jobs.error` 实际只有 `Crossref 503`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_job_failure_reports_openalex_and_crossref_errors tests/test_api.py::test_crawl_job_falls_back_to_crossref_when_openalex_fails tests/test_api.py::test_crawl_job_records_diagnostic_when_openalex_empty_uses_crossref -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1257 passed。
