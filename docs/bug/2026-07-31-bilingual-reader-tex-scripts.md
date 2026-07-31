# 双语阅读把 TeX 风格上下标显示为普通文本

## 现象

双语阅读中的科学变量以 `T_e`、`k_iz(T_e)`、`P_abs`、`P^{1/2}` 等原始文本显示，
下划线和花括号直接暴露，公式难以阅读。中英文两栏都会出现。

## 原因

翻译服务会保护已经带 `$...$` 定界符的公式，但真实 GROBID/翻译产物中也包含大量没有
定界符的 TeX 风格变量。阅读器原先只允许现成的 `<sub>`、`<sup>` 标签，没有把 `_` 和
`^` 记号转换为语义化上下标节点。

## 修复

- 在阅读器安全渲染层识别带标识符边界的 `_下标`、`_{下标}`、`^上标`、`^{上标}`。
- 只生成固定的 `<sub>` / `<sup>` 节点，原始文本仍经过 HTML 转义。
- 上标允许 `1/2` 等分数，下标不吞并除号，确保 `T_e/M_i` 渲染为两个独立下标。
- 原文与译文共用同一渲染路径，不修改数据库、翻译 Markdown、检索或 RAG 内容。

## 验证

- `node --check web/app.js`
- `python -m pytest tests/test_web_ui.py -q`：59 passed
- 真实文档 21 浏览器验证：双语段落生成 307 个科学上下标节点；
  `T_e/M_i` 分拆正确；控制台无 warning/error。
- `bash scripts/release_check.sh` 的发布预检、demo、打包和 smoke 阶段通过；全量测试为
  1361 passed、42 failed。失败集中在工作区已有的向量库后端/发布文档改动，与本修复文件
  和双语阅读测试无关。
- 完整 gate：`bash scripts/release_check.sh` → `1403 passed, 5 warnings in 274.33s`；
  正式 smoke 使用 `bge-m3 + Chroma`，发布检查退出码为 0。
