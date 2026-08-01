# Release Acceptance Matrix

本文档用于发布、演示或交接前，把 PRD 阶段目标、接口契约、数据库真理来源和可重复验证命令对齐。它不是替代 PRD，而是说明“当前 checkout 如何证明 V1 可运行”。

## 真理来源

| 维度 | 来源 | Gate |
| --- | --- | --- |
| 产品范围 | `docs/PRD_等离子体文献系统.md` | `bash scripts/release_check.sh` 覆盖隔离 smoke、demo 数据和全量测试 |
| 实施顺序 | `docs/任务拆分_开发路线.md` | release gate 按阶段链路验证基础、检索、文档理解、RAG、化学库交付 |
| API 契约 | `docs/接口设计文档.md` | `python scripts/validate_api_contract.py` 与导出的 OpenAPI schema 对齐 |
| 数据模型 | `docs/schema.sql` | `python scripts/validate_schema.py` 校验 schema、种子期刊、FTS 和关键索引 |
| 发布交接 | `docs/release-checklist.md` | `python scripts/build_release_handoff.py --artifact-dir out/release --package out/paper-lab-agent-release.zip --compact` |

## 阶段覆盖

| PRD 阶段 | 发布验收点 | 主要证据 |
| --- | --- | --- |
| 阶段 0 | 服务可启动、数据库可初始化、种子期刊和分类可查询 | `python scripts/doctor.py --strict --compact`；`curl /api/v1/health`；schema validator |
| 阶段 1 | 白名单来源内的 OR/AND 联网搜索、本地搜索缓存、DOI/无 DOI 去重、OA 补全、FTS 检索和原生工作台检索入口 | `python -m scripts.smoke_check`；`python scripts/prepare_demo_data.py --summary-only --compact` |
| 阶段 2 | PDF 上传去重、解析、章节入库、公式保护翻译和翻译产物 | smoke check；demo summary 的 document/section/translation 状态 |
| 阶段 3 | 分类覆盖、分块索引、RAG 查询和引用来源 | smoke check；demo summary 的 chunk/RAG 证据 |
| 阶段 4 | 反应集抽取、人工复核闸门、审计日志、JSON/TXT/BOLSIG 导出 | demo summary 的 `export_formats`、`export_audit_entry_counts`、`reaction_set_status` |

## 必跑命令

本地发布前至少运行：

```bash
python scripts/doctor.py --strict --compact
bash scripts/release_check.sh
```

演示数据单独确认：

```bash
python scripts/prepare_demo_data.py --summary-only --compact
python scripts/prepare_demo_data.py --summary-only --compact --output out/demo-summary.json
```

live runtime 单独确认：

```bash
bash scripts/dev.sh
python scripts/health_check.py --summary-only --compact
python scripts/health_check.py --require-release-ready
python scripts/health_check.py --require-frontend
python scripts/health_check.py --require-openapi
```

交接包生成：

```bash
python scripts/build_release_handoff.py --artifact-dir out/release --package out/paper-lab-agent-release.zip --compact
```

交接包应包含：

- `openapi.json`
- `demo-summary.json`
- `release-acceptance-matrix.md`
- `release-manifest.json`

## 发布判定

可发布的最低条件：

- `bash scripts/release_check.sh` 通过。
- `python scripts/health_check.py --require-release-ready` 在目标运行环境通过。
- 需要前端演示时，`python scripts/health_check.py --require-frontend` 通过。
- 需要接口交接时，`python scripts/health_check.py --require-openapi` 或 handoff package 验证通过。
- 需要真实 GROBID 解析时，额外运行 `python scripts/health_check.py --require-grobid`；fixture 发布门禁不强制连接 GROBID。
