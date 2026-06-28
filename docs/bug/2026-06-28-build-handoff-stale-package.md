# Build release handoff left stale zip after early failure

## 现象

- 触发命令、接口或页面：`python scripts/build_release_handoff.py --artifact-dir out/release --package out/paper-lab-agent-release.zip --compact`
- 实际结果：如果 export 或 artifact validation 阶段失败，目标 zip 路径上的旧 package 会继续保留。
- 期望结果：单命令 handoff 失败时不能留下旧 zip，避免操作者误把过期交接包当作本轮产物交付。

## 原因

- 根因：`scripts/build_release_handoff.py` 在 export 和 artifact validation 失败时直接返回失败报告，没有复用 package 阶段已有的 stale package cleanup 逻辑。
- 影响范围：交接目录存在脏文件、manifest/checksum 校验失败等早期失败场景；失败报告本身正确，但文件系统上仍可能残留旧 zip。

## 修复

- 修改文件：`scripts/build_release_handoff.py`、`tests/test_release_contracts.py`
- 关键行为：export 或 artifact validation 失败返回前删除目标 package 路径；如果删除失败，失败报告返回 cleanup issue。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_build_release_handoff_removes_stale_package_on_export_failure tests/test_release_contracts.py::test_build_release_handoff_removes_stale_package_on_artifact_validation_failure -q` -> `2 failed`，旧 zip 仍存在。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_build_release_handoff_removes_stale_package_on_export_failure tests/test_release_contracts.py::test_build_release_handoff_removes_stale_package_on_artifact_validation_failure -q` -> `2 passed`
- 完整 gate：`.venv/bin/python -m pytest -q` -> `1059 passed`
