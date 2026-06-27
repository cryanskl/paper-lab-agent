# Export release artifacts leaked JSON write failures

## 现象

- 触发命令、接口或页面：`scripts/export_release_artifacts.py --output-dir <dir>` 在内部写入 `demo-summary.json` 或 `release-manifest.json` 时遇到文件系统写入错误。
- 实际结果：`write_json()` 抛出的 `OSError` 直接冒泡，CLI 输出 traceback，而不是 release handoff 可消费的结构化失败报告。
- 期望结果：demo summary 或 manifest 写入失败时返回结构化 `ok:false` report，并说明具体失败的 artifact。

## 原因

- 根因：`scripts/export_release_artifacts.py` 只把 `openapi.json` 写入失败转换为结构化 `issues`，但后续两个 `write_json()` 调用仍按不会失败的路径处理。

## 修复

- 关键行为：`export_release_artifacts()` 捕获 `demo-summary.json` 和 `release-manifest.json` 写入时的 `OSError`，分别返回 `Demo summary artifact write failed` 和 `Release manifest artifact write failed`。
- 影响范围：只改变 release handoff bundle 写入失败时的失败路径；正常 artifact 内容、manifest 字段和 checksum 逻辑保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_demo_summary_write_failure tests/test_release_contracts.py::test_export_release_artifacts_reports_manifest_write_failure -q` 失败，当前实现直接抛出 `OSError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_demo_summary_write_failure tests/test_release_contracts.py::test_export_release_artifacts_reports_manifest_write_failure -q` 通过，`2 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "export_release_artifacts"` 通过，`11 passed, 228 deselected`。
- 全量验证：`.venv/bin/python -m pytest -q` 通过，`789 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `789 passed`。
