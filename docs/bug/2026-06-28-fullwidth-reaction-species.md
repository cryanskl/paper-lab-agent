# Fullwidth reaction species were extracted as an empty reaction

## 现象

- 触发命令、接口或页面：文档章节中包含全角字母/数字物种，例如 `ｅ + Ｏ２ -> Ｏ－ + Ｏ`。
- 实际结果：反应匹配到箭头但物种被丢失，reaction 变成 ` -> `，`reactants` 和 `products` 为空，`reaction_type` 为 `unknown`。
- 期望结果：反应、反应物和产物应保留原文 `ｅ + Ｏ２ -> Ｏ－ + Ｏ`，并根据内部归一化判断为 `attachment`。

## 原因

- 根因：`app/services/chemistry.py` 的 `REACTION_SPECIES_CHARS` 和 `SPECIES_SEPARATOR_RE` 只覆盖 ASCII 字母数字，未覆盖全角 ASCII 字母/数字；`infer_reaction_type()` 也直接比较原文 `e`，无法把全角 `ｅ` 识别为电子。
- 影响范围：PDF/TEI 或复制文本中使用全角字母/数字表示化学物种时，反应式、物种列表和初始分类都会失真。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：反应字符集和物种分隔支持全角字母/数字；分类判断对物种执行 NFKC 内部归一化；API 返回的 reaction/reactants/products 仍保留论文原文字符串。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_handles_fullwidth_species_letters_and_digits -q`，确认 reaction 为 ` -> `。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_handles_fullwidth_species_letters_and_digits tests/test_api.py::test_extract_chemistry_classifies_fullwidth_minus_negative_ions tests/test_api.py::test_extract_chemistry_classifies_unicode_minus_negative_ions tests/test_api.py::test_extract_chemistry_handles_unicode_species_subscripts_and_charges tests/test_api.py::test_extract_chemistry_classifies_fullwidth_positive_ion_products tests/test_api.py::test_extract_chemistry_classifies_superscript_positive_ion_products tests/test_api.py::test_extract_chemistry_infers_elastic_for_unchanged_electron_collision -q`，7 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，989 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `989 passed`。
