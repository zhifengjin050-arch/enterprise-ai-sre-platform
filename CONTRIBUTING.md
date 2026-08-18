# 贡献指南

感谢你对 Enterprise AI DevOps Platform 的关注！我们欢迎各种形式的贡献。

## 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发环境搭建](#开发环境搭建)
- [代码规范](#代码规范)
- [提交 PR](#提交-pr)
- [测试要求](#测试要求)

## 行为准则

本项目采用 [Contributor Covenant](https://www.contributor-covenant.org/) 行为准则。我们希望所有参与者都能：

- 友好、耐心地对待他人
- 尊重不同的观点和经验
- 建设性地接受批评
- 关注什么对社区最有利

## 如何贡献

### 报告 Bug

如果你发现了 Bug，请 [创建 Issue](https://github.com/yourusername/ai-devops-platform/issues/new) 并包含：

- Bug 的简要描述
- 复现步骤
- 预期行为与实际行为
- 环境信息（操作系统、Python 版本等）
- 相关日志或截图

### 提出新功能

如果你有新功能的想法，请先 [搜索已有 Issues](https://github.com/yourusername/ai-devops-platform/issues) 确认是否已被提出，然后创建新 Issue 描述：

- 功能的使用场景
- 期望的行为
- 可选：实现思路

### 改进文档

文档改进包括：修复错别字、补充说明、添加示例、翻译等。直接提交 PR 即可。

## 开发环境搭建

### 前置要求

- Python 3.12+
- Node.js 18+ (前端开发)
- PostgreSQL 16 (可选，开发可用 SQLite)
- Docker + Docker Compose (可选，容器部署)

### 后端设置

```bash
# 克隆仓库
git clone https://github.com/yourusername/ai-devops-platform.git
cd ai-devops-platform

# 创建虚拟环境
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 复制环境变量模板
cp .env.example .env
# 编辑 .env 填入你的 DeepSeek API Key

# 初始化数据库
python -c "from app.database.session import init_db; init_db()"

# 启动服务
python -m uvicorn app.main:app --reload --port 8000
```

### 前端设置

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### Docker 部署

```bash
docker compose up -d
```

## 代码规范

### Python

- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 编码规范
- 使用 `ruff` 进行代码检查：`ruff check app/ tests/`
- 使用 `mypy` 进行类型检查：`mypy app/`
- 所有函数和类需要包含类型注解
- 使用有意义的变量名，避免拼音命名

### TypeScript/React

- 遵循 [TypeScript 官方规范](https://www.typescriptlang.org/docs/handbook/declaration-files/do-s-and-don-ts.html)
- 使用 `eslint` 进行代码检查
- 组件使用函数式组件 + Hooks
- 使用 TypeScript 接口定义 Props 类型

### Git 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <description>

[optional body]
```

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具/依赖

示例：
```
feat(rag): 增加文档批量导入功能
fix(agent): 修复工具调用超时问题
docs(readme): 更新部署说明
```

## 提交 PR

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feat/amazing-feature`
3. 提交你的改动
4. 确保测试通过
5. 推送到你的 Fork：`git push origin feat/amazing-feature`
6. 创建 Pull Request

### PR 检查清单

- [ ] 代码遵循项目规范
- [ ] 所有测试通过
- [ ] 新增功能包含测试
- [ ] 文档已更新
- [ ] 变更记录已更新 (CHANGELOG.md)

## 测试要求

### 运行测试

```bash
# 运行所有后端测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_rag.py -v

# 运行前端测试
cd frontend && npm test

# 运行 E2E 测试
python tests/test_e2e_ok.py
```

### 测试覆盖

- 新增核心功能需包含单元测试
- API 改动需更新相关测试
- Bug 修复需添加回归测试

---

再次感谢你的贡献！如有问题，请创建 Issue 或 Discussion。