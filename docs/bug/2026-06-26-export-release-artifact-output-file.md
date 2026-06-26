# Export release artifacts 输出路径为文件会崩溃

## 现象

如果 `scripts/export_release_artifacts.py --output-dir` 指向一个已经存在的文件，脚本会直接抛出异常并输出 traceback，而不是返回结构化 JSON 错误报告。

## 原因

`export_release_artifacts()` 直接调用 `output_dir.mkdir(parents=True, exist_ok=True)`。当目标路径已经是普通文件时，`Path.mkdir()` 会抛出 `FileExistsError`，CLI 没有机会按 release 工具约定输出 JSON report。

## 修复

在创建目录前先判断 `output_dir.exists() and not output_dir.is_dir()`。命中时返回 `{ "ok": false, "output_dir": "...", "issues": [...] }`，CLI 输出该 JSON 并以退出码 1 结束；成功路径继续输出原有 release manifest。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_output_dir_not_directory -q` 失败，stdout 为空且无法解析 JSON。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_reports_output_dir_not_directory -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_script_writes_handoff_bundle tests/test_release_contracts.py::test_export_release_artifacts_reports_output_dir_not_directory tests/test_release_contracts.py::test_validate_release_artifacts_script_accepts_handoff_bundle tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `751 passed`。
