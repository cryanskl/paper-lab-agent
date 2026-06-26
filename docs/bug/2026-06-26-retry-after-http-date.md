# Retry-After HTTP-date was ignored by academic clients

## 现象

- OpenAlex、Crossref 和 Unpaywall 客户端在 429 响应中只解析数字秒数格式的 `Retry-After`。
- 当服务端返回 HTTP-date 格式，例如 `Thu, 01 Jan 1970 00:00:05 GMT`，客户端会忽略该值并退回固定 backoff。
- 真实抓取时可能不遵守服务端要求的等待时间，增加重复限流或失败风险。

## 原因

- 三个客户端各自用 `float(retry_after)` 解析 header。
- `Retry-After` 按 HTTP 规范既可以是 delta seconds，也可以是 HTTP-date；日期格式此前没有测试覆盖。

## 修复

- 新增 `app/clients/retry_after.py`，统一解析 `Retry-After` 的数字秒数和 HTTP-date 两种格式。
- HTTP-date 格式优先使用响应 `Date` header 作为参考时间，缺失时使用当前 UTC 时间。
- OpenAlex、Crossref 和 Unpaywall 的 `retry_delay` 统一调用共享解析工具。

## 验证

- RED：`python -m pytest tests/test_clients.py::test_academic_clients_parse_retry_after_http_date -q` 在日期格式未支持时失败。
- GREEN：`python -m pytest tests/test_clients.py::test_academic_clients_parse_retry_after_http_date -q`
- 客户端测试：`python -m pytest tests/test_clients.py -q`
- 完整 gate：`bash scripts/release_check.sh`
