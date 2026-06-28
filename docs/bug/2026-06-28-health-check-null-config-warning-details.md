# health_check 误拒绝空的配置 warning 详情

## 现象

- 触发命令、接口或页面：live API 启动后运行 `API_BASE_URL=http://127.0.0.1:8765/api/v1 .venv/bin/python scripts/health_check.py --summary-only --compact`
- 实际结果：命令返回 1，并报告 `config_warnings invalid values: 0.actual, 0.supported, 1.actual, 1.supported, 2.actual, 2.supported`
- 期望结果：`actual` 和 `supported` 是配置 warning 的可选详情，API 返回 `null` 时不应导致 system status shape 校验失败

## 原因

- 根因：`scripts/health_check.py` 的 `validate_system_status()` 只允许可选字段缺省，未允许 Pydantic 响应中常见的 `actual: null` 和 `supported: null`
- 影响范围：未配置 OpenAlex、Unpaywall 或 LLM key 的 live 环境中，`health_check.py --summary-only --compact` 会在摘要已可生成的情况下误返回失败

## 修复

- 修改文件：`scripts/health_check.py`
- 关键行为：`actual` 和 `supported` 为 `None` 时跳过可选详情校验；字段存在且非空值时仍要求 `actual` 为非空字符串、`supported` 为非空字符串列表

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py -q -k "allows_null_optional_config_warning_details or rejects_invalid_config_warning_detail_shape"` 曾失败，提示 `config_warnings invalid values: 0.actual, 0.supported`
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py -q -k "allows_null_optional_config_warning_details or rejects_invalid_config_warning_detail_shape"` 通过
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`1092 passed`
