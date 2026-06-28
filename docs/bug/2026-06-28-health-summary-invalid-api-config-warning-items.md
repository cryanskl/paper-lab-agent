# Health summary ignored invalid API config warning code items

## 现象

- 触发命令、接口或页面：`python scripts/health_check.py --summary-only --compact` 消费 `/api/v1/system/status`，响应中 `release_readiness.ready=true`，但 `release_readiness.config_warning_codes` 列表内包含非字符串元素，例如 `[false]`。
- 实际结果：health summary 把非字符串元素转成普通字符串 `"False"`，不会作为 blocking config warning，可能输出 `release_ready=true`。
- 期望结果：API 聚合的配置告警列表元素形状异常时，summary 应标记为不可发布，避免 malformed config warning 被误判为普通非阻断 warning。

## 原因

- 根因：`scripts/health_check.py` 的 `list_values()` 对 list 内元素直接 `str(item)`，只过滤空白字符串；当 `invalid_label` 已提供时也没有把非字符串元素归一为 `invalid`。
- 影响范围：发布前 compact summary、`--require-release-ready` 错误定位前的 stdout 摘要、异常 API 响应的配置诊断信号。

## 修复

- 修改文件：`scripts/health_check.py`、`tests/test_api.py`。
- 关键行为：当 `api_release_readiness()` 解析列表字段时，非空字符串以外的元素会加入 `invalid` sentinel；对 `config_warning_codes` 会输出 `config_warning_codes:invalid` blocker。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_summary_blocks_invalid_api_config_warning_code_items -q` 失败，summary 实际为 `release_ready=true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_summary_blocks_invalid_api_config_warning_code_items tests/test_api.py::test_health_check_summary_blocks_malformed_api_config_warning_codes tests/test_api.py::test_health_check_summary_blocks_malformed_api_release_readiness_lists -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1137 passed`。
