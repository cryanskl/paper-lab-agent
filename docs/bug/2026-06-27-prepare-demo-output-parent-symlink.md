# Prepare demo data followed output parent symlinks

## 现象

- 触发命令、接口或页面：`scripts/prepare_demo_data.py --summary-only --compact --output <path>`，其中 `<path>` 的父目录是指向目录外位置的 symlink。
- 实际结果：脚本把 walking skeleton 演示摘要写入 symlink 父目录指向的目标目录，并返回成功。
- 期望结果：`--output` 必须拒绝父目录链中包含 symlink 的路径，避免演示摘要写到用户指定路径树之外。

## 原因

- 根因：`scripts/prepare_demo_data.py` 只检查输出文件本身是否是 symlink，没有检查原始输出路径的父目录链；随后 `Path.write_text()` 会跟随 symlink 父目录写入目标目录。

## 修复

- 关键行为：新增 `first_symlink_parent()`，在写入前扫描 `--output` 的原始父级链；命中任一非系统根级 symlink 父目录时返回 `prepare_demo_data failed: output path parent is not a regular directory`，并且不写入目标目录。
- 影响范围：只改变 `--output` 父级链含 symlink 时的失败行为；普通输出文件和已存在普通文件写入保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_prepare_demo_data_script_rejects_symlinked_output_parent -q` 失败，当前实现返回 `0` 并写入 symlink 父目录目标。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_prepare_demo_data_script_rejects_symlinked_output_parent tests/test_api.py::test_prepare_demo_data_script_rejects_symlinked_output_file tests/test_api.py::test_prepare_demo_data_script_can_write_summary_output_file -q` 通过，`3 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_api.py -q -k "prepare_demo_data"` 通过，`5 passed, 391 deselected`。
- 全量验证：`.venv/bin/python -m pytest -q` 通过，`784 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `784 passed`。
