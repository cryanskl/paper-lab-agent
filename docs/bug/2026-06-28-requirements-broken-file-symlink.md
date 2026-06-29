# Requirements validator misreported broken requirements symlinks as missing

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_requirements.py`，且 `requirements.txt` 文件路径是断开的 symlink。
- 实际结果：validator 输出 `requirements file not found`。
- 期望结果：validator 应输出 `requirements file is not a regular file`，把 requirements 文件路径类型错误和真正缺失文件区分开。

## 原因

`main()` 在 requirements 文件普通文件检查前先判断 `requirements_path.exists()`。broken symlink 的 `exists()` 为假，函数直接返回 not found，跳过了后续已有的 symlink / regular file 诊断。

## 修复

- 修改文件：`scripts/validate_requirements.py`、`tests/test_release_contracts.py`。
- 关键行为：requirements 入口只在路径既不存在也不是 symlink 时返回 `requirements file not found`；broken symlink 会进入普通文件检查并报告 `requirements file is not a regular file`。
- 影响范围：只改变断开的 requirements 文件 symlink 错误分类；真正缺失 requirements、正常 requirements、普通 symlink requirements、父级异常和后续源码检查行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_rejects_broken_symlinked_requirements_file -q` 失败，当前实现输出 `requirements file not found`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_rejects_broken_symlinked_requirements_file tests/test_release_contracts.py::test_requirements_validator_rejects_symlinked_requirements_file tests/test_release_contracts.py::test_requirements_validator_rejects_symlinked_requirements_parent tests/test_release_contracts.py::test_requirements_validator_rejects_file_requirements_parent tests/test_release_contracts.py::test_requirements_validator_runs_as_release_script tests/test_release_contracts.py::test_requirements_validator_accepts_declared_direct_dependencies -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1119 passed`。
