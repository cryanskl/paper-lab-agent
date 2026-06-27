# 上标科学计数法速率值被截断

## 现象

化学抽取遇到 `The rate coefficient is 1.2×10⁻¹³ cm3/s` 时，`rate_value` 只保存为 `1.2`，丢失 `×10⁻¹³ cm3/s`。

## 原因

速率系数正则已经支持 `1.2×10^-13`，但指数部分只覆盖 ASCII `^-13` 或 `-13`，没有覆盖论文 PDF/TEI 中常见的上标负号和上标数字。

## 修复

扩展 `RATE_VALUE_RE` 的乘号科学计数法指数部分，支持 `⁺`、`⁻` 和上标数字 `⁰¹²³⁴⁵⁶⁷⁸⁹`，继续按论文原文保存，不做数值归一化或单位换算。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_superscript_scientific_rate_value -q` 失败，`rate_value` 为 `1.2`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_superscript_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_multiplication_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_explicit_rate_value_near_reaction tests/test_api.py::test_extract_chemistry_preserves_superscript_rate_units -q` 通过，`4 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`888 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `888 passed`。
