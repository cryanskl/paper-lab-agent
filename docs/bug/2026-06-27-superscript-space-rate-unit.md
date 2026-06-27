# 上标空格分隔速率单位被截断

## 现象

论文原文中的速率系数 `1.2e-13 cm³ s⁻¹` 被抽取为 `1.2e-13`，单位 `cm³ s⁻¹` 丢失。

## 原因

速率值正则已覆盖斜杠单位 `cm³/s` 和 ASCII 空格分隔单位 `cm3 s-1`，但没有覆盖体积单位后以空格连接的上标秒倒数 `s⁻¹`。

## 修复

扩展 `RATE_VALUE_RE` 的单位匹配，让 `cm3`、`cm³`、`m3`、`m³` 后的空格分隔单位同时支持 `s-1` 和 `s⁻¹`，保留论文原文单位。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_superscript_space_separated_rate_units -q` 失败，实际 `rate_value` 为 `1.2e-13`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_superscript_space_separated_rate_units tests/test_api.py::test_extract_chemistry_preserves_space_separated_rate_units tests/test_api.py::test_extract_chemistry_preserves_superscript_rate_units tests/test_api.py::test_extract_chemistry_preserves_explicit_rate_value_near_reaction -q` 通过，`4 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`890 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `890 passed`。
