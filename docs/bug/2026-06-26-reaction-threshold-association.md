# 多个阈值时反应 threshold_ev 错绑

## 现象

同一章节或表格中包含多条反应和多个 `threshold ... eV` 数值时，化学抽取可能把前一条反应的阈值绑定到后续反应，导致 `threshold_ev` 与原文来源不对应。

## 原因

`detect_threshold_ev()` 在 reaction 周边窗口内直接返回第一个匹配到的 `threshold ... eV`。当后一条 reaction 的窗口仍覆盖前一条 threshold 时，前一条数值会先被匹配到。

## 修复

阈值抽取改为收集 reaction 周边窗口中的所有候选阈值，并优先选择 reaction 后方最近的候选；没有后方候选时再回退到其它最近候选。这样与论文中“反应式后跟 threshold energy”的常见写法一致，也避免同段多反应时错绑前一条阈值。

## 验证

新增 `test_extract_chemistry_uses_nearest_threshold_ev_per_reaction`，覆盖同一文档章节中两条反应分别绑定两个不同 threshold eV 数值的场景。完整验证以 `bash scripts/release_check.sh` 为准。
