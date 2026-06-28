# Release artifact validator 未校验 OpenAPI 交接元数据

## 现象

`scripts/validate_release_artifacts.py` 只校验 OpenAPI title 和 `/api/v1/health` 基础路径。若 handoff artifact 中的 `openapi.json` 缺少 `system` tag metadata 或统一错误响应模型 `ErrorResponse`，validator 仍可能返回 `ok: true`。

## 原因

OpenAPI 交接契约在 `scripts/release_check.sh` 和 live `health_check.py --require-openapi` 中已经覆盖 `system` tag 与 `ErrorResponse` schema，但 artifact validator 没有复用这两条检查，导致离线 handoff package 校验比发布 gate 弱。

## 修复

在 `scripts/validate_release_artifacts.py` 的 OpenAPI 校验中加入 `system` tag metadata 与 `ErrorResponse` schema 检查。同步更新 README 和 release checklist，使文档描述与实际 handoff validator 一致。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_requires_handoff_openapi_metadata -q` 失败，`report["issues"]` 为空。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_requires_handoff_openapi_metadata -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_script_accepts_handoff_bundle tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle -q` 通过，`2 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`743 passed`。
