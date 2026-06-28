# Fullwidth gas mixture was not extracted

## 现象

- 触发命令、接口或页面：文档章节中包含全角 ASCII 气体混合物，例如 `The ＣＦ４／Ｏ２ plasma chemistry includes ...`。
- 实际结果：反应可以抽取成功，但 reaction set 的 `gas_mixture` 为 `null`。
- 期望结果：`gas_mixture` 应保留原文气体混合物字符串 `ＣＦ４／Ｏ２`，供复核界面和导出元数据使用。

## 原因

- 根因：`app/services/chemistry.py` 的 `GAS_FORMULA_PATTERN` 只接受 ASCII 元素字母，`GAS_MIXTURE_RE` 只接受 ASCII slash `/`，无法匹配全角字母和全角 slash。
- 影响范围：PDF/TEI 或复制文本中使用全角 ASCII 时，`Ａｒ／Ｏ２`、`ＣＦ４／Ｏ２` 等气体混合物元数据会缺失。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：气体分子式 token 支持 ASCII/fullwidth 元素字母，气体式分隔符支持 `/` 和 `／`；返回值仍保留论文原文字符串，不做归一化或单位换算。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_detects_fullwidth_gas_mixture -q`，确认 `gas_mixture` 为 `None`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_detects_fullwidth_gas_mixture tests/test_api.py::test_extract_reactions_detects_subscript_gas_mixture tests/test_api.py::test_extract_reactions_detects_multi_element_gas_mixture tests/test_api.py::test_extract_reactions_detects_explicit_gas_mixture -q`，4 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，985 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `985 passed`。
