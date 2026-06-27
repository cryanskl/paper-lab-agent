# Export release artifacts ignored OpenAPI write failures

## 现象

- 触发命令、接口或页面：`scripts/export_release_artifacts.py --output-dir <dir>` 在内部写入 `openapi.json` 时遇到 `write_openapi()` 返回错误。
- 实际结果：导出流程忽略 `write_openapi()` 的错误返回，继续准备 demo summary 和 manifest，随后读取不存在的 `openapi.json` 时抛出异常。
- 期望结果：OpenAPI artifact 写入失败时返回结构化 `ok:false` report，并且不继续生成后续 handoff 文件。

## 原因

- 根因：`scripts/export_openapi.py` 改为用返回字符串报告输出路径错误后，`scripts/export_release_artifacts.py` 仍按旧的无返回值接口调用 `write_openapi()`，没有检查错误返回值。

## 修复

- 关键行为：`export_release_artifacts()` 写入 OpenAPI artifact 后检查 `write_openapi()` 返回值；非空时返回 `OpenAPI artifact write failed` issue，并停止写入 `demo-summary.json` 和 `release-manifest.json`。
- 影响范围：只改变 OpenAPI artifact 写入失败时的失败路径；正常 release handoff bundle 生成保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_openapi_write_failure -q` 失败，当前实现抛出 `FileNotFoundError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_openapi_write_failure tests/test_release_contracts.py::test_export_release_artifacts_script_writes_handoff_bundle -q` 通过，`2 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "export_release_artifacts"` 通过，`9 passed, 228 deselected`。
- 全量验证：`.venv/bin/python -m pytest -q` 通过，`787 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `787 passed`。
