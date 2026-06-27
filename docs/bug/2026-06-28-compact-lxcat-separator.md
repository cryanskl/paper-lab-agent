# Compact LXCat separator was not extracted

## 现象

- 触发命令、接口或页面：文档章节中包含紧凑键值形式的 LXCat 数据库来源，例如 `LXCat=Biagi cross section ...`。
- 实际结果：反应和 cross section URL 可以抽取成功，但 reaction set 的 `lxcat_db` 为 `null`。
- 期望结果：`lxcat_db` 应抽取为真实数据库名 `Biagi`，供复核界面和导出元数据使用。

## 原因

- 根因：`app/services/chemistry.py` 的 `LXCAT_DB_RE` 在冒号、等号、短横线分隔符后仍要求至少一个空格，因此 `LXCat=Biagi` 这类紧凑写法无法匹配。
- 影响范围：PDF 表格或机器抽取文本把来源字段压缩成 `key=value` 时，数据库来源元数据缺失，降低人工复核和可审计性。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：`LXCat` 与数据库名之间如果存在冒号、等号或短横线分隔符，分隔符两侧空白可有可无；没有分隔符时仍要求空白分隔，避免无边界误匹配。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_detects_compact_lxcat_separator -q`，确认 `lxcat_db` 为 `None`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_detects_lxcat_database_and_url tests/test_api.py::test_extract_reactions_detects_colon_lxcat_database tests/test_api.py::test_extract_reactions_detects_labelled_lxcat_database tests/test_api.py::test_extract_reactions_detects_compact_lxcat_separator tests/test_api.py::test_extract_chemistry_uses_nearest_lxcat_url_per_reaction -q`，5 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1003 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1003 passed`。
