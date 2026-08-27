"""数据库 ORM 模型

- User: 用户表
- Conversation: 会话表（关联 User）
- Message: 消息表（关联 Conversation）
- ManagedServer: 托管服务器表（关联 User）
- AgentExecution: Agent 执行记录表（关联 User/Conversation）
- AlertRecord: 告警记录表
- KnowledgeDocument: 知识库文档表（关联 User）
- KnowledgeChunk: 知识库文本块表（关联 KnowledgeDocument）
"""

import datetime
import json
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum as SAEnum,
    JSON, Boolean, Float, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.database.database import Base
import enum


class Organization(Base):
    """企业/组织模型"""
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="企业名称")
    slug = Column(String(100), unique=True, nullable=False, index=True, comment="企业唯一标识")
    plan = Column(String(50), default="free", comment="套餐: free/pro/enterprise")
    is_active = Column(Boolean, default=True)
    settings = Column(JSON, nullable=True, comment="企业设置")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    # Relations
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")


class OrganizationRole(str, enum.Enum):
    """企业内角色"""
    admin = "admin"
    devops = "devops"
    viewer = "viewer"


class OrganizationMember(Base):
    """企业成员关联表"""
    __tablename__ = "organization_members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(SAEnum(OrganizationRole), default=OrganizationRole.viewer, nullable=False)
    joined_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # Relations
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", backref="organization_members")

    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_org_user"),)


class UserRole(str, enum.Enum):
    """用户角色"""
    admin = "admin"
    user = "user"
    viewer = "viewer"


class User(Base):
    """用户模型"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.user, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    # 关系
    organization = relationship("Organization", backref="users", foreign_keys=[organization_id])
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    servers = relationship("ManagedServer", back_populates="user", cascade="all, delete-orphan")
    executions = relationship("AgentExecution", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class Conversation(Base):
    """会话模型"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), default="新会话", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    executions = relationship("AgentExecution", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, title={self.title})>"


class MessageRole(str, enum.Enum):
    """消息角色"""
    user = "user"
    assistant = "assistant"
    tool = "tool"


class Message(Base):
    """消息模型"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(SAEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False, default="")
    trace_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # 关系
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, role={self.role})>"


class SSHKeyType(str, enum.Enum):
    """SSH 认证类型"""
    password = "password"
    key = "key"


class ManagedServer(Base):
    """托管服务器模型"""
    __tablename__ = "managed_servers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False, comment="服务器别名")
    host = Column(String(255), nullable=False, comment="服务器 IP 或域名")
    port = Column(Integer, default=22, nullable=False, comment="SSH 端口")
    username = Column(String(100), nullable=False, comment="SSH 登录用户名")
    auth_type = Column(SAEnum(SSHKeyType), default=SSHKeyType.password, nullable=False, comment="认证类型")
    auth_credential = Column(Text, nullable=True, comment="密码或密钥（Fernet 加密存储）")
    description = Column(String(500), default="", comment="服务器描述")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User", back_populates="servers")

    def __repr__(self):
        return f"<ManagedServer(id={self.id}, name={self.name}, host={self.host})>"


class ExecutionStatus(str, enum.Enum):
    """Agent 执行状态"""
    running = "running"
    success = "success"
    failed = "failed"


class AgentExecution(Base):
    """Agent 执行记录模型"""
    __tablename__ = "agent_executions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    status = Column(SAEnum(ExecutionStatus), default=ExecutionStatus.running, nullable=False, comment="执行状态")
    duration = Column(Float, default=0.0, comment="执行耗时（秒）")
    tools_called = Column(Integer, default=0, comment="调用工具数量")
    error_message = Column(Text, nullable=True, comment="错误信息")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User", back_populates="executions")
    conversation = relationship("Conversation", back_populates="executions")

    def __repr__(self):
        return f"<AgentExecution(id={self.id}, status={self.status}, duration={self.duration})>"


class AlertLevel(str, enum.Enum):
    """告警等级"""
    info = "info"
    warning = "warning"
    critical = "critical"


class AlertStatus(str, enum.Enum):
    """告警状态"""
    firing = "firing"
    resolved = "resolved"


class AlertRecord(Base):
    """告警记录模型"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    level = Column(SAEnum(AlertLevel), nullable=False, default=AlertLevel.warning, comment="告警等级")
    title = Column(String(200), nullable=False, comment="告警标题")
    message = Column(Text, nullable=False, comment="告警消息")
    source = Column(String(100), nullable=False, default="system", comment="告警来源")
    status = Column(SAEnum(AlertStatus), default=AlertStatus.firing, nullable=False, comment="告警状态")
    ai_analysis = Column(JSON, nullable=True, comment="AI 分析结果")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<AlertRecord(id={self.id}, level={self.level}, title={self.title}, status={self.status})>"


