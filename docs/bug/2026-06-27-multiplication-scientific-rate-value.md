# 乘号科学计数法速率值被截断

## 现象

化学抽取遇到 `The rate coefficient is 1.2×10^-13 cm3/s` 时，`rate_value` 只保存为 `1.2`，丢失 `×10^-13 cm3/s`。

## 原因

速率系数正则只覆盖 `1.2e-13` 这类 e/E 科学计数法。真实论文常见的 `1.2×10^-13` 或 `1.2x10^-13` 不匹配指数部分，于是匹配在小数后提前结束。

## 修复

扩展 `RATE_VALUE_RE` 的数值部分，支持 `×10^-13` 和 `x10^-13` 形式，并继续按论文原文保存，不做单位换算或数值归一化。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_multiplication_scientific_rate_value -q` 失败，`rate_value` 为 `1.2`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_multiplication_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_explicit_rate_value_near_reaction tests/test_api.py::test_extract_chemistry_preserves_superscript_rate_units tests/test_api.py::test_extract_chemistry_reads_explicit_threshold_ev_near_reaction -q` 通过，`4 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`887 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `887 passed`。
