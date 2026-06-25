# 多个 LXCat URL 时反应截面链接错绑

## 现象

同一章节或表格中包含多条反应和多个 LXCat URL 时，化学抽取会把章节里的第一个 LXCat URL 绑定到所有反应。若 URL 紧跟反应式，反应正则还可能把 `https` 或下一句普通文本吞进产物，导致反应式和 `cross_section_url` 都不适合人工复核或导出。

## 原因

`extract_reactions()` 先对整个 section 调用 `detect_cross_section_url()`，然后把返回值复用到该 section 内每个 reaction。反应匹配直接运行在原文上，URL 和 URL 后的标点没有被隔离，宽松的 reaction 正则会跨过链接继续匹配。

## 修复

反应匹配前用等长空格掩掉 URL 主体，并保留 URL 末尾句号等边界标点，避免 URL 污染反应式。写入每条 reaction 时，根据 reaction 在原文中的位置选择最近的 LXCat URL；找不到局部 URL 时才回退到 section 级 URL。

## 验证

新增 `test_extract_chemistry_uses_nearest_lxcat_url_per_reaction`，覆盖同一文档章节内两条反应分别绑定两个不同 LXCat URL 的场景。完整验证以 `bash scripts/release_check.sh` 为准。
