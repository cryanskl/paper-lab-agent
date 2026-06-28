# Build release handoff left invalid zip after package validation failure

## 现象

- 触发命令、接口或页面：`python scripts/build_release_handoff.py --artifact-dir out/release --package out/paper-lab-agent-release.zip --compact`
- 实际结果：如果 package 阶段产出 zip 后，最终 `validate_release_package` 复验失败，目标 zip 仍留在磁盘上。
- 期望结果：最终复验失败时删除目标 zip，确保失败的 handoff 命令不会留下可被误交付的无效包。

## 原因

- 根因：`scripts/build_release_handoff.py` 在 `validate_package` 阶段失败时直接返回失败报告，没有执行目标 package cleanup。
- 影响范围：zip 写入后被检测为损坏、缺项或不符合 release contract 的场景；报告会标记失败，但文件系统仍可能暴露无效交接包。

## 修复

- 修改文件：`scripts/build_release_handoff.py`、`tests/test_release_contracts.py`
- 关键行为：`validate_package` 失败时复用 handoff cleanup failure report，删除目标 zip；如果删除失败，失败报告返回 cleanup issue。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_build_release_handoff_removes_package_on_package_validation_failure -q` -> `1 failed`，无效 zip 仍存在。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_build_release_handoff_removes_package_on_package_validation_failure -q` -> `1 passed`
- 完整 gate：`.venv/bin/python -m pytest -q` -> `1060 passed`
