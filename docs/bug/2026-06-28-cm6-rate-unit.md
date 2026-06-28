# Cm6 rate unit was truncated

## 现象

- 触发命令、接口或页面：文档章节中包含三体反应速率单位，例如 `The rate coefficient is 1.2e-30 cm6/s`。
- 实际结果：反应可以抽取成功，`rate_type` 为 `constant`，但 `rate_value` 只保留 `1.2e-30`，单位 `cm6/s` 丢失。
- 期望结果：速率值应作为原文字符串 `1.2e-30 cm6/s` 保留，供复核界面和导出元数据使用。

## 原因

- 根因：`app/services/chemistry.py` 的 `RATE_VALUE_RE` 已支持 `cm3/s` 和相关写法，但 `cm` 指数只覆盖 3 次方，没有覆盖三体反应常见的 6 次方。
- 影响范围：使用 `cm6/s` 标注三体速率系数的表格或正文会丢失单位，降低人工复核和导出可审计性。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：速率值抽取支持 `1.2e-30 cm6/s`，并保留既有 `cm3/s`、`cm3 s-1`、`cm³/s`、`cm3 mol^-1 s^-1` 和常见科学计数法行为。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_cm6_rate_units -q`，确认 `rate_value` 被截断为 `1.2e-30`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_explicit_rate_value_near_reaction tests/test_api.py::test_extract_chemistry_preserves_superscript_rate_units tests/test_api.py::test_extract_chemistry_preserves_cm6_rate_units tests/test_api.py::test_extract_chemistry_preserves_space_separated_rate_units tests/test_api.py::test_extract_chemistry_preserves_mol_rate_units tests/test_api.py::test_extract_chemistry_preserves_multiplication_scientific_rate_value -q`，6 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1019 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1019 passed`。
