# Reaction export misclassified malformed reaction JSON as not found

## 现象

- 触发命令、接口或页面：`POST /api/v1/reaction-sets/{id}/export?format=json`，且该 reaction set 已存在、已复核，但库内 `reactants` JSON 损坏。
- 实际结果：接口返回 `404 reaction_set_not_found`，把损坏的化学库导出数据误报成反应集不存在。
- 期望结果：已存在 reaction set 的导出解析失败应返回 `500 reaction_export_failed`，保留真实排障原因。

## 原因

- 根因：`app/routers/reactions.py` 的导出路由捕获 `export_reaction_set()` 的所有非格式类 `ValueError` 并统一映射为 `reaction_set_not_found`；`reaction_set_detail()` 解析损坏 JSON 时抛出的 `json.JSONDecodeError` 也是 `ValueError` 子类。
- 影响范围：化学库导出接口和发布前排障；损坏的反应数据会被误判为 missing reaction set。

## 修复

- 修改文件：`app/routers/reactions.py`、`tests/test_api.py`。
- 关键行为：只有明确的 `reaction set not found` 继续映射为 `404 reaction_set_not_found`；其它非格式类 `ValueError` 作为 `500 reaction_export_failed` 返回。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_reaction_export_malformed_reaction_json_returns_backend_error -q` 失败，实际返回 `404`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_reaction_export_malformed_reaction_json_returns_backend_error tests/test_api.py::test_reaction_export_bolsig_text_and_rejects_unknown_format tests/test_api.py::test_reaction_export_text_formats_include_per_reaction_audit_summary tests/test_api.py::test_reaction_export_rejects_empty_reaction_set -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1129 passed`。
