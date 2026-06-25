# 抓取接口空请求体被拒绝

## 现象

接口文档约定 `POST /crawl/run` 的请求体字段均可选，不传 `journal_ids` 时应默认抓取全部 active 期刊。但实际调用 `POST /api/v1/crawl/run` 且不传 JSON body 时，FastAPI 返回 422，无法触发默认手动抓取。

## 原因

`run_crawl` 路由参数把 `body: CrawlRunIn` 设为必填。虽然 `CrawlRunIn` 内部字段都有默认值，但整个请求体本身没有默认值，导致缺失 body 在进入业务逻辑前被框架校验拒绝。

## 修复

将路由参数改为可选请求体，缺失时构造 `CrawlRunIn()`，继续复用既有默认值、字段校验和任务创建逻辑。

## 验证

新增 `test_crawl_run_accepts_missing_body_with_default_all_active_journals` 覆盖空请求体默认抓取；完整验证以 `bash scripts/release_check.sh` 为准。
