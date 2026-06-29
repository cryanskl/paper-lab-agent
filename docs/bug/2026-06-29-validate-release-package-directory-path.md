# Release package validator misreported directory package paths

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_release_package.py --package <path>`，且 `<path>` 被错误创建成目录。
- 实际结果：validator 报告 `release package is not a file: <path>`，和 symlink package 输入的 `is not a regular file` 诊断不一致。
- 期望结果：目录、symlink 等非普通文件 package 输入统一报告 `release package is not a regular file: <path>`，便于 CI 和交付脚本稳定匹配路径类型错误。

## 原因

- 根因：`validate_release_package()` 在解析路径后对存在但不是普通文件的 package 使用了单独的 `is not a file` 文案。
- 影响范围：发布 handoff zip 校验失败时，目录输入和 symlink 输入的错误分类不一致，增加自动化诊断和人工排查成本。

## 修复

- 修改文件：`scripts/validate_release_package.py`、`tests/test_release_contracts.py`。
- 关键行为：存在但不是普通文件的 package 路径统一返回 `release package is not a regular file`；坏 zip、读取失败、package symlink 和父目录 symlink 的既有行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_directory_package_path -q` 失败，当前实现输出 `release package is not a file`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_directory_package_path tests/test_release_contracts.py::test_validate_release_package_reports_zip_read_failure tests/test_release_contracts.py::test_validate_release_package_rejects_package_symlink tests/test_release_contracts.py::test_validate_release_package_rejects_package_parent_symlink tests/test_release_contracts.py::test_validate_release_package_rejects_package_ancestor_symlink tests/test_release_contracts.py::test_validate_release_package_script_rejects_tampered_zip_artifact -q` 通过，6 passed。
- 完整 pytest：`.venv/bin/python -m pytest -q` 通过，1249 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1249 passed。
