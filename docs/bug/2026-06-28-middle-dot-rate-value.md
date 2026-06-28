# Middle dot scientific rate value was truncated

## 现象

- 触发命令、接口或页面：文档章节中包含反应和中点科学计数法速率值，例如 `The rate coefficient is 1.2·10^-13 cm3/s`。
- 实际结果：反应可以抽取成功，`rate_type` 为 `constant`，但 `rate_value` 只保留 `1.2`。
- 期望结果：速率值应作为原文字符串 `1.2·10^-13 cm3/s` 保留，`rate_type` 标记为 `constant`。

## 原因

- 根因：`app/services/chemistry.py` 的 `RATE_VALUE_RE` 支持 `×`、ASCII `x` 和全角 `ｘ`，但未覆盖论文和 PDF/TEI 抽文本中常见的中点乘号 `·`。
- 影响范围：速率系数使用 `·10` 科学计数法时，原文速率值会被截断，降低人工复核和导出可审计性。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：rate value 科学计数法乘号匹配支持中点 `·`；返回值仍保留论文原文字符串，不做单位换算或数值归一化。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_middle_dot_scientific_rate_value -q`，确认 `rate_value` 被截断为 `1.2`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_middle_dot_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_multiplication_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_unicode_minus_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_superscript_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_fullwidth_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_fullwidth_x_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_explicit_rate_value_near_reaction -q`，7 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，995 passed；`bash scripts/release_check.sh`，通过，包含全量 pytest `995 passed`。
