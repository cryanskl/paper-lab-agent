# Requirements validator flagged zipfile as third-party

## 现象

新增 `scripts/package_release_artifacts.py` 后，完整发布门禁失败：

```bash
bash scripts/release_check.sh
```

错误为 `requirements missing imported packages: zipfile`。`zipfile` 是 Python 标准库，不应要求写入 `requirements.txt`。

## 原因

当前运行环境的标准库识别需要依赖 `scripts/validate_requirements.py` 中的 `FALLBACK_STDLIB_MODULES`。该 fallback 列表已包含 `hashlib`、`json`、`subprocess` 等模块，但漏掉了 `zipfile`。

## 修复

将 `zipfile` 加入 `FALLBACK_STDLIB_MODULES`，并扩展标准库忽略测试，覆盖 `import zipfile`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_ignores_standard_library_imports -q` 失败，`missing == ["zipfile"]`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_ignores_standard_library_imports -q`
- 完整 gate：`bash scripts/release_check.sh` 通过，`729 passed`。
