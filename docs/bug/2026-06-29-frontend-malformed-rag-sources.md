# Frontend RAG sources crashed on malformed source entries

## 现象

- 触发命令、接口或页面：Streamlit RAG 问答页调用 `rag_source_rows(rag_payload.get("sources") or [])` 渲染引用来源；`sources` 列表里混入非对象条目，例如字符串。
- 实际结果：`rag_source_rows()` 直接调用 `source.get()`，非对象 source 触发 `AttributeError`，导致问答结果和引用来源区域渲染失败。
- 期望结果：RAG 引用来源展示层应稳定降级：异常 source 显示为 `citation=[invalid]`、`source_location=invalid`，同一响应里的有效 source 继续展示。

## 原因

- 根因：展示层 helper 假设 RAG 返回的 `sources` 每一项都符合 API 契约，没有在 Streamlit 渲染边界校验 source 条目类型。
- 影响范围：Streamlit RAG 问答页引用来源展示、RAG 回答排障，以及接口契约漂移或异常检索结果下的演示稳定性。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`rag_source_rows()` 对非对象 source 输出一行 invalid 引用记录，并继续处理后续有效 source；正常 source 的 citation、location 和 excerpt 展示保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_rag_source_rows_handle_malformed_source_entries -q` 失败，非对象 source 触发 `AttributeError: 'str' object has no attribute 'get'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_rag_source_rows_handle_malformed_source_entries tests/test_frontend_api.py::test_rag_source_rows_include_citation_and_location_labels -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`118 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_rag_tab_separates_answer_and_sources tests/test_api.py::test_streamlit_rag_query_errors_show_payload_details -q` 通过，`2 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1175 passed`。
