# Spaced e notation rate value was truncated

## 现象

- 触发命令、接口或页面：文档章节中包含反应和空格分隔的 e 科学计数法速率值，例如 `The rate coefficient is 1.2 e -13 cm3/s`。
- 实际结果：反应可以抽取成功，`rate_type` 为 `constant`，但 `rate_value` 只保留 `1.2`。
- 期望结果：速率值应作为原文字符串 `1.2 e -13 cm3/s` 保留，`rate_type` 标记为 `constant`。

## 原因

- 根因：`app/services/chemistry.py` 的 `RATE_VALUE_RE` e 科学计数法分支要求数值、`e`、指数符号和指数数字紧贴，未允许 PDF/TEI 抽文本中常见的分隔空格。
- 影响范围：论文或 PDF/TEI 抽文本中使用 `1.2 e -13` 这类写法时，原文速率值会被截断，降低人工复核和导出可审计性。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：rate value e 科学计数法分支允许数值、`e`、指数符号和指数数字之间存在空格；返回值仍保留论文原文字符串，不做单位换算或数值归一化。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_spaced_e_notation_rate_value -q`，确认 `rate_value` 被截断为 `1.2`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_spaced_e_notation_rate_value tests/test_api.py::test_extract_chemistry_preserves_explicit_rate_value_near_reaction tests/test_api.py::test_extract_chemistry_preserves_superscript_rate_units tests/test_api.py::test_extract_chemistry_preserves_space_separated_rate_units tests/test_api.py::test_extract_chemistry_preserves_spaced_exponent_rate_value tests/test_api.py::test_extract_chemistry_preserves_multiplication_scientific_rate_value -q`，6 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，999 passed；`bash scripts/release_check.sh`，通过，包含全量 pytest `999 passed`。
