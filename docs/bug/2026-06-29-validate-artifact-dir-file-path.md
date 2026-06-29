# Release artifact validator misreported file artifact directories

## 现象

- 触发命令、接口或页面：调用 `validate_release_artifacts()` 或运行 `scripts/validate_release_artifacts.py --artifact-dir <path>`，且 `<path>` 是普通文件。
- 实际结果：validator 报告 `release artifact directory is not a directory: <path>`，和 artifact directory 为 symlink 时的 `release artifact directory is not a regular directory` 诊断不一致。
- 期望结果：文件、symlink 等非普通目录 artifact dir 输入统一报告 `release artifact directory is not a regular directory: <path>`，便于 handoff 校验脚本稳定匹配路径类型错误。

## 原因

- 根因：`validate_release_artifacts()` 在解析路径后对存在但不是目录的 artifact dir 使用了单独的 `is not a directory` 文案。
- 影响范围：release artifact 复验失败时，同类非普通目录输入错误分类不一致，增加 CI 和人工排障成本。

## 修复

- 修改文件：`scripts/validate_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：artifact dir 已存在但不是普通目录时统一返回 `release artifact directory is not a regular directory`；artifact dir symlink、父级 symlink、祖先 symlink、正常 handoff bundle 以及缺失 artifact 聚合行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_file_artifact_dir -q` 失败，当前实现输出 `release artifact directory is not a directory`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_file_artifact_dir tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink_parent tests/test_release_contracts.py::test_validate_release_artifacts_rejects_artifact_dir_symlink_ancestor tests/test_release_contracts.py::test_validate_release_artifacts_script_accepts_handoff_bundle -q` 通过，5 passed。
- 完整 gate：`bash scripts/release_check.sh` 通过，1251 passed。
