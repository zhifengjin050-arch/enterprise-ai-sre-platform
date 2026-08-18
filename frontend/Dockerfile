# ============================================================
# AI 智能运维助手 — Frontend Dockerfile
# 多阶段构建：Node.js 构建 → Nginx 运行
# ============================================================
# 第一阶段：构建 React 应用
FROM node:20-alpine AS builder

WORKDIR /app

# 安装依赖
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# 复制源代码并构建
COPY frontend/ .
RUN npm run build

# ============================================================
# 第二阶段：Nginx 运行环境
# ============================================================
FROM nginx:alpine

# 复制 Nginx 配置
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]