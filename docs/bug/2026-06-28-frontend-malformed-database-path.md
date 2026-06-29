# Frontend database path display crashed on malformed status field

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.database_path`，但该字段缺失、为空字符串或不是字符串。
- 实际结果：侧边栏直接访问 `status["database_path"]`；字段缺失时会抛出 `KeyError`，异常值也会被当成正常 DB 路径显示，影响后续外部能力、存储健康和配置提示诊断。
- 期望结果：malformed `database_path` 应显示为 `database_path: invalid` warning，而不是中断侧边栏诊断或展示误导性路径。

## 原因

- 根因：`streamlit_app.py` 将 `/system/status.database_path` 当作必然存在的非空字符串直接索引，没有通过展示层 helper 做类型防线。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的数据库路径和后续诊断信号。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `database_path_status_row()`；非空字符串显示为 `DB: <path>`，缺失、空字符串或非字符串显示为 `database_path: invalid` warning；Streamlit 侧边栏改为按 helper 返回的 caption/warning 行渲染。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_database_path_status_row_blocks_malformed_database_path tests/test_api.py::test_streamlit_sidebar_uses_safe_database_path_status -q` 失败，分别表现为 helper 缺失和 sidebar 仍未使用安全 DB path helper。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_database_path_status_row_blocks_malformed_database_path tests/test_api.py::test_streamlit_sidebar_uses_safe_database_path_status -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`95 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_uses_safe_database_path_status tests/test_api.py::test_streamlit_sidebar_exposes_runtime_status tests/test_api.py::test_streamlit_sidebar_exposes_external_capability_status -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1152 passed`。