class KnowledgeDocument(Base):
    """知识库文档模型"""
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False, comment="文档标题")
    content = Column(Text, nullable=False, comment="文档内容（原始）")
    source = Column(String(100), default="manual", comment="来源: manual/file/import/feishu")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    source_id = Column(Integer, ForeignKey("knowledge_sources.id"), nullable=True, index=True)
    external_id = Column(String(200), nullable=True, index=True)
    external_url = Column(String(500), nullable=True)
    checksum = Column(String(64), nullable=True)
    status = Column(String(20), default="active", nullable=False, comment="active/deleted")

    user = relationship("User", backref="knowledge_documents")
    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")
    knowledge_source = relationship("KnowledgeSource", back_populates="documents")

    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_kb_source_external"),
    )

    def __repr__(self):
        return f"<KnowledgeDocument(id={self.id}, title={self.title}, source={self.source})>"


class KnowledgeSource(Base):
    """企业知识源（飞书/语雀等）"""
    __tablename__ = "knowledge_sources"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    type = Column(String(40), nullable=False, comment="feishu/yuque/gitlab/confluence")
    name = Column(String(200), nullable=False)
    status = Column(String(40), default="disconnected", nullable=False)
    config_enc = Column(Text, nullable=True, comment="加密凭据 JSON")
    last_sync_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)

    organization = relationship("Organization")
    documents = relationship("KnowledgeDocument", back_populates="knowledge_source")
    tasks = relationship("SyncTask", back_populates="source", cascade="all, delete-orphan")


class SyncTask(Base):
    """知识同步任务"""
    __tablename__ = "sync_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("knowledge_sources.id"), nullable=False, index=True)
    trigger = Column(String(20), default="manual", nullable=False)
    status = Column(String(20), default="queued", nullable=False)
    stats_json = Column(JSON, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    source = relationship("KnowledgeSource", back_populates="tasks")
    logs = relationship("SyncLog", back_populates="task", cascade="all, delete-orphan")


class SyncLog(Base):
    """同步日志"""
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("sync_tasks.id"), nullable=False, index=True)
    level = Column(String(20), default="info", nullable=False)
    external_id = Column(String(200), nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    task = relationship("SyncTask", back_populates="logs")


class AgentTrace(Base):
    """Agent 执行轨迹模型（类似 LangSmith Trace）"""
    __tablename__ = "agent_traces"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    step = Column(Integer, default=0, nullable=False, comment="执行步骤序号")
    event_type = Column(String(50), nullable=False, comment="事件类型: agent_start/rag_search/memory_load/llm_start/tool_call/tool_result/final_answer")
    content = Column(Text, nullable=True, comment="事件内容/描述")
    tool_name = Column(String(100), nullable=True, comment="工具名称（如果是工具调用事件）")
    duration = Column(Float, default=0.0, comment="耗时（毫秒）")
    meta_info = Column(JSON, nullable=True, comment="附加元数据")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<AgentTrace(id={self.id}, step={self.step}, event={self.event_type})>"


class KnowledgeChunk(Base):
    """知识库文本块模型"""
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id"), nullable=False, index=True)
    content = Column(Text, nullable=False, comment="文本块内容")
    embedding = Column(Text, nullable=True, comment="向量（JSON 格式存储）")
    meta_info = Column(JSON, nullable=True, comment="附加元数据")
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    # 关系
    document = relationship("KnowledgeDocument", back_populates="chunks")

    @property
    def embedding_list(self):
        """解析 embedding JSON 为列表"""
        if not self.embedding:
            return None
        try:
            return json.loads(self.embedding)
        except (json.JSONDecodeError, TypeError):
            return None

    @embedding_list.setter
    def embedding_list(self, value):
        """将向量列表序列化为 JSON 存储"""
        self.embedding = json.dumps(value) if value else None

    def __repr__(self):
        return f"<KnowledgeChunk(id={self.id}, document_id={self.document_id})>"
