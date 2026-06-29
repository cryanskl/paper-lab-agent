# prepare_demo_data output file parent reported generic write failure

## 现象

- 触发命令、接口或页面：`python scripts/prepare_demo_data.py --summary-only --compact --output <file-parent>/demo-summary.json`，其中 `<file-parent>` 已存在且是普通文件。
- 实际结果：CLI 返回非零，但错误信息是泛化的 `failed to write output file ... Not a directory`。
- 期望结果：CLI 应在准备 demo data 前拒绝已存在但不是目录的输出父路径，并返回 `output path parent is not a regular directory: <file-parent>`。

## 原因

- 根因：`scripts/prepare_demo_data.py` 的 `output_path_error` 只检查输出文件 symlink、父级 symlink 和输出路径是否为普通文件，随后 `write_output_file` 直接 `mkdir(parents=True)`；父路径是普通文件时只能从 `OSError` 生成泛化写入失败。
- 影响范围：发布或演示前用 `--output out/demo-summary.json` 生成 demo summary artifact 时，如果 `out` 被误建为普通文件，错误信息不够明确。

## 修复

- 修改文件：`scripts/prepare_demo_data.py`、`tests/test_api.py`
- 关键行为：`output_path_error` 在运行 demo data 准备前检查 `path.parent.exists() and not path.parent.is_dir()`，并返回明确的父路径错误；新增回归测试覆盖普通文件父路径。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_prepare_demo_data_script_rejects_file_output_parent -q` -> `1 failed`
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_prepare_demo_data_script_rejects_file_output_parent tests/test_api.py::test_prepare_demo_data_script_rejects_symlinked_output_parent tests/test_api.py::test_prepare_demo_data_script_rejects_symlinked_output_file tests/test_api.py::test_prepare_demo_data_script_can_write_summary_output_file -q` -> `4 passed`
- 完整 gate：`bash scripts/release_check.sh` -> `1102 passed`
