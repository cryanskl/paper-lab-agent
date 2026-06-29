# LXCat URL retained closing brackets

## 现象

- 触发命令、接口或页面：`extract_reactions()` 解析带方括号引用格式的 LXCat 截面链接，例如 `[https://nl.lxcat.net/data/set/biagi]`。
- 实际结果：`cross_section_url` 保存为 `https://nl.lxcat.net/data/set/biagi]`，尾随闭合括号进入导出文件。
- 期望结果：保存和导出的 `cross_section_url` 应只包含可直接访问的 URL，不包含文献排版用的闭合分隔符。

## 原因

- 根因：`detect_cross_section_url()` 只剥离 URL 末尾的句号和逗号；`URL_RE` 会把 `]`、`}`、`>` 等闭合分隔符包含进匹配结果。
- 影响范围：化学库反应复核页、JSON/TXT/BOLSIG 导出中的 LXCat 截面链接。

## 修复

- 修改文件：`app/services/chemistry.py`、`tests/test_api.py`。
- 关键行为：统一用 `URL_TRAILING_DELIMITERS` 剥离 URL 末尾的句号、逗号和闭合分隔符；反应匹配前的 URL 掩码继续保留原文长度和尾随标点边界。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_strips_lxcat_url_closing_bracket -q` 失败，实际 `cross_section_url` 为 `https://nl.lxcat.net/data/set/biagi]`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_extract_reactions_strips_lxcat_url_closing_bracket tests/test_api.py::test_extract_reactions_detects_lxcat_database_and_url tests/test_api.py::test_extract_reactions_does_not_treat_lxcat_database_label_as_name tests/test_api.py::test_extract_reactions_skips_generic_lxcat_label_before_real_database_name tests/test_api.py::test_extract_reactions_detects_colon_lxcat_database tests/test_api.py::test_extract_reactions_detects_labelled_lxcat_database tests/test_api.py::test_extract_reactions_detects_compact_lxcat_separator -q` 通过，`7 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1265 passed。
