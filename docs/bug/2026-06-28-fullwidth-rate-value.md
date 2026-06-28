# Fullwidth scientific rate value was not extracted

## 现象

- 触发命令、接口或页面：文档章节中包含反应和全角科学计数法速率值，例如 `The rate coefficient is １．２×１０⁻¹³ cm3/s`。
- 实际结果：反应可以抽取成功，但 `rate_type` 为 `unknown`，`rate_value` 为 `null`。
- 期望结果：速率值应作为原文字符串 `１．２×１０⁻¹³ cm3/s` 保留，`rate_type` 标记为 `constant`。

## 原因

- 根因：`app/services/chemistry.py` 的 `RATE_VALUE_RE` 只匹配 ASCII 数字、小数点和 `10`，未覆盖全角数字、全角小数点和全角 `１０`。
- 影响范围：中文输入法、PDF/TEI 抽取或复制粘贴产生全角科学计数法时，化学库抽取会丢失速率值字段。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：rate value 匹配支持全角数字、全角小数点、全角指数符号和全角 `１０`；返回值仍保留论文原文字符串，不做单位换算或数值归一化。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_fullwidth_scientific_rate_value -q`，确认反应抽取成功但 `rate_type=unknown`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_fullwidth_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_explicit_rate_value_near_reaction tests/test_api.py::test_extract_chemistry_preserves_multiplication_scientific_rate_value tests/test_api.py::test_extract_chemistry_preserves_superscript_scientific_rate_value -q`，4 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，979 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `979 passed`。
