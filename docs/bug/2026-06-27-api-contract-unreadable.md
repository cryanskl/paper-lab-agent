# API contract validator crashed on unreadable contract

## 现象

- 触发命令、接口或页面：运行 `python scripts/validate_api_contract.py docs/接口设计文档.md`，且接口文档不是 UTF-8 文本或读取阶段抛出 `OSError`。
- 实际结果：校验器在解析 documented routes 时抛出底层异常，例如 `UnicodeDecodeError` traceback。
- 期望结果：API contract gate 应返回稳定错误，指出接口文档不可读，而不是中断整个 release gate。

## 原因

- 根因：`scripts/validate_api_contract.py` 的 `main()` 在确认 contract 路径存在、父级不是 symlink、文件本身是普通文件后，直接进入多个会读取 contract 的校验函数；读取和解码错误没有先转换为可诊断 CLI 错误。
- 影响范围：API contract 校验、release gate、CI 接口契约检查。

## 修复

- 修改文件：`scripts/validate_api_contract.py`、`tests/test_release_contracts.py`。
- 关键行为：contract regular-file 检查通过后、执行 documented routes / pagination / async response 等契约校验前，先用 UTF-8 读取接口文档；读取或解码失败时返回 1，并输出 `api contract file unreadable: ...`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_api_contract_validator_reports_unreadable_contract_file -q` 失败，stderr 包含 `UnicodeDecodeError` traceback。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "api_contract"` 通过，`85 passed, 218 deselected`；`.venv/bin/python -m py_compile scripts/validate_api_contract.py` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`910 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `910 passed`。
