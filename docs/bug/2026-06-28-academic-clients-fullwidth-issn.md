# Academic clients sent fullwidth ISSN values

## 现象

- 触发命令、接口或页面：OpenAlex / Crossref 客户端收到全角 ISSN，例如 `１２３４－５６７８`。
- 实际结果：OpenAlex filter 和 Crossref journal path 原样携带全角 ISSN。
- 期望结果：ISSN 应在请求前归一化为 ASCII `1234-5678`，避免白名单输入中的全角数字或连字符导致外部 API 查询偏离。

## 原因

- 根因：`app/clients/openalex.py` 与 `app/clients/crossref.py` 对 DOI 已做 NFKC 归一化，但 `works_by_issn()` 只对 ISSN 做 `strip()`。
- 影响范围：白名单期刊抓取、OpenAlex/Crossref 真实请求、中文输入法或复制粘贴场景下的检索稳定性。

## 修复

- 修改文件：`app/clients/openalex.py`、`app/clients/crossref.py`、`tests/test_clients.py`。
- 关键行为：字符串 ISSN 在请求前执行 `unicodedata.normalize("NFKC", issn).strip()`；空白和非字符串 ISSN 仍保持不请求外部 API。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_clients.py::test_openalex_normalizes_fullwidth_issn_before_request tests/test_clients.py::test_crossref_normalizes_fullwidth_issn_before_request -q`，确认 OpenAlex filter 和 Crossref path 都保留全角 ISSN。
- GREEN：`.venv/bin/python -m pytest tests/test_clients.py::test_openalex_normalizes_fullwidth_issn_before_request tests/test_clients.py::test_crossref_normalizes_fullwidth_issn_before_request tests/test_clients.py::test_openalex_returns_no_works_for_blank_issn_without_request tests/test_clients.py::test_crossref_returns_no_works_for_blank_issn_without_request tests/test_clients.py::test_openalex_returns_no_works_for_non_string_issn_without_request tests/test_clients.py::test_crossref_returns_no_works_for_non_string_issn_without_request -q`，6 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，977 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `977 passed`。
