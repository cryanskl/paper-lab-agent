# Reaction verify misclassified malformed reaction JSON as not found

## 现象

- 触发命令、接口或页面：`PUT /api/v1/reactions/{id}/verify`，且该 reaction 已存在但库内 `reactants` JSON 损坏。
- 实际结果：接口返回 `404 reaction_not_found`，把损坏的反应数据误报成资源不存在。
- 期望结果：已存在 reaction 的后端数据解析失败应返回 `500 reaction_verify_failed`，暴露真实排障原因。

## 原因

- 根因：`app/routers/reactions.py` 捕获 `verify_reaction()` 的所有 `ValueError` 并统一映射为 `reaction_not_found`；`json.JSONDecodeError` 是 `ValueError` 子类，因此 `reaction_set_detail()` 解析损坏 JSON 时也被误分类。
- 影响范围：人工复核接口的错误诊断；损坏的化学库数据会被误判为 missing reaction，影响发布前排障。

## 修复

- 修改文件：`app/routers/reactions.py`、`tests/test_api.py`。
- 关键行为：只有明确的 `reaction not found` 继续映射为 `404 reaction_not_found`；其它 `ValueError` 作为 `500 reaction_verify_failed` 返回。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_reaction_verify_malformed_reaction_json_returns_backend_error -q` 失败，实际返回 `404`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_reaction_verify_malformed_reaction_json_returns_backend_error tests/test_api.py::test_reaction_verify_backend_failure_returns_json_error tests/test_api.py::test_reaction_verify_updates_fields_and_records_audit -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1128 passed`。
