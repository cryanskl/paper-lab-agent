# Frontend config warnings display crashed on malformed objects

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.config_warnings`，但该字段不是列表，或列表内包含非对象元素。
- 实际结果：侧边栏直接遍历 `config_warnings` 并调用 `warning.get(...)`，会抛出 `AttributeError`，配置提示诊断无法显示。
- 期望结果：malformed `config_warnings` 顶层对象或列表元素应作为 `config_warnings: invalid` warning 展示，而不是让侧边栏崩溃。

## 原因

- 根因：`streamlit_app.py` 直接在页面代码里展开 `config_warnings`，假设顶层是 list 且每个元素都是 dict，没有展示层类型防线。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的配置提示诊断信号。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `config_warning_rows()`；顶层非 list 或列表元素非 dict 时返回 `{"capability": "config_warnings", "message": "invalid"}`，并让 Streamlit 侧边栏通过该 helper 渲染配置提示。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_config_warning_rows_blocks_malformed_config_warning_objects tests/test_api.py::test_streamlit_sidebar_surfaces_config_warnings -q` 失败，分别表现为 helper 缺失和 sidebar 仍直接遍历 `config_warnings`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_config_warning_rows_blocks_malformed_config_warning_objects tests/test_api.py::test_streamlit_sidebar_surfaces_config_warnings -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`91 passed`；`.venv/bin/python -m pytest tests/test_api.py -q -k "streamlit_sidebar"` 通过，`12 passed, 554 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1146 passed`。
