# Blank optional config suppressed missing capability warnings

## 现象

- 触发命令、接口或页面：启动环境里设置 `OPENALEX_MAILTO="   "`、`UNPAYWALL_EMAIL="   "` 或 `LLM_API_KEY="   "` 后访问 `/api/v1/system/status`。
- 实际结果：空白字符串被当成已配置，`config_warnings` 不再提示缺失外部能力，`external_capabilities` 也把对应能力标成 true，LLM 翻译链路显示为 `openai-compatible`。
- 期望结果：空白可选配置应等同于未配置；系统状态页和 health summary 应继续提示缺失能力，并保持离线 `local-echo` 适配器。

## 原因

- 根因：`app/config.py` 没有对可选 secret/config 字段做 trim 和空白归一化，后续 `bool(settings.llm_api_key)` 等判断把空白字符串视为 truthy。
- 影响范围：配置诊断、发布健康检查、OpenAlex/Crossref/Unpaywall 请求标识、翻译/分类适配器选择。

## 修复

- 修改文件：`app/config.py`、`tests/test_api.py`。
- 关键行为：`Settings` 读取 `OPENALEX_MAILTO`、`UNPAYWALL_EMAIL`、`LLM_API_KEY` 时先 trim；trim 后为空则归一化为 `None`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_status_treats_blank_optional_config_as_missing -q` 失败，当前实现的 `config_warnings` 是空集合。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_system_status_treats_blank_optional_config_as_missing tests/test_api.py::test_system_status_reports_missing_optional_config_without_blocking tests/test_api.py::test_system_status_reports_translation_adapter tests/test_api.py::test_system_status_reports_release_readiness -q` 通过，`4 passed`；配置和 health 相关 focused 测试通过，`4 passed` 与 `22 passed, 391 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`847 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `847 passed`。
