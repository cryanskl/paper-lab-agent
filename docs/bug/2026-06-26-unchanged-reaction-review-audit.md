# 无字段变化复核未写审计

## 现象

对同一条反应重复提交相同的人工复核请求时，接口返回成功，但不会新增 `reaction_audits` 记录。这样二次确认、交叉复核或重复确认动作无法追溯，削弱化学库导出的人工复核闸门。

## 原因

`verify_reaction` 在发现请求字段与当前反应记录完全一致时直接返回 reaction set 详情，没有写入审计表。这个分支把“没有字段变化”和“没有复核动作”混为一类。

## 修复

无字段变化时仍写入一条 `reaction_audits` 记录，`action` 保留为 `verify` 或 `unverify`，`verified_by` 记录提交人，`field_changes` 为空对象，避免伪造字段变化。

## 验证

新增 `test_reaction_verify_records_audit_for_unchanged_review` 覆盖重复复核；完整验证以 `bash scripts/release_check.sh` 为准。
