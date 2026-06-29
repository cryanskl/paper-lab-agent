# Release gate inherited optional external preflight environment

## 现象

- 触发命令、接口或页面：`OPENALEX_MAILTO=lab@example.test UNPAYWALL_EMAIL=lab@example.test LLM_API_KEY=sk-test bash scripts/release_check.sh`
- 实际结果：`scripts/doctor.py --strict --compact` 在调用者已配置外部能力时返回 `warning_count: 0`，但 release gate 固定校验默认离线 preflight 的 3 个 warning，导致发布门禁可能在配置完整的开发机上误失败；后续完整 pytest 也会继承 `LLM_API_KEY` 并误走外部 LLM 或破坏 `.env` loader 测试前提。
- 期望结果：release gate 校验默认离线 preflight 时应清空可选外部能力变量，只验证确定性的离线 handoff 路径，不受本机真实凭证影响。

## 原因

- 根因：`scripts/release_check.sh` 直接继承调用者的 `OPENALEX_MAILTO`、`UNPAYWALL_EMAIL` 和 `LLM_API_KEY`，但后续 doctor、demo data、release artifact、smoke 和 pytest 断言仍假定默认离线 warning 集合。
- 影响范围：已配置 OpenAlex、Unpaywall 或 LLM 凭证的开发机、CI secret 环境、发布机本地验证。

## 修复

- 修改文件：`scripts/release_check.sh`、`scripts/smoke_check.py`、`README.md`、`docs/release-checklist.md`、`tests/test_release_contracts.py`、`tests/test_api.py`
- 关键行为：release gate 对 doctor、demo data、release artifacts、smoke 和 pytest 的默认离线 preflight 调用显式 unset `OPENALEX_MAILTO`、`UNPAYWALL_EMAIL`、`LLM_API_KEY`，并在文档中说明该隔离行为；`smoke_check` 在内部清空可选外部变量后会恢复调用者环境。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_preflight_is_documented_and_in_release_gate -q` -> `1 failed`，release gate 未声明或使用 `OFFLINE_PREFLIGHT_ENV`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_preflight_is_documented_and_in_release_gate -q` -> `1 passed`
- 完整 gate：`OPENALEX_MAILTO=lab@example.test UNPAYWALL_EMAIL=lab@example.test LLM_API_KEY=sk-test bash scripts/release_check.sh` -> `1097 passed`
