# Mixed-language author metadata displayed translated names

## 现象

- 触发命令、接口或页面：打开 `/ui/` 的文献检索结果，查看 DOI `10.1088/2058-6272/ad5fe6` 的作者行。
- 实际结果：OpenAlex 返回的 `Wenhao 文昊 ZHOU 周` 等双语姓名被完整显示，界面看起来像自动翻译了作者姓名。
- 期望结果：姓名不显示译文；双语元数据优先显示拉丁字母姓名，同时纯中文或纯英文姓名保持原样。

## 原因

- 根因：`web/app.js` 的 `authorsText()` 直接拼接标准化元数据中的 `authors.name`，没有区分双语姓名和单语姓名。
- 影响范围：同一个 OpenAlex 作者名同时包含拉丁字母与汉字时，检索结果卡片会显示两套姓名；数据库原始元数据和摘要翻译链路不受影响。

## 修复

- 修改文件：`web/app.js`、`tests/test_web_ui.py`
- 关键行为：新增纯展示函数 `untranslatedAuthorName()`；仅当姓名同时包含拉丁字母与汉字时隐藏汉字部分，保留纯中文、纯英文及其他单语姓名，不修改 API 响应或数据库记录。

## 验证

- RED 证据：修复前真实 API 返回作者名 `Wenhao 文昊 ZHOU 周`，页面也按原值显示中英双语姓名。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_web_ui.py -q` -> `40 passed`；Playwright 实页快照显示 `Wenhao ZHOU, Dongxuan ZHANG, Xiaohui DUAN, Xi ZHU, Feng LIU, Zhi FANG`。
- 完整 gate：`.venv/bin/python -m pytest -q` -> `1325 passed`
