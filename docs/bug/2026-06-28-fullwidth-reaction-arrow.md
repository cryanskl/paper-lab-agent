# Fullwidth reaction arrow was not extracted

## 现象

- 触发命令、接口或页面：文档章节中包含全角箭头反应，例如 `ｅ + Ｏ２ －＞ Ｏ－ + Ｏ`。
- 实际结果：化学抽取可以创建 reaction set，但 `reactions` 为空。
- 期望结果：反应应被抽取为 `ｅ + Ｏ２ -> Ｏ－ + Ｏ`，物种保留原文，并推断为 `attachment`。

## 原因

- 根因：`app/services/chemistry.py` 的 `REACTION_ARROWS` 只包含 ASCII `->`、`=>` 和 Unicode 箭头，未覆盖中文输入法或复制文本常见的全角 `－＞`。
- 影响范围：PDF/TEI 或复制文本中使用全角箭头时，整条反应会漏抽，后续复核和导出链路缺少该反应。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：反应箭头匹配支持全角 `－＞`；输出仍统一为内部标准箭头 `->`，物种文本保留论文原文。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_handles_fullwidth_reaction_arrow -q`，确认 `reactions` 为空。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_handles_fullwidth_reaction_arrow tests/test_api.py::test_extract_chemistry_handles_fullwidth_species_letters_and_digits tests/test_api.py::test_extract_chemistry_handles_unicode_reaction_arrow tests/test_api.py::test_extract_chemistry_handles_equilibrium_reaction_arrows tests/test_api.py::test_extract_chemistry_classifies_fullwidth_minus_negative_ions -q`，5 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，990 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `990 passed`。
