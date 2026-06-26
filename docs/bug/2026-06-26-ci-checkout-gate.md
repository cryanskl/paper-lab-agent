# Release hygiene 未校验 CI checkout

## 现象

`scripts/validate_release_hygiene.py` 会校验 GitHub Actions 触发器、Python setup、依赖安装和 release gate 命令，但此前不校验 workflow 是否先执行 `actions/checkout@v4`。如果 checkout 步骤被误删，干净 runner 上没有仓库文件，`bash scripts/release_check.sh` 会直接找不到脚本或项目文件。

## 原因

CI hygiene 检查把 release gate 命令本身作为核心契约，但没有把运行 gate 前必须 checkout 仓库纳入发布契约。

## 修复

新增 `ci_checks_out_repo` 检查，要求 `.github/workflows/ci.yml` 包含 `actions/checkout@v4`。同时新增契约测试覆盖缺少 checkout 的 workflow。

## 验证

先新增契约测试并确认红灯，再实现 CI hygiene 检查。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_reports_missing_ci_checkout -q` 失败，`missing` 中缺少 `ci_checks_out_repo`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_hygiene_validator_reports_missing_ci_checkout -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`720 passed`。
