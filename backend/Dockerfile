# ============================================================
# AI 智能运维助手 — Backend Dockerfile
# 多阶段构建：生产环境 Python 运行时
# ============================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================================
# Runtime Stage
# ============================================================
FROM python:3.12-slim

WORKDIR /app

# 从 builder 复制已安装的包
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用代码
COPY app/ ./app/
COPY run.py .

# 创建非 root 用户
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --no-create-home appuser && \
    chown -R appuser:appgroup /app
USER appuser

# 环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx, sys; sys.exit(0 if httpx.get('http://localhost:8000/health').status_code == 200 else 1)"

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]