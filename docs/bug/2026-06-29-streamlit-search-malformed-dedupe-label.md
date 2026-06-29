# Streamlit search page crashed on malformed dedupe label

## 现象

- 触发命令、接口或页面：Streamlit 搜索页渲染论文卡片的去重信息行。
- 实际结果：当论文没有 DOI，且 `dedupe_key` 是 bool、数字或对象等非字符串值时，页面会在执行 `[:24]` 切片时崩溃。
- 期望结果：去重标签只从非空字符串 DOI 或非空字符串 `dedupe_key` 生成；异常值显示为 `-`。

## 原因

- 根因：搜索结果卡片直接对 `/papers` 响应里的 `dedupe_key` 做字符串切片，没有先做类型校验。
- 影响范围：搜索页结果卡片、发布演示中的异常 API 响应处理，以及历史脏数据下的列表渲染。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `paper_search_dedupe_label()`，仅接受非空字符串 DOI 或 `dedupe_key`；Streamlit 搜索卡片改为使用该 helper。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_search_dedupe_label_handles_malformed_values tests/test_api.py::test_streamlit_search_results_use_guarded_dedupe_label -q` 失败，helper 缺失且搜索页仍直接切片 `dedupe_key`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_search_dedupe_label_handles_malformed_values tests/test_api.py::test_streamlit_search_results_use_guarded_dedupe_label tests/test_api.py::test_streamlit_search_results_show_dedupe_strategy tests/test_api.py::test_streamlit_search_results_use_filtered_paper_items -q` 通过，4 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1220 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1220 passed。
