# Fullwidth threshold energy was not extracted

## 现象

- 触发命令、接口或页面：文档章节中包含反应和全角阈值，例如 `The threshold energy is １５．７６ eV`。
- 实际结果：反应可以抽取成功，但 `threshold_ev` 为 `null`。
- 期望结果：阈值应归一化为数值 `15.76`，进入反应集详情和后续人工复核/导出链路。

## 原因

- 根因：`app/services/chemistry.py` 的 `THRESHOLD_EV_RE` 只匹配 ASCII 数字和小数点，并直接对匹配值执行 `float()`。
- 影响范围：中文输入法、PDF/TEI 抽取或复制粘贴产生全角数字时，化学库抽取会丢失阈值字段。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：threshold 数值匹配支持全角数字和全角小数点，并在转换为 `float` 前执行 NFKC 归一化。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_reads_fullwidth_threshold_ev -q`，确认反应抽取成功但 `threshold_ev` 为 `None`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_reads_fullwidth_threshold_ev tests/test_api.py::test_extract_chemistry_reads_explicit_threshold_ev_near_reaction tests/test_api.py::test_extract_chemistry_uses_nearest_threshold_ev_per_reaction -q`，3 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，978 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `978 passed`。
