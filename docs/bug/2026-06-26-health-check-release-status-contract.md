# 健康检查未强制发布状态字段

## 现象

`scripts/health_check.py` 会消费 `/api/v1/system/status` 里的 `demo_data` 和 `release_readiness` 来判断演示数据与发布就绪状态，但基础状态契约没有把这两个字段列为必需字段。若 API 响应误删这些字段，普通健康检查可能只按旧字段通过或退回到间接推断，发布前门禁信号会变弱。

## 原因

`STATUS_REQUIRED_KEYS` 只包含运行时、存储、外部能力、资源计数和工作流状态字段；`demo_data` 与 `release_readiness` 只在字段存在时做形状校验，没有在最外层缺失检查中强制要求。

## 修复

把 `demo_data` 和 `release_readiness` 加入 `STATUS_REQUIRED_KEYS`，并更新健康检查测试 fixture，使有效的 `/system/status` 样例都显式包含发布数据状态和发布就绪汇总。

## 验证

新增 `test_health_check_requires_release_readiness_and_demo_data_keys` 覆盖基础契约；完整验证以 `bash scripts/release_check.sh` 为准。
