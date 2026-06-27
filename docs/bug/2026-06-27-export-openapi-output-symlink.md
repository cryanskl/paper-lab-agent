# Export OpenAPI followed output file symlinks

## 现象

- 触发命令、接口或页面：`scripts/export_openapi.py --output <path>`，其中 `<path>` 是指向目录外文件的 symlink。
- 实际结果：脚本跟随 symlink 写入目标文件，并返回成功。
- 期望结果：`--output` 必须拒绝 symlink 或非普通文件，避免 OpenAPI handoff artifact 写到用户指定路径之外。

## 原因

- 根因：`scripts/export_openapi.py` 在处理 `--output` 时直接调用 `Path.write_text()`。`write_text()` 会跟随 symlink，因此指向普通文件的 symlink 被当成安全输出路径。

## 修复

- 关键行为：`write_openapi()` 写入前先拒绝 symlink 和非普通文件；命中时返回 `export_openapi failed: output path is not a regular file`，并且不改写 symlink 目标文件。
- 影响范围：只改变 `--output` 指向 symlink 或非普通文件时的失败行为；普通 OpenAPI JSON 输出文件创建和写入保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_openapi_script_rejects_symlinked_output_file -q` 失败，当前实现返回 `0` 并接受 symlink 输出路径。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_openapi_script_rejects_symlinked_output_file tests/test_release_contracts.py::test_export_openapi_script_runs_as_file tests/test_release_contracts.py::test_export_openapi_script_writes_publishable_schema -q` 通过，`3 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "export_openapi"` 通过，`3 passed, 232 deselected`。
- 全量验证：`.venv/bin/python -m pytest -q` 通过，`785 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `785 passed`。
