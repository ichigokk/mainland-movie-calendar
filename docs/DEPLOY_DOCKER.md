# 在 NAS 或服务器上部署

容器会在启动后立即拉取一次中国大陆院线片单，之后默认每 6 小时更新。抓取失败时，
旧的 `calendar.ics` 会继续提供，并在 15 分钟后重试。更新和订阅都发生在服务器端，
Mac 无需保持开机或解锁。

## Docker Compose

1. 下载仓库中的 `compose.yaml` 和 `.env.example`。
2. 将 `.env.example` 复制为 `.env`。
3. 把 `PUBLIC_BASE_URL` 改成 Mac 能访问的 NAS 地址，例如
   `http://192.168.1.10:8000`；使用反向代理时填写 HTTPS 域名。
4. 启动服务：

```bash
docker compose pull
docker compose up -d
```

首次把本项目发布到 GitHub 后，请在仓库的 Packages 设置中确认容器包为 `Public`；
如果保持私有，则需要先在 NAS 上执行 `docker login ghcr.io`。

检查运行状态：

```bash
curl http://192.168.1.10:8000/healthz
curl -I http://192.168.1.10:8000/calendar.ics
```

健康状态说明：

- `ok`：最近一次抓取成功。
- `starting`：容器刚启动，后台首次抓取尚未完成；内置日历仍可访问。
- `degraded`：最近一次抓取失败；服务继续提供上一份有效日历并自动重试。

## 群晖 Container Manager / Portainer

在“项目”或“Stack”中粘贴 `compose.yaml`，并设置以下环境变量：

- `PUBLIC_BASE_URL`：用户访问服务的完整根地址，必须从 Mac 可达。
- `HOST_PORT`：NAS 对外端口，默认 `8000`。
- `TZ`：默认 `Asia/Shanghai`。
- `UPDATE_INTERVAL_SECONDS`：成功更新后的间隔，默认 `21600`（6 小时）。
- `RETRY_INTERVAL_SECONDS`：失败后的重试间隔，默认 `900`（15 分钟）。

数据保存在 Docker 命名卷 `movie-calendar-data` 中。重建或升级容器不会清除历史状态。

## 订阅地址

部署后，在 Apple Calendar 或 LunarBar 中订阅：

```text
http://192.168.1.10:8000/calendar.ics
```

如果需要在家庭网络之外访问，建议通过 NAS 自带的反向代理或 Caddy、Traefik、Nginx
配置 HTTPS，然后订阅：

```text
https://movies.example.com/calendar.ics
```

不要直接把容器管理端口暴露到公网；只代理本项目的 `8000` HTTP 端口即可。

## 从源码构建

如果暂时不使用 GHCR 镜像，可以直接在仓库目录构建：

```bash
docker build -t mainland-movie-calendar:local .
docker run -d \
  --name mainland-movie-calendar \
  --restart unless-stopped \
  -p 8000:8000 \
  -e PUBLIC_BASE_URL=http://192.168.1.10:8000 \
  -v mainland-movie-calendar-data:/data \
  mainland-movie-calendar:local
```

## 升级

```bash
docker compose pull
docker compose up -d
```

容器镜像升级与电影数据更新是两件事：镜像升级用于获取程序改进；影片定档数据由运行中
的容器自动拉取，无需重启或重新部署。
