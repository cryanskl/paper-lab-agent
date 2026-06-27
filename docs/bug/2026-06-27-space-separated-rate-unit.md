# 空格分隔速率单位被截断

## 现象

化学抽取遇到 `The rate coefficient is 1.2e-13 cm3 s-1` 时，`rate_value` 只保存为 `1.2e-13`，丢失原文单位 `cm3 s-1`。

## 原因

速率系数正则只覆盖 `cm3/s`、`cm³/s` 等斜杠单位写法，以及单独的 `s-1`。真实论文常见的体积单位加空格加 `s-1` 写法没有被纳入单位组。

## 修复

扩展 `RATE_VALUE_RE` 的单位匹配，让 `cm3 s-1` 和 `m3 s-1` 与现有斜杠写法一样保留到 `rate_value`，继续保存论文原文表达，不做单位换算。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_space_separated_rate_units -q` 失败，`rate_value` 为 `1.2e-13`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_space_separated_rate_units tests/test_api.py::test_extract_chemistry_preserves_explicit_rate_value_near_reaction tests/test_api.py::test_extract_chemistry_preserves_superscript_rate_units tests/test_api.py::test_extract_chemistry_preserves_multiplication_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_superscript_scientific_rate_value -q` 通过，`5 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`889 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `889 passed`。
