# Streamlit release readiness blocked config warnings

## 现象

- 触发命令、接口或页面：默认离线配置下打开 Streamlit 侧边栏查看“发布就绪”状态。
- 实际结果：API 已把 `config_warning_codes` 定义为非阻断提示，但 Streamlit 仍把它加入 `release blockers`，导致页面把缺少 OpenAlex、Unpaywall 或 LLM key 展示为发布阻断。
- 期望结果：Streamlit 的发布阻断列表只展示 demo data、失败/拒绝工作流和存储错误；配置缺失继续在“配置提示”区域展示。

## 原因

- 根因：`streamlit_app.py` 的 `blocker_groups` 仍包含 `config_warning_codes`，没有跟随 API 与 `scripts/health_check.py` 的 release readiness 语义更新。

## 修复

- 关键行为：从 Streamlit release blocker 分组中移除 `config_warning_codes`；保留已有 `config_warnings` 展示逻辑，继续提示外部能力配置状态。
- 影响范围：只改变侧边栏“发布就绪”阻断判断；配置提示区域、API 状态读取和其他页面功能保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_surfaces_release_readiness -q` 失败，当前 sidebar 的 `blocker_groups` 仍包含 `config_warning_codes`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_surfaces_release_readiness tests/test_api.py::test_streamlit_sidebar_surfaces_config_warnings -q` 通过，`2 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_api.py -q -k "streamlit_sidebar"` 通过，`11 passed, 386 deselected`。
- 全量验证：首次 `.venv/bin/python -m pytest -q` 失败，原因是本 bug 文档引用 health check 脚本时未写成可解析路径；修正为 `scripts/health_check.py` 后重跑通过，`792 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `792 passed`。
