# LXCat database label was misread as a database name

## 现象

- 触发命令、接口或页面：`extract_reactions()` 解析包含 `LXCat database cross section URL is ...` 的章节文本。
- 实际结果：反应集 `lxcat_db` 被误填为 `cross`，但文本并没有明确给出 LXCat 数据库名称。
- 期望结果：没有明确数据库名时，`lxcat_db` 应保持为空；包含 `lxcat` 的 URL 仍应写入反应的 `cross_section_url`。

## 原因

- 根因：`detect_lxcat_db()` 的正则在 `LXCat database` 后允许空格直接跟候选词，导致说明词 `cross` 被当作数据库名。
- 影响范围：化学库交付元数据、反应集详情、导出文件中的 LXCat 数据库来源说明。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：为 LXCat 数据库名候选增加说明词过滤；`cross`、`cross-section`、`section`、`url`、`database`、`data` 不再作为 `lxcat_db`，明确的 `Biagi` 等名称仍按原路径识别。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_does_not_treat_lxcat_database_label_as_name -q` 失败，`lxcat_db` 实际为 `cross`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_does_not_treat_lxcat_database_label_as_name tests/test_api.py::test_extract_reactions_detects_lxcat_database_and_url tests/test_api.py::test_extract_reactions_detects_colon_lxcat_database tests/test_api.py::test_extract_reactions_detects_labelled_lxcat_database tests/test_api.py::test_extract_reactions_detects_compact_lxcat_separator -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1263 passed。
