# Underscored k rate value was not extracted

## 现象

- 触发命令、接口或页面：文档章节中包含下划线编号速率常数标签，例如 `k_1 = 1.2e-13 cm3/s`。
- 实际结果：反应可以抽取成功，但 reaction 的 `rate_type` 为 `unknown`，`rate_value` 为 `null`。
- 期望结果：`rate_type` 应为 `constant`，`rate_value` 应保留原文数值 `1.2e-13 cm3/s`，供复核界面和导出元数据使用。

## 原因

- 根因：`app/services/chemistry.py` 的 `RATE_VALUE_RE` 已支持裸 `k` 和紧凑编号 `k1`，但没有覆盖反应表中常见的下划线编号标签 `k_1`、`k_2`。
- 影响范围：使用下划线编号速率常数标签的表格或正文会丢失速率字段，降低人工复核和导出可审计性。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：速率值抽取支持 `k_1 = 1.2e-13 cm3/s`，并保留既有 `rate coefficient is ...`、`k = ...`、`k1 = ...`、间隔 e 记法和乘号科学计数法行为。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_underscored_k_rate_value -q`，确认 `rate_type` 为 `unknown`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_explicit_rate_value_near_reaction tests/test_api.py::test_extract_chemistry_preserves_numbered_k_rate_value tests/test_api.py::test_extract_chemistry_preserves_underscored_k_rate_value tests/test_api.py::test_extract_chemistry_preserves_spaced_e_notation_rate_value tests/test_api.py::test_extract_chemistry_preserves_multiplication_scientific_rate_value -q`，5 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1009 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1009 passed`。
