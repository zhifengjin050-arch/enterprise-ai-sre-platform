"""CloudShop 科技有限公司 — Demo 业务服务与模拟数据

定义企业业务系统架构和服务依赖关系。
提供可查询的模拟业务数据接口。
"""

import logging

logger = logging.getLogger(__name__)

# ============================================================
# CloudShop 业务系统架构
# ============================================================

COMPANY_INFO = {
    "name": "CloudShop 科技有限公司",
    "industry": "电子商务",
    "website": "https://www.cloudshop.com",
    "description": "一家快速成长的电商平台，提供在线购物、支付、物流等服务。",
}

BUSINESS_SYSTEMS = {
    "user-center": {
        "name": "用户中心",
        "description": "用户注册、登录、权限管理",
        "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
        "servers": ["prod-web-01", "prod-web-02", "prod-db-01"],
        "k8s_namespace": "production",
        "k8s_service": "user-service",
        "criticality": "high",
    },
    "order-system": {
        "name": "订单系统",
        "description": "订单创建、支付处理、物流跟踪",
        "tech_stack": ["Java", "Spring Boot", "MySQL", "Redis"],
        "servers": ["prod-web-01", "prod-web-02", "prod-db-01", "prod-cache-01"],
        "k8s_namespace": "production",
        "k8s_service": "order-service",
        "criticality": "critical",
    },
    "payment-system": {
        "name": "支付系统",
        "description": "支付网关、账单管理、退款处理",
        "tech_stack": ["Go", "gRPC", "PostgreSQL", "Kafka"],
        "servers": ["prod-web-02", "prod-db-01"],
        "k8s_namespace": "production",
        "k8s_service": "payment-service",
        "criticality": "critical",
    },
    "logging-system": {
        "name": "日志系统",
        "description": "集中式日志采集、存储、检索",
        "tech_stack": ["Elasticsearch", "Logstash", "Kibana", "Filebeat"],
        "servers": ["prod-web-01", "prod-web-02"],
        "k8s_namespace": "production",
        "k8s_service": None,
        "criticality": "medium",
    },
}

SERVICE_DEPENDENCIES = {
    "user-center": [],
    "order-system": ["user-center", "payment-system"],
    "payment-system": ["user-center"],
    "logging-system": [],
}


# ============================================================
# 模拟 Docker 容器状态（离线数据，不依赖真实 Docker）
# ============================================================
SIMULATED_DOCKER_STATUS = {
    "prod-web-01": [
        {"name": "nginx", "status": "running", "uptime": "15d", "ports": ["80:80", "443:443"]},
        {"name": "node-app", "status": "running", "uptime": "15d", "ports": ["3000:3000"]},
        {"name": "filebeat", "status": "running", "uptime": "15d", "ports": []},
    ],
    "prod-web-02": [
        {"name": "nginx", "status": "running", "uptime": "15d", "ports": ["80:80", "443:443"]},
        {"name": "node-app", "status": "running", "uptime": "15d", "ports": ["3000:3000"]},
        {"name": "filebeat", "status": "running", "uptime": "15d", "ports": []},
    ],
    "prod-db-01": [
        {"name": "postgres", "status": "running", "uptime": "30d", "ports": ["5432:5432"]},
        {"name": "pgbouncer", "status": "running", "uptime": "30d", "ports": ["6432:6432"]},
    ],
    "prod-cache-01": [
        {"name": "redis-master", "status": "running", "uptime": "20d", "ports": ["6379:6379"]},
        {"name": "redis-slave", "status": "running", "uptime": "20d", "ports": ["6380:6380"]},
    ],
}


# ============================================================
# 模拟服务器健康数据（离线数据）
# ============================================================
SIMULATED_SERVER_HEALTH = {
    "prod-web-01": {
        "cpu": {"percent": 45.2, "cores": 8},
        "memory": {"percent": 62.3, "total_gb": 32.0, "used_gb": 19.9, "free_gb": 12.1},
        "disks": [{"mount": "/", "percent": 55.0, "total_gb": 200.0, "used_gb": 110.0, "free_gb": 90.0}],
    },
    "prod-web-02": {
        "cpu": {"percent": 52.8, "cores": 8},
        "memory": {"percent": 68.7, "total_gb": 32.0, "used_gb": 22.0, "free_gb": 10.0},
        "disks": [{"mount": "/", "percent": 58.0, "total_gb": 200.0, "used_gb": 116.0, "free_gb": 84.0}],
    },
    "prod-db-01": {
        "cpu": {"percent": 72.5, "cores": 16},
        "memory": {"percent": 82.1, "total_gb": 64.0, "used_gb": 52.5, "free_gb": 11.5},
        "disks": [
            {"mount": "/", "percent": 45.0, "total_gb": 100.0, "used_gb": 45.0, "free_gb": 55.0},
            {"mount": "/data", "percent": 78.5, "total_gb": 500.0, "used_gb": 392.5, "free_gb": 107.5},
        ],
    },
    "prod-cache-01": {
        "cpu": {"percent": 35.1, "cores": 8},
        "memory": {"percent": 45.6, "total_gb": 32.0, "used_gb": 14.6, "free_gb": 17.4},
        "disks": [{"mount": "/", "percent": 35.0, "total_gb": 100.0, "used_gb": 35.0, "free_gb": 65.0}],
    },
}


