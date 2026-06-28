# Health check wrote output for invalid status payload

## 现象

- 触发命令、接口或页面：运行 `scripts/health_check.py --output <path>`，且 `/api/v1/system/status` 返回缺少必需字段的无效结构。
- 实际结果：脚本最终返回失败，但已经把无效状态响应写入 `<path>`，下游 release artifact 或人工检查可能误把该文件当成可用健康报告。
- 期望结果：基础 health/status 结构校验失败时不写 `--output` 文件；只有基础结构可信后，才允许输出诊断 JSON。

## 原因

- 根因：`scripts/health_check.py` 在 `validate_system_status()` 和 health 响应基础校验之前执行 `write_output_file()`。
- 影响范围：发布前健康检查、`--output` 产物、依赖健康报告文件的 release gate 和人工验收。

## 修复

- 修改文件：`scripts/health_check.py`、`tests/test_api.py`。
- 关键行为：将 `--output` 写入延后到 health 响应对象、服务名、状态值以及 system status schema 校验通过之后；后续 release-ready、frontend、OpenAPI、GROBID 等可选 gate 失败时仍保留输出诊断 JSON 的能力。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_does_not_write_output_when_status_shape_is_invalid -q` 失败，`health.json` 被写出。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_does_not_write_output_when_status_shape_is_invalid -q` 通过，`1 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`866 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `866 passed`。
