# Mainland Movie Calendar

[![CI](https://github.com/ichigokk/mainland-movie-calendar/actions/workflows/ci.yml/badge.svg)](https://github.com/ichigokk/mainland-movie-calendar/actions/workflows/ci.yml)
[![Update calendar](https://github.com/ichigokk/mainland-movie-calendar/actions/workflows/update-calendar.yml/badge.svg)](https://github.com/ichigokk/mainland-movie-calendar/actions/workflows/update-calendar.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

自动更新的中国大陆院线电影日历，同时收录国产片与进口片。

## 订阅

- [打开订阅页](https://ichigokk.github.io/mainland-movie-calendar/)
- Apple Calendar / LunarBar：点击订阅页中的“订阅 Apple 日历”。
- 其他日历客户端：订阅 `https://ichigokk.github.io/mainland-movie-calendar/calendar.ics`。

订阅后，新定档影片会自动出现；提档或延期会更新原日程，不会为同一影片制造重复事件。

> 档期可能临时变化，请以片方或购票平台最新公告为准。当前数据来自豆瓣电影公开的“即将上映”页面。

## 工作方式

1. GitHub Actions 每天运行一次。
2. 抓取中国大陆“即将上映”片单。
3. 使用来源影片 ID 合并状态和档期变化。
4. 生成 RFC 5545 `calendar.ics` 与静态订阅页。
5. 只有生成物变化时才提交。

尚未上映的影片连续三次从数据源消失后，会被标记为“已撤档，待定”，不会被自动删除。
若 GitHub Actions 无法直连来源页，会自动通过 Jina Reader 获取同一页面的原始 HTML，
保持影片 ID 与合并逻辑不变。

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
mainland-movie-calendar
```

验证：

```bash
ruff check .
pytest
python -m build
```

使用本地 HTML fixture 调试而不访问网络：

```bash
mainland-movie-calendar --fixture tests/fixtures/douban-coming.html --today 2026-07-28
```

## 项目文档

- [PRD 与验收标准](docs/PRD.md)
- [关键决策](docs/DECISIONS.md)

## 数据与责任说明

本项目只聚合公开的影片名称、上映日期、类型和制片国家/地区等事实性元数据，不提供视频、海报或购票服务。数据源不是正式 API，若网页结构、访问策略或备用读取服务发生变化，自动更新可能暂时失败。

## License

[MIT](LICENSE)
