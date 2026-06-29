# Release artifact exporter crashed on file output parents

## 现象

- 触发命令、接口或页面：调用 `export_release_artifacts()` 或运行 `scripts/export_release_artifacts.py --output-dir <parent>/release`，且 `<parent>` 是普通文件。
- 实际结果：导出流程在 `output_dir.mkdir(parents=True)` 抛出 `NotADirectoryError`，单命令 handoff 的 artifact export 阶段无法返回结构化 JSON report。
- 期望结果：父级路径已存在但不是普通目录时，返回 `{ "ok": false, ... }`，并报告 `release artifact output directory parent is not a regular directory: <parent>`。

## 原因

- 根因：`export_release_artifacts()` 只检查输出目录本身是否为非目录，以及父级链是否包含 symlink；没有在创建目录前检查已存在但不是目录的父路径。
- 影响范围：release handoff artifact 导出和 `scripts/build_release_handoff.py` 的第一步在路径结构错误时可能以异常退出，降低发布排障可诊断性。

## 修复

- 修改文件：`scripts/export_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：在 `mkdir(parents=True)` 前拒绝已存在但不是目录的输出父路径，返回结构化 issue；输出目录本身为文件、输出目录 symlink、父级 symlink、祖先 symlink、正常 handoff bundle 和单命令 handoff 行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_rejects_file_output_parent -q` 失败，当前实现抛出 `NotADirectoryError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_rejects_file_output_parent tests/test_release_contracts.py::test_export_release_artifacts_reports_output_dir_not_directory tests/test_release_contracts.py::test_export_release_artifacts_rejects_output_dir_symlink tests/test_release_contracts.py::test_export_release_artifacts_rejects_output_dir_symlink_parent tests/test_release_contracts.py::test_export_release_artifacts_rejects_output_dir_symlink_ancestor tests/test_release_contracts.py::test_export_release_artifacts_script_writes_handoff_bundle tests/test_release_contracts.py::test_build_release_handoff_script_exports_validates_packages_and_revalidates -q` 通过，7 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1251 passed。
