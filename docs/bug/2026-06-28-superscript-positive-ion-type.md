# Superscript positive ion product was classified as unknown

## 现象

- 触发命令、接口或页面：文档章节中包含上标正离子产物，例如 `e + Ar -> e + e + Ar⁺`。
- 实际结果：反应、反应物和产物可以抽取成功，但 `reaction_type` 为 `unknown`。
- 期望结果：该反应应被推断为 `ionization`，进入后续人工复核和导出链路。

## 原因

- 根因：`app/services/chemistry.py` 的 `infer_reaction_type()` 只把 ASCII `+` 后缀识别为正离子，未把 Unicode 上标正号 `⁺` 纳入正离子判断。
- 影响范围：PDF/TEI 或复制文本中使用上标正号表示正离子时，电离反应初始分类会缺失，增加人工复核负担。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：正离子后缀判断同时支持 ASCII `+` 和 Unicode 上标正号 `⁺`；反应字符串和物种仍保留论文原文，不做符号归一化。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_classifies_superscript_positive_ion_products -q`，确认 `reaction_type` 为 `unknown`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_classifies_superscript_positive_ion_products tests/test_api.py::test_extract_chemistry_handles_unicode_species_subscripts_and_charges tests/test_api.py::test_extract_chemistry_classifies_unicode_minus_negative_ions tests/test_api.py::test_extract_chemistry_infers_recombination_for_positive_ion_reactant tests/test_api.py::test_extract_chemistry_infers_excitation_for_starred_product tests/test_api.py::test_extract_chemistry_infers_elastic_for_unchanged_electron_collision -q`，6 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，986 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `986 passed`。
