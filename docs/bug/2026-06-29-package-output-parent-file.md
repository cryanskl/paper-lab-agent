# Release package builder misreported file output parents

## 现象

- 触发命令、接口或页面：运行 `scripts/package_release_artifacts.py --artifact-dir <dir> --output <parent>/paper-lab-agent-release.zip`，且 `<parent>` 是普通文件。
- 实际结果：打包流程报告 `release package output parent is not a directory: <parent>`，和输出父级 symlink 的 `release package output parent is not a regular directory` 诊断不一致。
- 期望结果：文件、symlink 等非普通目录输出父路径统一报告 `release package output parent is not a regular directory: <parent>`，便于 CI 和交付脚本稳定匹配路径类型错误。

## 原因

- 根因：`package_release_artifacts()` 对存在但不是目录的输出父路径使用了单独的 `is not a directory` 文案。
- 影响范围：release package 生成失败时，输出父路径为文件和父路径为 symlink 的错误分类不一致，增加自动化诊断和人工排查成本。

## 修复

- 修改文件：`scripts/package_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：存在但不是普通目录的 release package 输出父路径统一返回 `release package output parent is not a regular directory`；输出路径目录、输出 symlink、父目录 symlink 和输出位于 artifact 目录内的既有行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_rejects_file_output_parent -q` 失败，当前实现输出 `release package output parent is not a directory`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_rejects_file_output_parent tests/test_release_contracts.py::test_package_release_artifacts_rejects_directory_output_path tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_symlink tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_parent_symlink tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_ancestor_symlink tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_inside_artifact_dir -q` 通过，6 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1249 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1249 passed。
