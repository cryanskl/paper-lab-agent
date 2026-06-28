# Streamlit config page accepted malformed category parent options

## 现象

- 触发命令、接口或页面：Streamlit 配置页调用 `/api/v1/categories` 后，用 `category_parent_options(categories_all)` 生成“新增分类”的父级分类下拉。
- 实际结果：父级选项只过滤非对象，但会保留缺少 `id`、字符串 `id` 或 bool `id` 的分类对象；当用户选中这类对象并提交时，页面会读取 `parent_choice["id"]` 生成 payload，导致崩溃或提交非法 `parent_id`。
- 期望结果：进入父级分类下拉的 category 必须带有非 bool 整数 `id`；异常条目被跳过，“无”选项仍保留。

## 原因

- 根因：`category_parent_options()` 只校验对象类型，没有校验后续提交路径必需的 `id` 字段。
- 影响范围：配置页新增分类、父级分类选择，以及异常 API 响应或历史脏数据下的发布演示。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：`category_parent_options()` 现在只保留带非 bool 整数 `id` 的 category，并继续保留首个 `None` 选项表示无父级分类。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_category_parent_options_skip_malformed_items -q` 失败，helper 保留了缺 id、字符串 id 和 bool id 的分类对象。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_category_parent_options_skip_malformed_items tests/test_frontend_api.py::test_category_parent_option_label_summarizes_category_identity tests/test_frontend_api.py::test_category_parent_option_label_handles_malformed_category_items tests/test_api.py::test_streamlit_config_tab_uses_category_parent_option_label_helper tests/test_api.py::test_streamlit_config_category_parent_options_skip_malformed_items tests/test_api.py::test_streamlit_config_create_errors_show_payload_details -q` 通过，6 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1214 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1214 passed`。
