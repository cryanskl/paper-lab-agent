# Release checklist documented non-strict doctor preflight

## 现象

- `docs/release-checklist.md` 的 Local Gate 指导运行 `python scripts/doctor.py --compact`。
- `scripts/doctor.py` 默认是报告模式；如果缺少必需文件或依赖，它会输出 `ok: false`，但不会用非零退出码阻断发布流程。
- 手工发布检查可能因此漏掉 preflight 失败。

## 原因

- release gate 已经要求 `scripts/doctor.py --strict --compact`，但发布 checklist 没有同步更新。
- 文档契约测试只检查 checklist 提到了 doctor，没有要求发布场景使用 strict 模式。

## 修复

- 将 `docs/release-checklist.md` 的 Local Gate 改为 `python scripts/doctor.py --strict --compact`。
- 扩展 `test_doctor_preflight_is_documented_and_in_release_gate`，要求发布 checklist 和 release gate 都使用 strict doctor preflight。

## 验证

- RED：`python -m pytest tests/test_release_contracts.py::test_doctor_preflight_is_documented_and_in_release_gate -q` 在 checklist 缺少 strict 时失败。
- GREEN：`python -m pytest tests/test_release_contracts.py::test_doctor_preflight_is_documented_and_in_release_gate -q`
- 完整 gate：`bash scripts/release_check.sh`
