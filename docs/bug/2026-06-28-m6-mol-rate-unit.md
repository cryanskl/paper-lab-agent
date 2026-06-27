# M6 mol rate unit was truncated

## 现象

- 触发命令、接口或页面：文档章节中包含 SI 三体反应速率单位，例如 `The rate coefficient is 1.2e-42 m6 mol-2 s-1`。
- 实际结果：反应可以抽取成功，`rate_type` 为 `constant`，但 `rate_value` 只保留 `1.2e-42`，单位 `m6 mol-2 s-1` 丢失。
- 期望结果：速率值应作为原文字符串 `1.2e-42 m6 mol-2 s-1` 保留，供复核界面和导出元数据使用。

## 原因

- 根因：`app/services/chemistry.py` 的 `RATE_VALUE_RE` 已支持 `cm6 mol-2 s-1` 同类写法，也支持 `m6/s`，但 `m` 单位分支没有覆盖带 mol/molecule 指数的三体速率单位。
- 影响范围：使用 `m6 mol-2 s-1` 或同类 SI 浓度单位标注三体速率系数的表格或正文会丢失单位，降低人工复核和导出可审计性。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：速率值抽取支持 `1.2e-42 m6 mol-2 s-1`，并保留既有 `m6/s`、`cm6 molecule-2 s-1`、`cm3 mol^-1 s^-1` 和常见科学计数法行为。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_m6_mol_rate_units -q`，确认 `rate_value` 被截断为 `1.2e-42`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_cm6_rate_units tests/test_api.py::test_extract_chemistry_preserves_m6_rate_units tests/test_api.py::test_extract_chemistry_preserves_m6_mol_rate_units tests/test_api.py::test_extract_chemistry_preserves_molecule_rate_units tests/test_api.py::test_extract_chemistry_preserves_termolecular_molecule_rate_units tests/test_api.py::test_extract_chemistry_preserves_caret_molecule_rate_units tests/test_api.py::test_extract_chemistry_preserves_mol_rate_units tests/test_api.py::test_extract_chemistry_preserves_multiplication_scientific_rate_value -q`，8 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1022 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1022 passed`。
