# Academic clients skipped requests when max_pages was zero

## 现象

- 触发命令、接口或页面：配置 `ACADEMIC_API_MAX_PAGES=0` 或代码直接调用 `OpenAlexClient.works_by_issn(..., max_pages=0)` / `CrossrefClient.works_by_issn(..., max_pages=0)`。
- 实际结果：客户端循环 0 次，不向 OpenAlex 或 Crossref 发起任何请求，调用方得到空列表。
- 期望结果：页数配置异常时仍至少请求第一页，避免把配置错误误判成“元数据源无结果”。

## 原因

- 根因：OpenAlex 和 Crossref 客户端直接使用 `range(max_pages)` 控制分页；当 `max_pages <= 0` 时循环不会执行。
- 影响范围：确定性检索层、crawl job 诊断、发布前真实抓取验证。错误配置会静默变成空结果，降低失败可诊断性。

## 修复

- 修改文件：`app/clients/openalex.py`、`app/clients/crossref.py`、`tests/test_clients.py`。
- 关键行为：两个客户端在发起分页请求前把 `max_pages` 下限收敛为 `1`，确保至少请求第一页。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_clients.py -k "max_pages_is_zero" -q` 失败，两个客户端均未发起请求，`len(seen_urls) == 0`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_clients.py -k "max_pages_is_zero" -q` 通过，`2 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1256 passed。
