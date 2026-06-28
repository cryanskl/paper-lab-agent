# Env example validator misreported broken env example symlinks as missing

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_env_example.py`，且 `.env.example` 文件路径是断开的 symlink。
- 实际结果：validator 输出 `env example not found`。
- 期望结果：validator 应输出 `env example is not a regular file`，把 `.env.example` 文件路径类型错误和真正缺失文件区分开。

## 原因

`main()` 在 `.env.example` 普通文件检查前先判断 `path.exists()`。broken symlink 的 `exists()` 为假，函数直接返回 not found，跳过了后续已有的 symlink / regular file 诊断。

## 修复

- 修改文件：`scripts/validate_env_example.py`、`tests/test_release_contracts.py`。
- 关键行为：`.env.example` 入口只在路径既不存在也不是 symlink 时返回 `env example not found`；broken symlink 会进入普通文件检查并报告 `env example is not a regular file`。
- 影响范围：只改变断开的 `.env.example` 文件 symlink 错误分类；真正缺失 `.env.example`、正常 `.env.example`、普通 symlink `.env.example`、父级异常、unreadable `.env.example` 和后续配置检查保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_broken_symlinked_env_example -q` 失败，当前实现输出 `env example not found`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_broken_symlinked_env_example tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_env_example tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_env_example_parent tests/test_release_contracts.py::test_env_example_validator_rejects_file_env_example_parent tests/test_release_contracts.py::test_env_example_validator_reports_unreadable_env_example tests/test_release_contracts.py::test_env_example_validator_reports_missing_required_key -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1120 passed`。
