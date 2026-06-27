# API contract validator accepted symlinked contract file

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_api_contract.py docs/接口设计文档.md`，且接口文档路径是指向仓库外 Markdown 文件的 symlink。
- 实际结果：只要 symlink 目标文件包含有效接口契约，validator 会跟随 symlink 并返回成功。
- 期望结果：接口契约发布检查应拒绝 symlinked contract 文件，避免 release gate 使用仓库边界外的 API 真理来源。

## 原因

- 根因：API contract validator 的 CLI 入口直接把传入路径交给各个解析函数，没有先检查目标是否为普通文件。
- 影响范围：已文档化接口、未文档化接口、分页、异步响应和错误响应契约检查的输入可信度。

## 修复

- 在 `scripts/validate_api_contract.py` 入口增加存在性和普通文件检查。
- 当 contract 路径是 symlink 或非普通文件时，返回非零并报告 `api contract file is not a regular file`，不再继续读取目标内容。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_api_contract_validator_rejects_symlinked_contract_file -q` 失败，当前实现返回 `0`。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_api_contract_validator_rejects_symlinked_contract_file -q` 通过，`1 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "api_contract"` 通过，`82 passed, 179 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`826 passed`；`bash scripts/release_check.sh` 通过。
