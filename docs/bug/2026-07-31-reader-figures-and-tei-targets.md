# 双语阅读缺少论文插图并暴露 TEI 内部标记

## 现象

双语阅读仅展示解析后的段落文字，论文中的 Figure 图片没有出现在正文附近。图、参考文献和公式引用还会显示 GROBID 的内部锚点，例如 `figure 1 (#fig_0)`、`[33] (#b33)` 和 `式 (1) (#formula_0)`；译文中的 `<sup>`、`<sub>` 也会作为普通字符串显示。

## 原因

GROBID 已在 TEI 的 `<figure>`、`<graphic coords="...">` 中提供图片所在页和裁剪坐标，但原有文档服务只提取了图注，没有读取坐标或从原 PDF 生成图片。正文提取器又把所有 `<ref target>` 都拼回正文，因此把只用于 TEI 节点跳转的 `#fig_*`、`#b*`、`#formula_*` 一并暴露给读者。前端对全文统一转义，导致翻译结果中受控的科学上下标标签也无法渲染。

## 修复

1. 文档服务解析 TEI 图片编号、图注、页码与坐标，并通过受控接口从该文档的原 PDF 动态裁剪 PNG；图片路径、figure id、页码和裁剪范围均经过校验。
2. 双语阅读按正文中的 Figure 引用把图片插入对应段落之后，支持懒加载和打开原图；图注优先使用当前语言的翻译。
3. 文本提取和历史翻译读取统一清除 TEI 内部锚点，同时保留真正的外部 URL。
4. 前端只恢复严格匹配的 `<sup>`、`<sub>` 标签，其余 HTML 继续转义，兼顾科学排版和注入安全。
5. OpenAPI 发布契约路径数从 42 同步更新为 44。

## 验证

- RED：真实文档 2 的 TEI 中有 13 个 `<figure>`，旧版双语阅读无图片，并显示 `figure 1 (#fig_0)`。
- GREEN：真实 API 返回 13 张图；`fig_0` 返回 `image/png`，尺寸为 483×241；文档段落与译文均无 `(#fig_*)`、`(#b*)`、`(#formula_*)`。
- 浏览器：双语阅读正文成功显示 Figure 1，原文显示为 `figure 1.`；上下标为真实 DOM 节点，浏览器控制台无 error/warn。
- 定向回归：文档、翻译和图片相关测试 120 项通过；发布契约相关测试 38 项通过。
- 完整 gate：`EMBEDDING_MODEL=local-hash VECTOR_DB_BACKEND=local-json VECTOR_DB_PATH=data/vector-index.json .venv/bin/python -m pytest -q` → `1387 passed, 5 warnings in 232.46s`。
