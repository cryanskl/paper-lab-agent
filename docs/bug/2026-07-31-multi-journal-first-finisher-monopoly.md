# 多期刊联网检索被单一期刊独占

## 现象

同一次联网检索选择 6 本期刊、全局上限 20 篇时，6 个任务都成功，但 20 条结果可能全部来自同一本期刊。占满额度的任务还会因为逐条执行元数据增强和 OA 查询而最后完成，前端长时间显示 `5/6`。

## 原因

旧实现让每个并发期刊任务在完成候选过滤后直接锁定 `search_history.result_count`，按到达数据库事务的先后顺序预占全局额度。网络响应最快的期刊可以一次取走全部 20 个名额，结果组成受调度和网络时序影响，而不是由跨期刊检索策略决定。

OpenAlex 返回记录但缺少 `abstract_inverted_index` 时，旧实现也不会按 DOI 请求 Crossref 补全；再次同步空摘要记录还可能覆盖本地已有摘要。

## 修复

1. 将联网搜索改成两阶段：所有期刊并发召回并完成查询词复核后，再统一选择结果。
2. 选择阶段按期刊任务顺序轮询，每本期刊内部保留上游相关度顺序；无候选期刊自动让出名额，并按 DOI/保守指纹跨期刊去重。
3. 过滤 `paratext`、`editorial`、`erratum` 等明确的非研究记录。
4. 对入选且缺少摘要的 OpenAlex DOI 使用 Crossref 公开元数据做字段补全；上游仍无摘要时明确保持为空。
5. 空的上游字段不再覆盖数据库中已有的摘要和作者。

## 验证

- `tests/test_multi_journal_search.py` 覆盖跨期刊轮询、空期刊名额再分配、跨刊 DOI 去重、非论文过滤、Crossref 单 DOI 补全和已有摘要保护。
- 联网检索相关定向回归：`51 passed`。
- 完整 gate：`EMBEDDING_MODEL=local-hash VECTOR_DB_BACKEND=local-json VECTOR_DB_PATH=data/vector-index.json bash scripts/release_check.sh` → `1375 passed in 188.74s`。
