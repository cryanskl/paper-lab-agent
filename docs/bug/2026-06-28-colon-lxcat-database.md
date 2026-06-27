# Colon-separated LXCat database was not extracted

## 现象

- 触发命令、接口或页面：文档章节中包含带冒号分隔的 LXCat 数据库说明，例如 `LXCat: Biagi database cross section ...`。
- 实际结果：反应和 cross section URL 可以抽取成功，但 reaction set 的 `lxcat_db` 为 `null`。
- 期望结果：`lxcat_db` 应抽取为 `Biagi`，供复核界面和导出元数据使用。

## 原因

- 根因：`app/services/chemistry.py` 的 `LXCAT_DB_RE` 只支持 `LXCat Biagi` 这种空格分隔写法，没有允许 `LXCat` 后出现冒号等显式分隔符。
- 影响范围：来源表格或正文使用 `LXCat: Name` 标注时，数据库来源元数据缺失，降低人工复核和导出可审计性。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：`LXCat` 与数据库名之间允许冒号、等号或短横线分隔，同时保留原有空格分隔写法。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_detects_colon_lxcat_database -q`，确认 `lxcat_db` 为 `None`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_detects_lxcat_database_and_url tests/test_api.py::test_extract_reactions_detects_colon_lxcat_database tests/test_api.py::test_extract_chemistry_uses_nearest_lxcat_url_per_reaction -q`，3 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1001 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1001 passed`。
