# Env example validator accepted symlinked env example

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_env_example.py`，且 `.env.example` 是指向仓库外文件的 symlink。
- 实际结果：只要 symlink 目标文件包含有效配置样例，validator 会跟随 symlink 并返回成功。
- 期望结果：发布配置契约检查应拒绝 symlinked `.env.example`，避免新机器配置样例来自仓库边界之外。

## 原因

- 根因：env example validator 入口只检查路径是否存在，没有拒绝 symlink 或非普通文件。
- 影响范围：`.env.example` 必需键、默认值漂移和 secret-like 空值检查的输入可信度。

## 修复

- 在 `scripts/validate_env_example.py` 入口增加普通文件检查。
- 当 `.env.example` 是 symlink 或非普通文件时，返回非零并报告 `env example is not a regular file`，不再继续读取目标内容。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_env_example -q` 失败，当前实现返回 `0`。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_env_example -q` 通过，`1 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "env_example"` 通过，`17 passed, 241 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`823 passed`；`bash scripts/release_check.sh` 通过。
