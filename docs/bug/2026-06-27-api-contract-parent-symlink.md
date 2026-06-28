# API contract validator followed symlinked parent directory

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_api_contract.py docs/接口设计文档.md`，且接口文档的父级目录是指向仓库外目录的 symlink。
- 实际结果：validator 会跟随 symlinked parent 读取仓库外 API 契约文档；只要内容满足当前接口契约检查，命令返回成功。
- 期望结果：API 契约作为发布真理来源时，入口路径和父级目录都必须来自普通仓库文件树；遇到 symlinked parent 应返回非零。

## 原因

- 根因：入口只拒绝 contract 文件本身是 symlink 或非普通文件，没有检查父级目录链。
- 影响范围：发布前 API contract gate 可能基于仓库边界外的文档内容，削弱接口契约和当前 checkout 的一致性证明。

## 修复

- 在 `scripts/validate_api_contract.py` 中增加 contract 路径父级链 symlink 检查。
- 当任一父级目录是 symlink 时，报告 `api contract file parent is not a regular directory` 并返回非零。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_api_contract_validator_rejects_symlinked_contract_parent -q` 失败，当前实现返回 `0`。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_api_contract_validator_rejects_symlinked_contract_parent tests/test_release_contracts.py::test_api_contract_validator_rejects_symlinked_contract_file tests/test_release_contracts.py::test_api_contract_validator_runs_as_release_script -q` 通过，`3 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "api_contract"` 通过，`83 passed, 183 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`831 passed`；`bash scripts/release_check.sh` 通过。
