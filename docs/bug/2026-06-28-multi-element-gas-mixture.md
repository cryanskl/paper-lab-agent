# Multi-element gas mixture was not extracted

## 现象

- 触发命令、接口或页面：文档章节中包含多元素气体混合物，例如 `The CF4/O2 plasma chemistry includes ...`。
- 实际结果：反应可以抽取成功，但 reaction set 的 `gas_mixture` 为 `null`。
- 期望结果：`gas_mixture` 应保留原文气体混合物字符串 `CF4/O2`，供复核界面和导出元数据使用。

## 原因

- 根因：`app/services/chemistry.py` 的 `GAS_MIXTURE_RE` 只支持单个元素符号加可选数字再用 slash 连接，例如 `Ar/O2`。低温等离子体中常见的 `CF4/O2`、`SF6/O2`、`C2F6/O2` 属于多元素分子式，无法匹配。
- 影响范围：氟碳/含硫等多元素气体混合物的 reaction set 元数据缺失，降低人工复核和导出可审计性。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：气体分子式 token 支持一个或多个元素片段，每个片段可带数字；slash 连接多个气体式时，`CF4/O2` 这类混合物可被完整抽取。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_detects_multi_element_gas_mixture -q`，确认 `gas_mixture` 为 `None`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_detects_multi_element_gas_mixture tests/test_api.py::test_extract_reactions_detects_explicit_gas_mixture -q`，2 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，983 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `983 passed`。
