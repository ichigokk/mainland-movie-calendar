# Mainland Movie Calendar

[![CI](https://github.com/ichigokk/mainland-movie-calendar/actions/workflows/ci.yml/badge.svg)](https://github.com/ichigokk/mainland-movie-calendar/actions/workflows/ci.yml)
[![Update calendar](https://github.com/ichigokk/mainland-movie-calendar/actions/workflows/update-calendar.yml/badge.svg)](https://github.com/ichigokk/mainland-movie-calendar/actions/workflows/update-calendar.yml)
[![Docker image](https://github.com/ichigokk/mainland-movie-calendar/actions/workflows/docker.yml/badge.svg)](https://github.com/ichigokk/mainland-movie-calendar/actions/workflows/docker.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

自动更新的中国大陆院线电影日历，同时收录国产片与进口片。

## 订阅

- [打开订阅页](https://ichigokk.github.io/mainland-movie-calendar/)
- Apple Calendar / LunarBar：点击订阅页中的“订阅 Apple 日历”。
- 其他日历客户端：订阅 `https://ichigokk.github.io/mainland-movie-calendar/calendar.ics`。

订阅后，新定档影片会自动出现；提档或延期会更新原日程，不会为同一影片制造重复事件。

> 档期可能临时变化，请以片方或购票平台最新公告为准。当前数据来自豆瓣电影公开的“即将上映”页面。

## NAS / 服务器 Docker 部署（推荐）

Docker 服务不依赖 Mac 或 Codex。容器启动即更新，之后默认每 6 小时自动拉取；抓取失败
会保留上一份有效日历，并在 15 分钟后重试。

```bash
cp .env.example .env
# 修改 .env 中的 PUBLIC_BASE_URL，例如 http://192.168.1.10:8000
docker compose pull
docker compose up -d
```

部署完成后订阅：

```text
http://192.168.1.10:8000/calendar.ics
```

服务状态位于 `/healthz`。群晖 Container Manager、Portainer、反向代理和源码构建步骤见
[Docker 部署指南](docs/DEPLOY_DOCKER.md)。

## 工作方式

1. NAS/服务器容器按间隔抓取中国大陆“即将上映”片单。
2. 使用来源影片 ID 合并状态和档期变化。
3. 将状态持久化到 Docker 卷，并生成 RFC 5545 `calendar.ics` 与订阅页。
4. 容器内的 HTTP 服务直接提供订阅地址和健康状态。
5. GitHub Pages 保留为公共演示；Actions 只允许手动生成，不再设置定时任务。

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
- [Docker / NAS 部署指南](docs/DEPLOY_DOCKER.md)
- [关键决策](docs/DECISIONS.md)

## 数据与责任说明

本项目只聚合公开的影片名称、上映日期、类型和制片国家/地区等事实性元数据，不提供视频、海报或购票服务。数据源不是正式 API，若网页结构、访问策略或备用读取服务发生变化，自动更新可能暂时失败。

## License

[MIT](LICENSE)
