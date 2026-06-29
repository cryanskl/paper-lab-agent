# Frontend crawl journal selector crashed on malformed journal items

## 现象

- 触发命令、接口或页面：Streamlit 检索页的手动抓取期刊 selectbox 使用 `/api/v1/journals` 返回值构建 `crawl_journal_options()`，但列表中包含非 dict 项或缺少必要字段的 journal 项。
- 实际结果：`crawl_journal_options()` 直接调用 `journal.get(...)` 并访问 `journal["id"]` / `journal["name"]`，遇到 malformed 项会抛出 `AttributeError` 或 `KeyError`，导致手动抓取控件无法渲染。
- 期望结果：手动抓取期刊选项应保留默认“全部 active 期刊”选项，并跳过 malformed journal 项，避免前端被异常 API 响应拖垮。

## 原因

- 根因：展示层 helper 假设 journals 列表项都是完整 journal dict，没有校验 item 类型、`id` 类型和 `name` 字符串形状。
- 影响范围：Streamlit 检索页手动抓取控件、异常 API 响应或接口契约漂移时的期刊选择器。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`crawl_journal_options()` 只接受 dict 且含非 bool 整数 `id`、非空字符串 `name` 的 journal 项；其他项跳过，默认“全部 active 期刊”选项始终保留。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_crawl_journal_options_skips_malformed_journal_items -q` 失败，非 dict journal 触发 `AttributeError: 'str' object has no attribute 'get'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_crawl_journal_options_skips_malformed_journal_items tests/test_frontend_api.py::test_crawl_journal_options_label_whitelist_choices_for_manual_runs -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`105 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_crawl_run_surfaces_success_and_error_states -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1162 passed`。
