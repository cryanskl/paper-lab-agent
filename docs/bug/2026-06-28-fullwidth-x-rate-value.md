# Fullwidth x scientific rate value was truncated

## 现象

- 触发命令、接口或页面：文档章节中包含反应和全角 `x` 科学计数法速率值，例如 `The rate coefficient is １．２ｘ１０⁻¹³ cm3/s`。
- 实际结果：反应可以抽取成功，`rate_type` 为 `constant`，但 `rate_value` 只保留 `１`。
- 期望结果：速率值应作为原文字符串 `１．２ｘ１０⁻¹³ cm3/s` 保留，`rate_type` 标记为 `constant`。

## 原因

- 根因：`app/services/chemistry.py` 的 `RATE_VALUE_RE` 支持乘号 `×` 和 ASCII `x`，但未覆盖全角 `ｘ`；正则因此只匹配到开头数字。
- 影响范围：PDF/TEI 或复制文本中使用全角 `ｘ１０` 科学计数法时，速率系数原文会被截断，降低人工复核和导出可审计性。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：rate value 匹配支持全角 `ｘ`；返回值仍保留论文原文字符串，不做单位换算或数值归一化。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_fullwidth_x_scientific_rate_value -q`，确认 `rate_value` 被截断为 `１`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_fullwidth_x_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_fullwidth_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_multiplication_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_superscript_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_fullwidth_rate_unit tests/test_api.py::test_extract_chemistry_preserves_fullwidth_space_separated_rate_unit -q`，6 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，992 passed；`bash scripts/release_check.sh`，通过，包含全量 pytest `992 passed`。
