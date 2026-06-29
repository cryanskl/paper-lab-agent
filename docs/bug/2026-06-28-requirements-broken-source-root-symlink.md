# Requirements validator ignored broken Python source root symlinks

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_requirements.py`，且 Python source root（例如 `app`）是断开的目录 symlink。
- 实际结果：validator 返回 0，未报告源码根路径异常。
- 期望结果：validator 应输出 `python source root is not a regular directory`，把 broken source root symlink 作为发布前路径安全问题拦截。

## 原因

`non_regular_python_source_roots()` 在检查 `path.is_symlink()` 前先判断 `not path.exists()` 并 `continue`。broken symlink 的 `exists()` 为假，函数直接跳过该源码根，后续 `python_files()` 也不会扫描它，导致发布校验误通过。

## 修复

- 修改文件：`scripts/validate_requirements.py`、`tests/test_release_contracts.py`。
- 关键行为：source root 先拒绝 symlink，再跳过真正不存在的可选路径；broken symlink 和普通 symlink 都会报告 `python source root is not a regular directory`。
- 影响范围：只改变断开的 Python source root symlink 处理；普通 source root symlink、source file symlink、正常 requirements 检查和缺失可选路径行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_rejects_broken_symlinked_python_source_root -q` 失败，当前实现返回 0。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_rejects_broken_symlinked_python_source_root tests/test_release_contracts.py::test_requirements_validator_rejects_symlinked_python_source_root tests/test_release_contracts.py::test_requirements_validator_rejects_symlinked_python_source tests/test_release_contracts.py::test_requirements_validator_rejects_broken_symlinked_requirements_file tests/test_release_contracts.py::test_requirements_validator_accepts_declared_direct_dependencies tests/test_release_contracts.py::test_requirements_validator_reports_imported_package_missing_from_requirements -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1121 passed`。
