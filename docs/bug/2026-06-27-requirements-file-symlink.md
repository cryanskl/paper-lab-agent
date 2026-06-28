# Requirements validator accepted symlinked requirements file

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_requirements.py requirements.txt`，且 `requirements.txt` 是指向仓库外文件的 symlink。
- 实际结果：只要 symlink 目标文件包含有效依赖声明，validator 会跟随 symlink 并返回成功。
- 期望结果：发布依赖契约检查应拒绝 symlinked `requirements.txt`，避免 release gate 使用仓库边界外的依赖清单。

## 原因

- 根因：requirements validator 的 CLI 入口直接把传入路径交给各个解析函数，没有先检查目标是否为普通文件。
- 影响范围：必需依赖、导入依赖、固定版本和重复依赖检查的输入可信度。

## 修复

- 在 `scripts/validate_requirements.py` 入口增加存在性和普通文件检查。
- 当 requirements 路径是 symlink 或非普通文件时，返回非零并报告 `requirements file is not a regular file`，不再继续读取目标内容。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_rejects_symlinked_requirements_file -q` 失败，当前实现返回 `0`。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_rejects_symlinked_requirements_file -q` 通过，`1 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "requirements_validator"` 通过，`8 passed, 251 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`824 passed`；`bash scripts/release_check.sh` 通过。
