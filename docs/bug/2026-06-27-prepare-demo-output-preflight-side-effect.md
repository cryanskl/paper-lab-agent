# Prepare demo data mutated storage before output preflight

## 现象

- 触发命令、接口或页面：运行 `scripts/prepare_demo_data.py --summary-only --compact --output <path>`，其中 `<path>` 是 symlink 或其他非法输出路径。
- 实际结果：脚本最终返回失败，但在拒绝输出路径之前已经导入 fixture、初始化数据库、写入 PDF/TEI/translation/export 等 demo 数据。
- 期望结果：`--output` 路径明显非法时应在任何 demo 数据准备之前失败，不创建 `PAPER_LAB_DATA_DIR`，避免失败的 release 命令留下半成品状态。

## 原因

- 根因：`main()` 先调用 `prepare_demo_data()`，之后才通过 `write_output_file()` 检查 `--output` 是否安全。
- 影响范围：发布前 walking skeleton 准备脚本、release gate 临时目录、人工执行 `--output` 失败后的本地数据目录整洁性。

## 修复

- 修改文件：`scripts/prepare_demo_data.py`、`tests/test_api.py`。
- 关键行为：拆出 `output_path_error()` 作为无副作用预检；`main()` 在调用 `prepare_demo_data()` 前先拒绝 symlink、symlink parent 和非普通输出文件，`write_output_file()` 继续复用同一规则。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_prepare_demo_data_script_rejects_symlinked_output_file -q` 失败，非法输出路径返回失败但仍创建了 `data` 目录。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_prepare_demo_data_script_rejects_symlinked_output_file tests/test_api.py::test_prepare_demo_data_script_can_write_summary_output_file tests/test_api.py::test_prepare_demo_data_script_rejects_symlinked_output_parent -q` 通过，`3 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`866 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `866 passed`。
