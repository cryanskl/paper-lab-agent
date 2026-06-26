# Release hygiene 未校验 CI Python setup

## 现象

`scripts/validate_release_hygiene.py` 会检查 GitHub Actions 是否运行 release gate、安装 requirements、设置触发器和超时，但此前不校验 workflow 是否显式使用 `actions/setup-python@v5`。如果 CI 配置漂移并依赖 runner 默认 Python，干净 CI 环境可能和本地/文档中的运行环境不一致，导致发布 gate 的可复现性下降。

## 原因

CI hygiene 检查只约束了命令顺序和依赖安装，没有把 Python 运行时 setup 纳入发布契约。

## 修复

新增 `ci_sets_up_python` 检查，要求 `.github/workflows/ci.yml` 包含 `actions/setup-python@v5`。同时新增契约测试覆盖缺少 Python setup 的 workflow。

## 验证

先新增契约测试并确认红灯，再实现 CI hygiene 检查。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_reports_missing_ci_python_setup -q` 失败，`missing` 中缺少 `ci_sets_up_python`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_reports_missing_ci_python_setup -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`718 passed`。
