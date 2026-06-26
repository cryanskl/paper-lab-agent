# Release hygiene 未校验 CI 安装 requirements

## 现象

`scripts/validate_release_hygiene.py` 会检查 GitHub Actions workflow 是否触发 `push`、`pull_request`、`workflow_dispatch`，是否设置超时，以及是否运行 `bash scripts/release_check.sh`。但它此前不校验 workflow 是否在干净 runner 上先执行 `python -m pip install -r requirements.txt`。如果 CI 配置漂移删掉依赖安装，本地 release gate 仍可能通过，GitHub Actions 会在导入 FastAPI、Streamlit、pytest 等依赖时失败。

## 原因

CI hygiene 检查只覆盖 release gate 命令本身，没有把“安装锁定依赖后再跑 gate”作为发布契约的一部分。

## 修复

新增 `ci_installs_requirements` 检查，要求 `.github/workflows/ci.yml` 包含 `python -m pip install -r requirements.txt`。同时新增契约测试，覆盖缺少 requirements 安装步骤的 workflow。

## 验证

先新增契约测试并确认红灯，再实现 CI hygiene 检查。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_reports_missing_ci_requirements_install -q` 失败，`missing` 中缺少 `ci_installs_requirements`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_reports_missing_ci_requirements_install -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`717 passed`。
