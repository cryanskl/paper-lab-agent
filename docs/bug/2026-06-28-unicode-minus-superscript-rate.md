# Unicode minus superscript rate exponent was truncated

## 现象

- 触发命令、接口或页面：文档章节中包含反应和 Unicode minus + 上标数字混合指数速率值，例如 `The rate coefficient is 1.2×10−¹³ cm3/s`。
- 实际结果：反应可以抽取成功，`rate_type` 为 `constant`，但 `rate_value` 只保留 `1.2`。
- 期望结果：速率值应作为原文字符串 `1.2×10−¹³ cm3/s` 保留，`rate_type` 标记为 `constant`。

## 原因

- 根因：`app/services/chemistry.py` 的 `RATE_VALUE_RE` 已支持 `−13` 和 `⁻¹³`，但上标数字分支的符号集合没有覆盖 Unicode minus `−`。
- 影响范围：PDF/TEI 或复制文本中使用 `10−¹³` 这类混合指数写法时，原文速率值会被截断，降低人工复核和导出可审计性。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：rate value 上标指数分支支持 Unicode minus `−`；返回值仍保留论文原文字符串，不做单位换算或数值归一化。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_unicode_minus_superscript_rate_value -q`，确认 `rate_value` 被截断为 `1.2`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_unicode_minus_superscript_rate_value tests/test_api.py::test_extract_chemistry_preserves_unicode_minus_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_superscript_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_middle_dot_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_multiplication_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_fullwidth_x_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_explicit_rate_value_near_reaction -q`，7 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，996 passed；`bash scripts/release_check.sh`，通过，包含全量 pytest `996 passed`。
