# Requirements validator flagged importlib as third-party

## 现象

`scripts/release_check.sh` 在新增 `scripts/doctor.py` 后失败，错误为 `requirements missing imported packages: importlib`。`importlib` 是 Python 标准库，不应该要求写入 `requirements.txt`。

## 原因

当前运行环境是 Python 3.9，`scripts/validate_requirements.py` 需要依赖 `FALLBACK_STDLIB_MODULES` 判断标准库模块。该 fallback 列表包含 `fnmatch`、`shlex`、`subprocess` 等模块，但漏掉了 `importlib`。

## 修复

将 `importlib` 加入 `FALLBACK_STDLIB_MODULES`，并扩展标准库忽略测试，覆盖 `import importlib.util`。

## 验证

新增红测确认 `importlib.util` 不会被误判为缺失依赖，并重新运行 requirements validator：

```bash
python -m pytest tests/test_release_contracts.py::test_requirements_validator_ignores_standard_library_imports -q
python scripts/validate_requirements.py
```
