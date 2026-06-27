# Fullwidth space-separated rate unit was truncated

## 现象

- 触发命令、接口或页面：文档章节中包含反应和全角空格分隔单位速率值，例如 `The rate coefficient is １．２×１０⁻¹³ ｃｍ３ ｓ－１`。
- 实际结果：反应可以抽取成功，`rate_type` 为 `constant`，但 `rate_value` 只保留 `１．２×１０⁻¹³`，单位 `ｃｍ３ ｓ－１` 丢失。
- 期望结果：速率值应作为原文字符串 `１．２×１０⁻¹³ ｃｍ３ ｓ－１` 完整保留。

## 原因

- 根因：`app/services/chemistry.py` 的 `RATE_VALUE_RE` 已支持全角单位字母和全角斜杠，但空格分隔的 `s-1` 单位只覆盖 ASCII `-1` 和上标 `⁻¹`，未覆盖全角 `ｓ－１`。
- 影响范围：PDF/TEI 抽取或复制粘贴产生全角负号和全角数字时，化学库抽取会丢失速率单位。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：rate value 单位匹配支持全角 `ｓ－１`、`s－１` 等形式；返回值仍保留论文原文字符串，不做单位换算或数值归一化。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_fullwidth_space_separated_rate_unit -q`，确认 `rate_value` 被截断为 `１．２×１０⁻¹³`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_preserves_fullwidth_space_separated_rate_unit tests/test_api.py::test_extract_chemistry_preserves_fullwidth_rate_unit tests/test_api.py::test_extract_chemistry_preserves_space_separated_rate_units tests/test_api.py::test_extract_chemistry_preserves_superscript_space_separated_rate_units -q`，4 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，981 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `981 passed`。
