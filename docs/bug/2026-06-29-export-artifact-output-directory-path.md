# Release artifact exporter misreported directory artifact outputs

## 现象

- 触发命令、接口或页面：调用 `export_release_artifacts()` 或运行 `scripts/export_release_artifacts.py --output-dir <dir>`，且 `<dir>/openapi.json`、`demo-summary.json` 或 `release-manifest.json` 已存在为目录。
- 实际结果：导出流程报告 `release artifact output path is not a file: <path>`，和 artifact 输出路径为 symlink 时的 `release artifact output path is not a regular file` 诊断不一致。
- 期望结果：目录、symlink 等非普通文件 artifact 输出路径统一报告 `release artifact output path is not a regular file: <path>`，便于 release handoff 自动化稳定匹配路径类型错误。

## 原因

- 根因：`export_release_artifacts()` 在检查目标目录内预期 artifact 输出路径时，symlink 分支使用 `not a regular file`，但已存在目录分支使用 `not a file`。
- 影响范围：release artifact 导出失败时，同类非普通文件路径错误分类不一致，增加 CI 和人工排障成本。

## 修复

- 修改文件：`scripts/export_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：预期 artifact 输出路径已存在但不是普通文件时统一返回 `release artifact output path is not a regular file`；artifact symlink、broken symlink、正常 handoff bundle 和单命令 handoff 行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_rejects_expected_artifact_directory_path -q` 失败，当前实现输出 `release artifact output path is not a file`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_export_release_artifacts_rejects_expected_artifact_directory_path tests/test_release_contracts.py::test_export_release_artifacts_rejects_expected_artifact_symlink tests/test_release_contracts.py::test_export_release_artifacts_rejects_broken_expected_artifact_symlink tests/test_release_contracts.py::test_export_release_artifacts_script_writes_handoff_bundle tests/test_release_contracts.py::test_build_release_handoff_script_exports_validates_packages_and_revalidates -q` 通过，5 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1251 passed。
