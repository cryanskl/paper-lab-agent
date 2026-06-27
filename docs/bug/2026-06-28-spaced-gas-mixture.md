# Spaced gas mixture was not extracted

## 现象

- 触发命令、接口或页面：文档章节中包含斜杠两侧带空格的气体混合物，例如 `The O2 / Ar plasma chemistry includes ...`。
- 实际结果：反应可以抽取成功，但 reaction set 的 `gas_mixture` 为 `null`。
- 期望结果：`gas_mixture` 应保留原文气体混合物字符串 `O2 / Ar`，供复核界面和导出元数据使用。

## 原因

- 根因：`app/services/chemistry.py` 的 `GAS_MIXTURE_RE` 只支持紧贴 slash 的气体混合物，例如 `O2/Ar`，没有允许 `/` 或 `／` 两侧出现空白。
- 影响范围：PDF 文本抽取后保留排版空格时，气体混合物元数据缺失，降低人工复核和导出可审计性。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：气体混合物 slash 两侧允许空白，同时保留原文匹配值；`O2 / Ar`、`Ar/O2`、`CF₄/O₂`、`ＣＦ４／Ｏ２` 均可继续被抽取。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_detects_spaced_gas_mixture -q`，确认 `gas_mixture` 为 `None`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_detects_explicit_gas_mixture tests/test_api.py::test_extract_reactions_detects_multi_element_gas_mixture tests/test_api.py::test_extract_reactions_detects_spaced_gas_mixture tests/test_api.py::test_extract_reactions_detects_subscript_gas_mixture tests/test_api.py::test_extract_reactions_detects_fullwidth_gas_mixture -q`，5 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1000 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1000 passed`。
