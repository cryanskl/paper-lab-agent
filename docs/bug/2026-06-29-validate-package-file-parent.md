# Release package validator misreported file package parents

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_release_package.py --package <parent>/paper-lab-agent-release.zip`，且 `<parent>` 是普通文件。
- 实际结果：validator 报告 `release package missing: <parent>/paper-lab-agent-release.zip`，没有指出 package 路径父级不是目录。
- 期望结果：父级路径已存在但不是普通目录时，返回 `release package parent is not a regular directory: <parent>`，便于交付 zip 复验脚本直接定位路径结构错误。

## 原因

- 根因：`validate_release_package()` 只在 `resolve()` 前检查 package 路径本身和 symlink 父级；当父级是普通文件时，会直接进入 package missing 分支。
- 影响范围：release handoff zip 复验失败时，文件父级路径被误分类为缺失 zip，增加发布排障成本。

## 修复

- 修改文件：`scripts/validate_release_package.py`、`tests/test_release_contracts.py`。
- 关键行为：在解析 package 路径前先检查已存在但不是目录的父路径，并返回 `release package parent is not a regular directory`；package 本身为目录、package symlink、父级 symlink、祖先 symlink、坏 zip 等既有行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_file_package_parent -q` 失败，当前实现输出 `release package missing`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_file_package_parent tests/test_release_contracts.py::test_validate_release_package_rejects_directory_package_path tests/test_release_contracts.py::test_validate_release_package_rejects_package_symlink tests/test_release_contracts.py::test_validate_release_package_rejects_package_parent_symlink tests/test_release_contracts.py::test_validate_release_package_rejects_package_ancestor_symlink tests/test_release_contracts.py::test_validate_release_package_reports_zip_read_failure tests/test_release_contracts.py::test_validate_release_package_script_rejects_tampered_zip_artifact -q` 通过，7 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1250 passed。
