# Frontend demo data display crashed on malformed object

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.demo_data`，但该字段不是对象而是非空列表或字符串。
- 实际结果：侧边栏直接调用 `demo_data.get("ready")` 和 `demo_data.get("missing")`，会抛出 `AttributeError`，演示数据状态无法显示。
- 期望结果：malformed `demo_data` 顶层对象应作为 walking skeleton 未就绪状态展示，而不是让侧边栏崩溃。

## 原因

- 根因：`streamlit_app.py` 只用 `status.get("demo_data") or {}` 处理缺失或空值；非空 list/string 会原样进入 `.get()` 调用，没有前端展示层的类型防线。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的演示数据诊断信号。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `demo_data_display_state()`，先校验 `demo_data` 顶层对象；非 dict 时返回 `demo_data:invalid`，并让 Streamlit 侧边栏通过该 helper 渲染 walking skeleton 状态。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_demo_data_display_state_blocks_malformed_demo_data_object tests/test_api.py::test_streamlit_sidebar_surfaces_demo_data_readiness -q` 失败，分别表现为 helper 缺失和 sidebar 未使用 `demo_data_display_state`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_demo_data_display_state_blocks_malformed_demo_data_object tests/test_api.py::test_streamlit_sidebar_surfaces_demo_data_readiness -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`87 passed`；`.venv/bin/python -m pytest tests/test_api.py -q -k "streamlit_sidebar"` 通过，`12 passed, 554 deselected`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1142 passed`。
