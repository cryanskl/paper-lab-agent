# Health summary ignored malformed API config warning codes

## 现象

- 触发命令、接口或页面：`python scripts/health_check.py --summary-only --compact` 消费 `/api/v1/system/status`，响应中 `release_readiness.ready=true`，但 `release_readiness.config_warning_codes` 不是列表。
- 实际结果：health summary 把 malformed `config_warning_codes` 静默归一为空列表，可能输出 `release_ready=true` 和 `config_ready=true`。
- 期望结果：API 聚合的配置告警字段形状异常时，summary 应标记为不可发布，避免 unsupported adapter 等阻断性配置状态被误判。

## 原因

- 根因：`scripts/health_check.py` 的 `api_release_readiness()` 对 `config_warning_codes` 使用默认 `list_values()`；非列表字段会返回 `[]`。同时 `release_readiness_blockers()` 只阻断已知 blocking warning code，无法表达字段本身 malformed。
- 影响范围：发布前 compact summary、`--require-release-ready` 错误定位前的 stdout 摘要、异常 API 响应的配置诊断信号。

## 修复

- 修改文件：`scripts/health_check.py`、`tests/test_api.py`。
- 关键行为：API `release_readiness.config_warning_codes` 非列表时，summary 会加入 `config_warning_codes:invalid` blocker，并输出 `release_ready=false`、`config_ready=false`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_summary_blocks_malformed_api_config_warning_codes -q` 失败，summary 实际为 `release_ready=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_summary_blocks_malformed_api_config_warning_codes tests/test_api.py::test_health_check_summary_surfaces_blocking_config_warnings tests/test_api.py::test_health_check_summary_blocks_malformed_api_release_readiness_lists -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1136 passed`。
