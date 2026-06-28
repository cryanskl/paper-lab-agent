# Labelled LXCat database was misread as database

## 现象

- 触发命令、接口或页面：文档章节中包含带标签说明的 LXCat 数据库来源，例如 `LXCat database: Biagi cross section ...`。
- 实际结果：反应和 cross section URL 可以抽取成功，但 reaction set 的 `lxcat_db` 被误写为 `database`。
- 期望结果：`lxcat_db` 应抽取为真实数据库名 `Biagi`，供复核界面和导出元数据使用。

## 原因

- 根因：`app/services/chemistry.py` 的 `LXCAT_DB_RE` 固定捕获 `LXCat` 后的第一个 token。当正文使用 `LXCat database: Name` 这种标签写法时，`database` 被当成数据库名。
- 影响范围：来源表格或正文使用显式 `database` 标签时，导出元数据会包含错误数据库名，降低人工复核和可审计性。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：`LXCat database` 可作为标签前缀被跳过，继续捕获冒号、等号、短横线或空格后的真实数据库名；原有 `LXCat Biagi` 和 `LXCat: Biagi` 写法保持可用。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_detects_labelled_lxcat_database -q`，确认 `lxcat_db` 被误写为 `database`。
- GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_detects_lxcat_database_and_url tests/test_api.py::test_extract_reactions_detects_colon_lxcat_database tests/test_api.py::test_extract_reactions_detects_labelled_lxcat_database tests/test_api.py::test_extract_chemistry_uses_nearest_lxcat_url_per_reaction -q`，4 passed。
- 完整 gate：`.venv/bin/python -m pytest -q`，1002 passed。
- 发布 gate：`bash scripts/release_check.sh`，通过，包含全量 pytest `1002 passed`。
