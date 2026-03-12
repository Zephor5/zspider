# zspider 基础设施说明

zspider 作为独立 GitHub 项目，应优先使用**项目内自带**的基础设施定义，不依赖某台机器上的本地绝对路径。

## 推荐方式：使用项目内 compose

在项目根目录中直接启动：

```bash
docker compose -f docker-compose.services.yml up -d
```

查看状态：

```bash
docker compose -f docker-compose.services.yml ps
```

停止：

```bash
docker compose -f docker-compose.services.yml down
```

## 当前 zspider 使用的连接信息

- MongoDB: `localhost:27017`
- RabbitMQ: `amqp://guest:guest@127.0.0.1`
- Memcached: `127.0.0.1:11211`

## 可选：复用本机共享 infra

如果你自己维护了一套共享开发中间件，也可以让 zspider 复用同等配置的 MongoDB、RabbitMQ 和 Memcached。

但这只是**本机开发便利方案**，不是 zspider 项目的默认依赖入口。

## 原则

- GitHub 项目应保持自包含，可独立启动依赖
- 共享 infra 适合作为多个项目复用的本机开发设施
- 项目文档中不应包含任何机器相关的本地绝对路径
