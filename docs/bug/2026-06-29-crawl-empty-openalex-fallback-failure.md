# Crawl failure diagnostics dropped OpenAlex empty-result context when Crossref failed

## 现象

- 触发命令、接口或页面：运行 `/api/v1/crawl/run` 创建抓取任务，OpenAlex 正常返回空列表后，Crossref fallback 失败。
- 实际结果：`crawl_jobs.error` 只记录 Crossref 的失败原因，例如 `Crossref 503`，无法看出 OpenAlex 已经被访问且返回了空结果。
- 期望结果：抓取任务应同时记录 `OpenAlex returned no works` 和 Crossref 失败原因，便于区分“源无结果 + fallback 故障”和“OpenAlex 未执行”。

## 原因

- 根因：`app/services/crawl.py` 的 `fetch_metadata_works()` 只在 OpenAlex 抛异常时包装 Crossref fallback 的失败；当 OpenAlex 返回空列表并设置 `openalex_empty=True` 时，Crossref 异常直接向外传播。
- 影响范围：确定性检索层、crawl job 失败排障、P1 外部元数据源可诊断性。

## 修复

- 修改文件：`app/services/crawl.py`、`tests/test_api.py`。
- 关键行为：当 OpenAlex 返回空结果且 Crossref fallback 失败时，抛出包含 `OpenAlex returned no works; Crossref failed: ...` 的错误；Crossref fallback 成功时仍保持既有 `OpenAlex returned no works; used Crossref fallback` 诊断。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_job_failure_reports_openalex_empty_and_crossref_error -q` 失败，`crawl_jobs.error` 实际只有 `Crossref 503`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_crawl_job_failure_reports_openalex_empty_and_crossref_error tests/test_api.py::test_crawl_job_failure_reports_openalex_and_crossref_errors tests/test_api.py::test_crawl_job_falls_back_to_crossref_when_openalex_fails tests/test_api.py::test_crawl_job_records_diagnostic_when_openalex_empty_uses_crossref -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1258 passed。
