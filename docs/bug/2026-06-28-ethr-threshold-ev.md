# E_thr threshold energy was not extracted

## 现象

- 触发命令、接口或页面：文档章节中包含表格式阈值能量标签，例如 `E_thr = 15.76 eV`。
- 实际结果：反应可以抽取成功，但 reaction 的 `threshold_ev` 为 `null`。
- 期望结果：`threshold_ev` 应抽取为 `15.76`，供复核界面和导出元数据使用。

## 原因

- 根因：`app/services/chemistry.py` 的 `THRESHOLD_EV_RE` 已支持 `E_th`、`Eth` 和 Unicode 下标 `Eₜₕ`，但没有覆盖 `E_thr` 简写。
- 影响范围：使用 `E_thr` 标注阈值能量的表格或正文会丢失阈值字段，降低人工复核和导出可审计性。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：阈值能量抽取支持 `E_thr = 15.76 eV`，并保留既有 `threshold energy is ... eV`、`E_th = ... eV`、`Eₜₕ = ... eV`、`Eth = ... eV`、全角数值、全角单位和多反应最近阈值绑定行为。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_reads_ethr_threshold_ev -q`，确认 `threshold_ev` 为 `None`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_chemistry_reads_explicit_threshold_ev_near_reaction tests/test_api.py::test_extract_chemistry_reads_fullwidth_threshold_ev tests/test_api.py::test_extract_chemistry_reads_fullwidth_threshold_ev_unit tests/test_api.py::test_extract_chemistry_reads_eth_threshold_ev tests/test_api.py::test_extract_chemistry_reads_subscript_eth_threshold_ev tests/test_api.py::test_extract_chemistry_reads_compact_eth_threshold_ev tests/test_api.py::test_extract_chemistry_reads_ethr_threshold_ev tests/test_api.py::test_extract_chemistry_uses_nearest_threshold_ev_per_reaction -q`，8 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1007 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1007 passed`。
