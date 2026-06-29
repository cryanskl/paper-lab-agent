# LXCat real database names were skipped after generic labels

## 现象

- 触发命令、接口或页面：`extract_reactions()` 解析同一章节中先出现 `LXCat database cross section URL ...`，后出现明确的 `LXCat Biagi database`。
- 实际结果：第一个 generic 候选 `cross` 被过滤后，`detect_lxcat_db()` 直接返回空，后面的真实数据库名 `Biagi` 没有被识别。
- 期望结果：generic 候选应被跳过，函数继续查找后续 LXCat 候选并返回第一个真实数据库名。

## 原因

- 根因：`detect_lxcat_db()` 使用 `LXCAT_DB_RE.search()` 只检查第一个匹配；当第一个匹配是说明词时，没有继续遍历后续匹配。
- 影响范围：化学库交付元数据、反应集详情、导出文件中的 LXCat 数据库来源说明。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：`detect_lxcat_db()` 改为遍历全部 LXCat 候选，跳过说明词，返回第一个非说明词数据库名；没有真实候选时仍返回空。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_skips_generic_lxcat_label_before_real_database_name -q` 失败，`lxcat_db` 实际为 `None`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_skips_generic_lxcat_label_before_real_database_name tests/test_api.py::test_extract_reactions_does_not_treat_lxcat_database_label_as_name tests/test_api.py::test_extract_reactions_detects_lxcat_database_and_url tests/test_api.py::test_extract_reactions_detects_colon_lxcat_database tests/test_api.py::test_extract_reactions_detects_labelled_lxcat_database tests/test_api.py::test_extract_reactions_detects_compact_lxcat_separator -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1264 passed。
