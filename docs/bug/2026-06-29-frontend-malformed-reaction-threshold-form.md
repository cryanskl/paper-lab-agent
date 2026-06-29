# Frontend reaction review form crashed on malformed threshold values

## 现象

- 触发命令、接口或页面：Streamlit 化学库复核页展示单条 reaction 复核表单时，`reaction_review_form_state()` 会把 `reaction["threshold_ev"]` 转成 `number_input` 的默认值。
- 实际结果：当 `threshold_ev` 因历史脏数据、接口漂移或异常响应变成 `not-a-number` 等非数值字符串时，`float(...)` 抛出 `ValueError`，导致复核表单无法渲染，也无法继续人工复核或导出。
- 期望结果：异常阈值应稳定降级：不启用 threshold 输入，默认值为 `0.0`，页面继续展示 reaction 复核表单。

## 原因

- 根因：表单状态 helper 只判断 `threshold_ev is not None`，随后无条件执行 `float(reaction["threshold_ev"])`，没有校验值是否为有限数字。
- 影响范围：化学库人工复核 UI、包含 malformed threshold 历史数据的 reaction set、导出前人工复核流程。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：新增 `finite_float_or_none()`，过滤 `None`、布尔值、不可解析字符串和非有限数；`reaction_review_form_state()` 只在解析出有限数值时启用 threshold 输入。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_review_form_state_ignores_malformed_threshold -q` 失败，`threshold_ev="not-a-number"` 触发 `ValueError: could not convert string to float`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_reaction_review_form_state_ignores_malformed_threshold tests/test_frontend_api.py::test_reaction_review_form_state_normalizes_unknown_types_and_zero_threshold tests/test_frontend_api.py::test_reaction_review_form_state_preserves_known_type_indexes_and_blank_text -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含全量 pytest `1195 passed`。
