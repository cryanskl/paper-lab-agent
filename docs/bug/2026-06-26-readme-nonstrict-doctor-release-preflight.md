# README documented non-strict doctor as release preflight

## 现象

- `README.md` 只记录了 `python scripts/doctor.py --compact`，并把它描述为适合发布前快速预检。
- `scripts/doctor.py --compact` 是报告模式；当缺少关键文件或依赖时会输出失败结果，但不会返回非零退出码。
- 读者按 README 做发布或演示前检查时，可能漏掉应被阻断的 preflight 问题。

## 原因

- release gate 和 release checklist 已经使用 `python scripts/doctor.py --strict --compact`，但 README 没有同步区分 Quick Start 预检和发布门禁。
- 文档契约测试只要求 README 提到轻量 doctor，没有要求 README 暴露 strict 发布命令。

## 修复

- README 保留 Quick Start 的 `python scripts/doctor.py --compact`，但明确它只用于新机器快速预检。
- README 的 Verification 区块新增 `python scripts/doctor.py --strict --compact`，并说明 strict 模式会在必需检查失败时返回非零退出码。
- 扩展 `test_doctor_preflight_is_documented_and_in_release_gate`，要求 README、release checklist 和 release gate 都覆盖 strict doctor preflight。

## 验证

- RED：`python -m pytest tests/test_release_contracts.py::test_doctor_preflight_is_documented_and_in_release_gate -q` 在 README 缺少 strict 命令时失败。
- GREEN：`python -m pytest tests/test_release_contracts.py::test_doctor_preflight_is_documented_and_in_release_gate -q`
- 完整 gate：`bash scripts/release_check.sh` 通过，`707 passed`。
