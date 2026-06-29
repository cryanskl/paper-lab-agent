# Release package builder misreported directory output paths

## 现象

- 触发命令、接口或页面：运行 `scripts/package_release_artifacts.py --artifact-dir <dir> --output <path>`，且 `<path>` 已被错误创建成目录。
- 实际结果：打包流程报告 `release package output is not a file: <path>`，和输出 symlink 的 `release package output is not a regular file` 诊断不一致。
- 期望结果：目录、symlink 等非普通文件输出路径统一报告 `release package output is not a regular file: <path>`，便于 CI 和交付脚本稳定匹配路径类型错误。

## 原因

- 根因：`package_release_artifacts()` 在解析输出路径后对存在但不是普通文件的输出路径使用了单独的 `is not a file` 文案。
- 影响范围：release package 生成失败时，输出目录和输出 symlink 的错误分类不一致，增加自动化诊断和人工排查成本。

## 修复

- 修改文件：`scripts/package_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：存在但不是普通文件的 release package 输出路径统一返回 `release package output is not a regular file`；输出 symlink、父目录 symlink、父目录为文件和输出位于 artifact 目录内的既有行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_rejects_directory_output_path -q` 失败，当前实现输出 `release package output is not a file`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_rejects_directory_output_path tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_symlink tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_parent_symlink tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_ancestor_symlink tests/test_release_contracts.py::test_package_release_artifacts_reports_output_parent_not_directory tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_inside_artifact_dir -q` 通过，6 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1249 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1249 passed。
