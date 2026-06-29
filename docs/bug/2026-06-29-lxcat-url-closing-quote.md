# LXCat URL retained closing quotes

## 现象

- 触发命令、接口或页面：`extract_reactions()` 解析被引号包裹的 LXCat 截面链接，例如 `"https://nl.lxcat.net/data/set/biagi"`。
- 实际结果：`cross_section_url` 保存为 `https://nl.lxcat.net/data/set/biagi"`，尾随引号进入复核页和导出文件。
- 期望结果：保存和导出的 `cross_section_url` 应只包含可直接访问的 URL，不包含文献排版用的闭合引号。

## 原因

- 根因：上一阶段 URL 尾随分隔符规范化覆盖了句号、逗号和闭合括号，但没有覆盖单双引号；`URL_RE` 会把 URL 后的右引号包含进匹配结果。
- 影响范围：化学库反应复核页、JSON/TXT/BOLSIG 导出中的 LXCat 截面链接。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：`URL_TRAILING_DELIMITERS` 增加单双引号，`detect_cross_section_url()` 和反应匹配 URL 掩码共用同一套尾随分隔符剥离规则。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_strips_lxcat_url_closing_quote -q` 失败，实际 `cross_section_url` 为 `https://nl.lxcat.net/data/set/biagi"`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_strips_lxcat_url_closing_quote tests/test_api.py::test_extract_reactions_strips_lxcat_url_closing_bracket tests/test_api.py::test_extract_reactions_detects_lxcat_database_and_url tests/test_api.py::test_extract_reactions_skips_generic_lxcat_label_before_real_database_name tests/test_api.py::test_extract_reactions_detects_compact_lxcat_separator -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1266 passed。
