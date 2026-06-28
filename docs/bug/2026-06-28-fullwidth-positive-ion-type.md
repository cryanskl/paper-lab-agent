# Fullwidth positive ion product was truncated

## 现象

- 触发命令、接口或页面：文档章节中包含全角正号正离子产物，例如 `e + Ar -> e + e + Ar＋`。
- 实际结果：反应可以抽取成功，但 reaction 字符串被截断为 `e + Ar -> e + e + Ar`，`products` 丢失正号，`reaction_type` 为 `unknown`。
- 期望结果：反应和产物应保留原文 `Ar＋`，并推断为 `ionization`。

## 原因

- 根因：`app/services/chemistry.py` 的 `REACTION_SPECIES_CHARS` 未包含全角正号 `＋`，反应匹配在该字符前停止；`infer_reaction_type()` 也未把 `＋` 后缀识别为正离子。
- 影响范围：PDF/TEI 或复制文本中使用全角正号表示正离子时，反应式会被截断，初始反应分类和后续导出元数据都不准确。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：反应字符集允许全角正号 `＋`；正离子后缀判断同时支持 ASCII `+`、上标 `⁺` 和全角 `＋`；反应字符串和物种仍保留论文原文。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_classifies_fullwidth_positive_ion_products -q`，确认 reaction 被截断为 `e + Ar -> e + e + Ar`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_classifies_fullwidth_positive_ion_products tests/test_api.py::test_extract_chemistry_classifies_superscript_positive_ion_products tests/test_api.py::test_extract_chemistry_handles_unicode_species_subscripts_and_charges tests/test_api.py::test_extract_chemistry_classifies_unicode_minus_negative_ions tests/test_api.py::test_extract_chemistry_infers_recombination_for_positive_ion_reactant tests/test_api.py::test_extract_chemistry_infers_excitation_for_starred_product tests/test_api.py::test_extract_chemistry_infers_elastic_for_unchanged_electron_collision -q`，7 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，987 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `987 passed`。
