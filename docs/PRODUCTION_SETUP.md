# Production Setup Notes (v3.3.0)

> `docker-compose.prod.yml` **架构保持不变**。本文只记录必须由运维覆盖的风险与变量。  
> 生产启动：`docker compose -f docker-compose.prod.yml up -d`（与 README 一致）

## 必须替换的环境变量

在项目根 `.env` 或 Compose 环境中设置，**不要使用仓库默认值**：

| 变量 | 要求 |
|------|------|
| `ENVIRONMENT` | 必须 `production` |
| `JWT_SECRET` | 长度 ≥ 32；不得包含 `change-me` / `secret` / `password` / `test`。生成：`openssl rand -hex 32` |
| `ALLOW_REGISTER` | 生产默认关闭公开注册（compose 已设 `false`） |
| `POSTGRES_PASSWORD` | 替换默认 `devops_prod_secret` |
| `REDIS_PASSWORD` | 替换默认 `redis_prod_pass` |
| `GRAFANA_USER` / `GRAFANA_PASSWORD` | 替换默认 `admin` / `admin` |
| `SILICONFLOW_API_KEY` | 真实 Key，不要提交到 Git |
| `DOMAIN` | 生产域名（影响 CORS） |

弱 `JWT_SECRET` 在 `ENVIRONMENT=production` 时会 **拒绝启动**，错误信息：

```
JWT_SECRET is insecure for production environment
```

## 默认密码风险（compose 未改架构）

`docker-compose.prod.yml` 当前带有开发友好的默认值，**不可直接上公网**：

- PostgreSQL：`${POSTGRES_PASSWORD:-devops_prod_secret}`
- Redis：`${REDIS_PASSWORD:-redis_prod_pass}`
- Grafana：`${GRAFANA_USER:-admin}` / `${GRAFANA_PASSWORD:-admin}`

上线前必须用强密码覆盖上述变量。Grafana 默认账号风险等同于面板裸奔。

## JWT_SECRET 要求

- development：允许占位符，便于 Demo。
- production：启动门禁见 `Settings.validate_production_security()`。
- Compose **不会**自动生成 JWT。若 `.env` 仍是弱密钥，backend 容器会起不来。这是预期行为。

## Redis healthcheck 注意事项

生产 Redis 使用 `--requirepass`。当前 healthcheck 为：

```yaml
test: ["CMD", "redis-cli", "--raw", "ping"]
```

**未带 `-a $REDIS_PASSWORD`**。在要求密码时，`PING` 可能失败，backend `depends_on: redis (service_healthy)` 会一直等。

运维可选：

1. 将 healthcheck 改为 `redis-cli -a "$REDIS_PASSWORD" ping`（需自行改 compose，本版本不改架构）；或
2. 临时用无密码仅内网 Redis（不推荐生产）。

`REDIS_URL` 已包含密码：`redis://:${REDIS_PASSWORD}@redis:6379/0`，应用侧连接不受 healthcheck 文案影响。

## Grafana 默认账号

默认 `admin/admin`。必须设置 `GRAFANA_PASSWORD`。监控页未启动 Grafana 时前端走浅色占位，不代表生产已加固。

## 推荐启动检查清单

1. `.env`：强 `JWT_SECRET`、强库/Redis/Grafana 密码、有效 LLM Key。
2. `docker compose -f docker-compose.prod.yml up -d`
3. `GET /health` → `version=3.3.0`，`environment=production`
4. 使用 **admin 或 devops** 账号访问 `GET /api/system/status`（JWT 必填；普通 user 为 403）
5. 确认响应 **不含** API Key / JWT / Database URL / Redis URL / MCP 路径
