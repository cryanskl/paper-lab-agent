# Env example validator followed symlinked parent directory

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_env_example.py .env.example`，且传入的 `.env.example` 父级目录是指向仓库外目录的 symlink。
- 实际结果：validator 会跟随 symlinked parent 读取仓库外 `.env.example`；只要目标文件满足当前键和值检查，命令返回成功。
- 期望结果：`.env.example` 作为运行配置契约和发布检查输入时，文件和父级目录都必须来自普通文件树；遇到 symlinked parent 应返回非零。

## 原因

- 根因：入口只拒绝 `.env.example` 文件本身是 symlink 或非普通文件，没有检查父级目录链。
- 影响范围：发布前外部依赖和运行配置契约检查可能基于仓库边界外的 env example。

## 修复

- 在 `scripts/validate_env_example.py` 中增加路径父级链 symlink 检查。
- 当任一父级目录是 symlink 时，报告 `env example parent is not a regular directory` 并返回非零。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_env_example_parent -q` 失败，当前实现返回 `0`。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_env_example_parent tests/test_release_contracts.py::test_env_example_validator_rejects_symlinked_env_example tests/test_release_contracts.py::test_requirements_validator_rejects_symlinked_requirements_parent tests/test_release_contracts.py::test_requirements_validator_rejects_symlinked_requirements_file -q` 通过，`4 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "env_example"` 通过，`18 passed, 251 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`834 passed`；`bash scripts/release_check.sh` 通过。
