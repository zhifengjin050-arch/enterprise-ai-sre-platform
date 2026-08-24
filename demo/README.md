# Enterprise AI SRE Platform — Demo pack

三分钟跑通（不要把 `.env`、kubeconfig、SSH 密钥提交到 Git）。

## Quick start

```bash
git clone https://github.com/zhifengjin050-arch/enterprise-ai-sre-platform.git
cd enterprise-ai-sre-platform
cp .env.example .env
python scripts/demo_check.py
```

Windows:

```powershell
.\scripts\demo_start.ps1
```

Linux / macOS:

```bash
./scripts/demo_start.sh
```

打开 http://localhost ，账号 `demo_admin` / `Demo@2026!`。

| 项 | 值 |
|----|----|
| Tenant | CloudShop demo |
| User | demo_admin / `Demo@2026!` |
| 试一句 | `生产环境 payment-service 出现大量 502，请分析原因` |

脚本会 `docker compose up -d` 并运行 `python demo/import_demo_data.py`。

## 场景

| 场景 | 用户输入 | 展示能力 |
|------|----------|----------|
| K8s 502 故障排查 | 生产环境 payment-service 出现大量 502，请分析原因 | Agent + K8s Tools + RAG + Incident Report |

## 数据文件

| 文件 | 用途 |
|------|------|
| `knowledge/kubernetes_operation.md` | RAG 运维手册 |
| `knowledge/nginx_troubleshooting.md` | Nginx 排查 |
| `knowledge/production_deployment.md` | 部署规范 |
| `logs/*.log` | 日志分析样本 |
| `import_demo_data.py` | 注册 demo 账号并导入文档 |

## 截图

README 图由 `python scripts/render_readme_images.py` 从 `docs/screenshots/html/` 导出，标注 **Product preview**，占位符为 `YOUR_CLUSTER` / `YOUR_NAMESPACE`。
