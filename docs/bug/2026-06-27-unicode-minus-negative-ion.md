# Unicode minus 负离子未识别为 attachment

## 现象

化学抽取能解析 `e + O2 -> O− + O` 这类使用 Unicode minus `−` 的负离子反应，但 `reaction_type` 被推断为 `unknown`，而不是 `attachment`。

## 原因

反应式字符集允许 Unicode minus `−`，归一化后产品会保留为 `O−`。但负离子判断只检查 ASCII `-` 和上标负号 `⁻`，没有把 Unicode minus 视为负电荷。

## 修复

在 `infer_reaction_type()` 的负离子判断中加入 Unicode minus `−`，让 `O−` 与 `O-`、`O⁻` 一样触发 attachment 分类。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_classifies_unicode_minus_negative_ions -q` 失败，`reaction_type` 为 `unknown`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_classifies_unicode_minus_negative_ions tests/test_api.py::test_extract_chemistry_handles_unicode_species_subscripts_and_charges tests/test_api.py::test_extract_chemistry_infers_excitation_for_starred_product tests/test_api.py::test_extract_chemistry_infers_recombination_for_positive_ion_reactant tests/test_api.py::test_extract_chemistry_infers_elastic_for_unchanged_electron_collision -q` 通过，`5 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`885 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `885 passed`。
