# Unicode minus molecule rate unit was truncated

## 现象

- 触发命令、接口或页面：文档章节中包含 Unicode minus 指数形式的二体反应速率单位，例如 `The rate coefficient is 1.2e-13 cm3 molecule−1 s−1`。
- 实际结果：反应可以抽取成功，`rate_type` 为 `constant`，但 `rate_value` 只保留 `1.2e-13`，单位 `cm3 molecule−1 s−1` 丢失。
- 期望结果：速率值应作为原文字符串 `1.2e-13 cm3 molecule−1 s−1` 保留，供复核界面和导出元数据使用。

## 原因

- 根因：`app/services/chemistry.py` 的 `RATE_VALUE_RE` 已支持 `molecule-1` 和 `molecule^-1`，但单位指数分支没有覆盖 PDF 抽取中常见的 Unicode minus `−`。
- 影响范围：使用 Unicode minus 标注二体速率单位的表格或正文会丢失单位，降低人工复核和导出可审计性。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：速率值抽取支持 `1.2e-13 cm3 molecule−1 s−1`，并保留既有 `molecule^-1`、`molecule-1`、`molec^-1`、`cm3 s-1`、`cm³ s⁻¹` 和常见科学计数法行为。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_unicode_minus_molecule_rate_units -q`，确认 `rate_value` 被截断为 `1.2e-13`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_explicit_rate_value_near_reaction tests/test_api.py::test_extract_chemistry_preserves_molecule_rate_units tests/test_api.py::test_extract_chemistry_preserves_caret_molecule_rate_units tests/test_api.py::test_extract_chemistry_preserves_abbreviated_molecule_rate_units tests/test_api.py::test_extract_chemistry_preserves_unicode_minus_molecule_rate_units tests/test_api.py::test_extract_chemistry_preserves_space_separated_rate_units tests/test_api.py::test_extract_chemistry_preserves_superscript_space_separated_rate_units tests/test_api.py::test_extract_chemistry_preserves_multiplication_scientific_rate_value -q`，8 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1017 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1017 passed`。
