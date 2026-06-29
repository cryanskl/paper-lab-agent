# Streamlit search page crashed on malformed abstract preview

## 现象

- 触发命令、接口或页面：Streamlit 搜索页渲染论文卡片摘要预览。
- 实际结果：当 `/papers` 响应中的 `abstract` 是 bool、数字、列表或对象等非字符串真值时，页面会在执行 `[:400]` 切片时崩溃。
- 期望结果：摘要预览只从字符串 `abstract` 生成；异常值显示为空摘要，不影响整页搜索结果渲染。

## 原因

- 根因：搜索结果卡片直接对原始 `paper.get("abstract")` 做字符串切片，没有先校验字段类型。
- 影响范围：搜索页结果卡片、发布演示中的异常 API 响应处理，以及历史脏数据下的列表渲染。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `paper_search_abstract_preview()`，仅接受字符串摘要并截断到 400 字符；Streamlit 搜索卡片改为使用该 helper。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_search_abstract_preview_handles_malformed_values tests/test_api.py::test_streamlit_search_results_use_guarded_abstract_preview -q` 失败，helper 缺失且搜索页仍直接切片 `abstract`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_paper_search_abstract_preview_handles_malformed_values tests/test_api.py::test_streamlit_search_results_use_guarded_abstract_preview tests/test_api.py::test_streamlit_search_results_use_guarded_dedupe_label tests/test_api.py::test_streamlit_search_results_use_filtered_paper_items -q` 通过，4 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1222 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1222 passed。
