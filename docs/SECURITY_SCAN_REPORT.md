# Security Scan Report

> Generated: 2026-08-18T05:04:12
> 本报告不输出真实 API Key / JWT / 密码。

| Critical | High | Medium | Info |
|----------|------|--------|------|
| 0 | 0 | 1 | 6 |

| Severity | Check | Detail | Path |
|----------|-------|--------|------|
| info | .env 是否提交 | 无法执行 git ls-files，已确认 .gitignore 含 .env | `.gitignore` |
| info | .gitignore | .env 已加入忽略规则 | `.gitignore` |
| info | 默认 JWT Secret（示例文件） | .env.example 含开发占位符，生产启动会被拒绝 | `.env.example` |
| medium | 默认数据库密码 | compose 含默认 POSTGRES_PASSWORD/REDIS_PASSWORD 回退值，生产必须用环境变量覆盖 | `docker-compose.prod.yml` |
| info | CORS 过宽 | 当前 CORS 未使用通配符 * | `.env.example` |
| info | CORS 过宽 | 生产环境空 origins 不再回退 *（开发仍可 *） | `app/main.py` |
| info | DEBUG=true 生产风险 | 未发现 DEBUG=true | `.env` |