# ============================================================
# 模拟 Kubernetes Pod 数据（离线数据）
# ============================================================
SIMULATED_K8S_PODS = [
    {"name": "user-service-7d8b6f8d9c-abcde", "namespace": "production", "status": "Running", "ready": "1/1", "restarts": 0},
    {"name": "user-service-7d8b6f8d9c-fghij", "namespace": "production", "status": "Running", "ready": "1/1", "restarts": 0},
    {"name": "order-service-9f4k2d7a1b-klmno", "namespace": "production", "status": "Running", "ready": "2/2", "restarts": 1},
    {"name": "order-service-9f4k2d7a1b-pqrst", "namespace": "production", "status": "Running", "ready": "2/2", "restarts": 0},
    {"name": "payment-service-3b7c1d5e2f-uvwxy", "namespace": "production", "status": "Running", "ready": "1/1", "restarts": 0},
    {"name": "payment-service-3b7c1d5e2f-zabcd", "namespace": "production", "status": "Running", "ready": "1/1", "restarts": 0},
]

SIMULATED_K8S_NODES = [
    {"name": "k8s-node-01", "status": "Ready", "role": "worker", "cpu": "8", "memory": "32Gi"},
    {"name": "k8s-node-02", "status": "Ready", "role": "worker", "cpu": "8", "memory": "32Gi"},
    {"name": "k8s-master-01", "status": "Ready", "role": "master", "cpu": "4", "memory": "16Gi"},
]


def get_company_info() -> dict:
    """获取公司信息"""
    return COMPANY_INFO


def get_business_systems() -> dict:
    """获取业务系统架构"""
    return BUSINESS_SYSTEMS


def get_simulated_server_health(server_name: str) -> dict | None:
    """获取模拟的服务器健康数据"""
    return SIMULATED_SERVER_HEALTH.get(server_name)


def get_simulated_docker_status(server_name: str) -> list:
    """获取模拟的 Docker 容器状态"""
    return SIMULATED_DOCKER_STATUS.get(server_name, [])


def get_simulated_k8s_pods(namespace: str = "production") -> list:
    """获取模拟的 K8s Pod 列表"""
    return [p for p in SIMULATED_K8S_PODS if p["namespace"] == namespace]


def get_simulated_k8s_nodes() -> list:
    """获取模拟的 K8s 节点列表"""
    return SIMULATED_K8S_NODES


if __name__ == "__main__":
    print("=" * 60)
    print("  CloudShop 科技有限公司 — Demo 业务服务数据")
    print("=" * 60)

    info = get_company_info()
    print(f"\n[Company] {info['name']}")
    print(f"   行业: {info['industry']}")
    print(f"   网站: {info['website']}")

    print(f"\n[Systems] 业务系统 ({len(BUSINESS_SYSTEMS)} 个):")
    for key, sys in BUSINESS_SYSTEMS.items():
        deps = SERVICE_DEPENDENCIES.get(key, [])
        dep_names = ", ".join(BUSINESS_SYSTEMS[d]["name"] for d in deps) if deps else "无"
        print(f"   - {sys['name']} [关键等级: {sys['criticality']}]")
        print(f"     技术栈: {', '.join(sys['tech_stack'])}")
        print(f"     依赖: {dep_names}")

    print(f"\n[Servers] 服务器 ({len(SIMULATED_SERVER_HEALTH)} 台):")
    for name in SIMULATED_SERVER_HEALTH:
        print(f"   - {name}")

    print(f"\n[K8s] K8s Pod ({len(SIMULATED_K8S_PODS)} 个):")
    for p in SIMULATED_K8S_PODS:
        print(f"   - {p['name']} ({p['status']})")

    print("\n[OK] Demo 业务数据加载完成")
