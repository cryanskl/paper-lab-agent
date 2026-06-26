# Requirements validator flagged email as third-party

## 现象

- `bash scripts/release_check.sh` 在新增 `app/clients/retry_after.py` 后失败。
- 失败信息为 `requirements missing imported packages: email`。
- `email` 是 Python 标准库，不应该要求写入 `requirements.txt`。

## 原因

- 当前运行环境需要依赖 `scripts/validate_requirements.py` 的 `FALLBACK_STDLIB_MODULES` 识别标准库模块。
- fallback 列表已包含多个标准库模块，但漏掉了 `email`。
- 新代码使用 `from email.utils import parsedate_to_datetime` 后触发误判。

## 修复

- 将 `email` 加入 `FALLBACK_STDLIB_MODULES`。
- 扩展 `test_requirements_validator_ignores_standard_library_imports`，覆盖 `import email.utils`。

## 验证

- RED：`python -m pytest tests/test_release_contracts.py::test_requirements_validator_ignores_standard_library_imports -q` 在 fallback 缺少 `email` 时失败。
- GREEN：`python -m pytest tests/test_release_contracts.py::test_requirements_validator_ignores_standard_library_imports -q`
- validator：`python scripts/validate_requirements.py`
- 完整 gate：`bash scripts/release_check.sh` 通过，`707 passed`。
