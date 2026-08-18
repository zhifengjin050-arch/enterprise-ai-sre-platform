#!/bin/bash
# ============================================================
# AI 智能运维助手 — 一键部署脚本
# 适用环境: Linux + Docker
# ============================================================
set -euo pipefail

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  AI 智能运维助手 — 一键部署${NC}"
echo -e "${GREEN}============================================${NC}"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[错误] 未安装 Docker，请先安装 Docker${NC}"
    exit 1
fi

# 检查 Docker Compose
if ! docker compose version &> /dev/null; then
    echo -e "${RED}[错误] 未安装 Docker Compose${NC}"
    exit 1
fi

# 检查 .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[警告] .env 文件不存在，从 .env.example 复制${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}[提示] 请编辑 .env 文件填入你的 API Key 后重新运行脚本${NC}"
    else
        echo -e "${RED}[错误] .env.example 不存在，无法创建配置${NC}"
        exit 1
    fi
    exit 1
fi

echo -e "${YELLOW}[步骤 1/4] 拉取最新代码...${NC}"
# git pull  # 取消注释以在生产中使用

echo -e "${YELLOW}[步骤 2/4] 构建 Docker 镜像...${NC}"
docker compose build --pull

echo -e "${YELLOW}[步骤 3/4] 停止旧容器...${NC}"
docker compose down --remove-orphans 2>/dev/null || true

echo -e "${YELLOW}[步骤 4/4] 启动新容器...${NC}"
docker compose up -d

echo -e "${GREEN}[健康检查] 等待服务启动...${NC}"
for i in $(seq 1 12); do
    sleep 5
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}[成功] 后端服务已就绪!${NC}"
        echo -e "${GREEN}[成功] 前端: http://localhost${NC}"
        echo -e "${GREEN}[成功] API: http://localhost:8000${NC}"
        echo -e "${GREEN}[成功] 文档: http://localhost:8000/docs${NC}"
        exit 0
    fi
    echo "  等待服务启动... ($i/12)"
done

echo -e "${RED}[失败] 服务启动超时，请检查日志: docker compose logs backend${NC}"
exit 1