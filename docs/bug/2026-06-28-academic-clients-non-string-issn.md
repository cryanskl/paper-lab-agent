# Academic clients crashed on non-string ISSN

## 现象

- 触发命令、接口或页面：OpenAlex / Crossref 客户端收到非字符串 ISSN，例如 `None`。
- 实际结果：`works_by_issn()` 在 `issn.strip()` 处抛出 `AttributeError`。
- 期望结果：无效 ISSN 不应触发外部请求，也不应让抓取链路因输入类型崩溃；客户端应返回空列表，和空白 ISSN 的行为一致。

## 原因

- 根因：`app/clients/openalex.py` 与 `app/clients/crossref.py` 只处理空白字符串，没有在 `.strip()` 前检查 ISSN 类型。
- 影响范围：白名单数据异常、未来导入或配置漂移时的外部检索稳定性。

## 修复

- 修改文件：`app/clients/openalex.py`、`app/clients/crossref.py`、`tests/test_clients.py`。
- 关键行为：非字符串 ISSN 直接返回 `[]`，不发起 OpenAlex / Crossref 请求。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_clients.py::test_openalex_returns_no_works_for_non_string_issn_without_request tests/test_clients.py::test_crossref_returns_no_works_for_non_string_issn_without_request -q`，确认两个客户端都因 `AttributeError` 失败。
- GREEN：`.venv/bin/python -m pytest tests/test_clients.py::test_openalex_returns_no_works_for_non_string_issn_without_request tests/test_clients.py::test_crossref_returns_no_works_for_non_string_issn_without_request tests/test_clients.py::test_openalex_returns_no_works_for_blank_issn_without_request tests/test_clients.py::test_crossref_returns_no_works_for_blank_issn_without_request -q`，4 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，975 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `975 passed`。
