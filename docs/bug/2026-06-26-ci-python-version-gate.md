# Release hygiene 未校验 CI Python 版本

## 现象

`scripts/validate_release_hygiene.py` 已校验 GitHub Actions 使用 `actions/setup-python@v5`，但此前不校验 workflow 是否固定 `python-version: "3.11"`。如果 CI 配置漂移并省略版本，release gate 会运行在 action 或 runner 的默认 Python 上，可能和本地验证环境不一致。

## 原因

CI hygiene 检查只确认 setup-python action 存在，没有把具体 Python 版本纳入发布契约。

## 修复

新增 `ci_python_version` 检查，要求 `.github/workflows/ci.yml` 包含 `python-version: "3.11"`。同时新增契约测试覆盖缺少 Python version 的 workflow。

## 验证

先新增契约测试并确认红灯，再实现 CI hygiene 检查。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_reports_missing_ci_python_version -q` 失败，`missing` 中缺少 `ci_python_version`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_reports_missing_ci_python_version -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`719 passed`。
