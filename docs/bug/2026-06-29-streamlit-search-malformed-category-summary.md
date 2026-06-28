# Streamlit search page crashed on malformed category summary fields

## 现象

- 触发命令、接口或页面：Streamlit 搜索页渲染论文卡片、触发分类或保存人工分类后，会调用 `format_category_summary()` 展示 `category_details`。
- 实际结果：旧实现直接遍历 `category_details` 并用 `f"{confidence:.2f}"` 格式化置信度；当详情列表混入非对象、字符串置信度、bool 置信度或缺少 `slug` 时，页面会在渲染分类摘要时崩溃。
- 期望结果：分类摘要只使用结构有效的详情；非数字置信度显示 `-`，缺少 slug 时显示 `category`，没有有效详情时回退到 `categories` 字符串列表，最后兜底为 `-`。

## 原因

- 根因：分类摘要逻辑留在 `streamlit_app.py` 本地函数中，缺少单元测试，也没有校验 `category_details` 内部字段类型。
- 影响范围：搜索结果卡片、触发自动分类后的成功提示、保存人工分类后的成功提示，以及异常 API 响应或历史脏数据下的发布演示。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增可测试的 `format_category_summary()` helper；Streamlit 改为从 `app.frontend_api` 导入该 helper；异常详情项被跳过或降级显示。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_format_category_summary_handles_malformed_details tests/test_frontend_api.py::test_format_category_summary_falls_back_to_category_slugs tests/test_api.py::test_streamlit_search_results_can_trigger_classification -q` 失败，`frontend_api` helper 缺失且 Streamlit 仍保留本地未测试函数。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_format_category_summary_handles_malformed_details tests/test_frontend_api.py::test_format_category_summary_falls_back_to_category_slugs tests/test_api.py::test_streamlit_search_results_can_trigger_classification tests/test_api.py::test_streamlit_search_classification_errors_show_payload_details tests/test_api.py::test_streamlit_search_results_can_override_categories_manually tests/test_api.py::test_streamlit_search_manual_category_errors_show_payload_details -q` 通过，6 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1216 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1216 passed`。
