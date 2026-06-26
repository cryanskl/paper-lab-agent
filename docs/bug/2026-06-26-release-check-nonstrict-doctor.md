# Release gate ran doctor without strict mode

## 现象

`scripts/release_check.sh` 会运行 `scripts/doctor.py --compact`，但没有传 `--strict`。如果 doctor 检查发现缺失文件、缺失依赖或 Python 版本不满足要求，它会输出 `ok: false` 但仍以 0 退出，release gate 会继续通过后续步骤。

## 原因

`scripts/doctor.py` 设计为默认只报告结果，只有传入 `--strict` 时才在失败检查上返回非零。release gate 接入 doctor 时使用了非严格模式。

## 修复

将 release gate 中的 doctor 调用改为 `scripts/doctor.py --strict --compact`，并增加契约测试要求 release gate 使用严格模式。

## 验证

新增 release contract 测试确认严格调用，并重新运行 doctor focused tests：

```bash
python -m pytest tests/test_release_contracts.py::test_doctor_preflight_is_documented_and_in_release_gate -q
python scripts/doctor.py --strict --compact
```

- 完整 gate：`bash scripts/release_check.sh` 通过，`708 passed`。
