# Frontend system count metrics crashed on malformed counts

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.counts`，但 `counts` 不是对象，或 `journals` / `papers` / `documents` 不是非负整数。
- 实际结果：侧边栏直接访问 `status["counts"]["journals"]`、`papers`、`documents`；顶层缺失或形状漂移时会在最前面的系统指标处崩溃，后续发布就绪、存储健康和配置提示都无法显示。
- 期望结果：malformed counts 应显示为 `counts: invalid` 或 `counts.<key>: invalid` warning，而不是中断侧边栏诊断。

## 原因

- 根因：`streamlit_app.py` 将 `/system/status.counts` 当作稳定 dict 直接索引，没有像 release readiness、demo data、storage health 一样通过展示层 helper 做类型防线。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的基础系统指标和后续诊断信号。

## 修复

- 修改文件：`app/frontend_api.py`、`streamlit_app.py`、`tests/test_frontend_api.py`、`tests/test_api.py`。
- 关键行为：新增 `system_count_metric_rows()`；顶层非 dict 时输出 `系统计数=invalid` 和 `counts: invalid` warning，单个计数字段不是非布尔非负整数时输出对应字段的 invalid warning；Streamlit 侧边栏改为通过 helper 渲染指标。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_system_count_metric_rows_blocks_malformed_counts_objects tests/test_api.py::test_streamlit_sidebar_uses_safe_system_count_metrics -q` 失败，分别表现为 helper 缺失和 sidebar 仍未使用安全 metrics helper。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_system_count_metric_rows_blocks_malformed_counts_objects tests/test_api.py::test_streamlit_sidebar_uses_safe_system_count_metrics -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`93 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_exposes_runtime_status tests/test_api.py::test_streamlit_sidebar_uses_safe_system_count_metrics -q` 通过，`2 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1149 passed`。
