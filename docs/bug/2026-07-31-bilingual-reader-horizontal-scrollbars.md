# 双语阅读正文底部出现横向滚动条

## 现象

双语阅读的英文和中文正文栏底部都会出现横向滚动条。长 URL、DOI 或连续公式文本会把
正文内容撑出当前栏宽，用户需要左右拖动才能阅读。

## 原因

正文栏只声明了 `overflow-y: auto`。按 CSS overflow 的计算规则，横向 `visible` 会被计算
为 `auto`，所以一旦长文本超宽，浏览器就为每一栏生成横向滚动条。正文段落也没有为
无自然断点的长文本配置强制折行。

## 修复

- 阅读双栏和单栏补充 `min-width: 0`，允许 flex 子项收缩到可用宽度。
- 阅读区域明确设置 `overflow-x: hidden`，只保留需要的纵向滚动。
- 正文段落用 `overflow-wrap: anywhere` 和 `word-break: break-word` 折行长 URL、DOI
  与公式文本，避免内容被裁切。

## 验证

- `.venv/bin/python -m pytest tests/test_web_ui.py -q`：65 passed。
- 浏览器打开真实双语文档：
  - 1280px 视口下，英文、中文栏均为 `scrollWidth = clientWidth = 522px`。
  - 800px 视口下，英文、中文栏均为 `scrollWidth = clientWidth = 282px`。
  - 两种视口下 `overflow-x` 都为 `hidden`，横向滚动条数量为 0。
  - 页面控制台无 warning/error。
- 完整 gate：`bash scripts/release_check.sh` 使用的全量 pytest 已通过，`1413 passed`。
