# LXCat URL retained fullwidth separators

## 现象

- 触发命令、接口或页面：`extract_reactions()` 解析后接中文/全角分隔符的 LXCat 截面链接，例如 `https://nl.lxcat.net/data/set/biagi，`。
- 实际结果：`cross_section_url` 保存为 `https://nl.lxcat.net/data/set/biagi，`，尾随全角逗号进入复核页和导出文件。
- 期望结果：保存和导出的 `cross_section_url` 应只包含可直接访问的 URL，不包含文献排版用的全角分隔符。

## 原因

- 根因：URL 尾随分隔符规范化覆盖了英文逗号、句号、引号和闭合括号，但没有覆盖中文逗号、顿号、全角分号等句内分隔符；`URL_RE` 会把这些字符包含进匹配结果。
- 影响范围：化学库反应复核页、JSON/TXT/BOLSIG 导出中的 LXCat 截面链接。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：`URL_TRAILING_DELIMITERS` 增加中文逗号、顿号和全角分号，`detect_cross_section_url()` 与反应匹配 URL 掩码继续共用同一尾随分隔符剥离规则。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_strips_lxcat_url_fullwidth_separator -q` 失败，实际 `cross_section_url` 为 `https://nl.lxcat.net/data/set/biagi，`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_strips_lxcat_url_fullwidth_separator tests/test_api.py::test_extract_reactions_strips_lxcat_url_fullwidth_closing_punctuation tests/test_api.py::test_extract_reactions_strips_lxcat_url_closing_curly_quote tests/test_api.py::test_extract_reactions_strips_lxcat_url_closing_quote tests/test_api.py::test_extract_reactions_strips_lxcat_url_closing_bracket tests/test_api.py::test_extract_reactions_detects_lxcat_database_and_url tests/test_api.py::test_extract_reactions_detects_compact_lxcat_separator -q` 通过，`7 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1269 passed。
