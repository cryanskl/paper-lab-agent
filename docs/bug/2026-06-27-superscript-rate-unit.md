# 速率系数上标单位被截断

## 现象

化学抽取遇到 `The rate coefficient is 1.2e-13 cm³/s` 时，`rate_value` 只保存为 `1.2e-13`，丢失原文单位 `cm³/s`。

## 原因

速率系数正则只覆盖 `cm3/s`、`cm^3/s`、`m3/s`、`m^3/s` 等 ASCII 单位写法。真实论文常见的上标三 `³` 不匹配，于是可选单位组被跳过，只捕获数字。

## 修复

扩展 `RATE_VALUE_RE` 的单位匹配，让 `cm³/s` 和 `m³/s` 与现有 ASCII 写法一样被保留到 `rate_value`。不做单位换算，继续保存论文原文表达。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_superscript_rate_units -q` 失败，`rate_value` 为 `1.2e-13`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_superscript_rate_units tests/test_api.py::test_extract_chemistry_preserves_explicit_rate_value_near_reaction tests/test_api.py::test_extract_chemistry_classifies_unicode_minus_negative_ions tests/test_api.py::test_extract_chemistry_reads_explicit_threshold_ev_near_reaction -q` 通过，`4 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`886 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `886 passed`。
