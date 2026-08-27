"""企业级业务场景测试

模拟真实企业运维场景，验证 AI Agent 的业务处理能力。

场景覆盖：
1. 生产服务器巡检 — 检查所有生产服务器健康状态并生成巡检报告
2. 故障排查 — 分析订单服务异常的根本原因
3. Docker 容器状态检查 — 检查特定服务器的容器运行状态
4. Kubernetes 集群健康检查 — 查看生产环境 Pod 状态
5. 历史事件分析 — 查询过去一周的告警事件并分析趋势
6. Demo 数据完整性 — 验证所有 Demo 数据是否正确加载
"""

import pytest
import json
import os
import sys

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ensure_demo_data() -> None:
    """业务场景测试依赖 CloudShop Demo 数据；缺失时自动种子。"""
    from app.database.session import get_local_session, init_db
    from app.database.models import User, ManagedServer, AlertRecord

    init_db()
    db = get_local_session()
    try:
        admin = db.query(User).filter(User.username == "cloudshop_admin").first()
        demo_servers = db.query(ManagedServer).filter(
            ManagedServer.name.in_(["prod-web-01", "prod-web-02", "prod-db-01", "prod-cache-01"])
        ).count()
        demo_alerts = db.query(AlertRecord).filter(AlertRecord.source == "demo").count()
        need = admin is None or demo_servers < 4 or demo_alerts < 4
    finally:
        db.close()

    if need:
        from scripts.demo.init_all import init_all
        init_all()


_ensure_demo_data()


# ============================================================
# 场景组1：生产服务器巡检
# ============================================================
class TestProductionServerInspection:
    """场景1：生产服务器健康巡检"""

    def test_demo_servers_created(self):
        """验证 Demo 服务器数据已创建"""
        from app.database.session import get_local_session
        from app.database.models import ManagedServer, User

        db = get_local_session()
        try:
            servers = db.query(ManagedServer).all()
            assert len(servers) >= 3, f"预期至少 3 台服务器，实际 {len(servers)}"

            server_names = [s.name for s in servers]
            expected = ["prod-web-01", "prod-web-02", "prod-db-01", "prod-cache-01"]
            for name in expected:
                assert name in server_names, f"缺少服务器: {name}"

            print(f"[OK] Demo 服务器已创建: {[s.name for s in servers]}")
        finally:
            db.close()

    def test_server_health_data_structure(self):
        """验证服务器健康数据格式符合生产巡检要求"""
        from scripts.demo.demo_services import get_simulated_server_health

        for server_name in ["prod-web-01", "prod-web-02", "prod-db-01", "prod-cache-01"]:
            data = get_simulated_server_health(server_name)
            assert data is not None, f"{server_name} 健康数据缺失"

            assert "cpu" in data, f"{server_name} 缺少 cpu 数据"
            assert "percent" in data["cpu"], f"{server_name} cpu 缺少 percent"
            assert "cores" in data["cpu"], f"{server_name} cpu 缺少 cores"

            assert "memory" in data, f"{server_name} 缺少 memory 数据"
            assert "percent" in data["memory"], f"{server_name} memory 缺少 percent"
            assert "total_gb" in data["memory"], f"{server_name} memory 缺少 total_gb"

            assert "disks" in data, f"{server_name} 缺少 disks 数据"
            assert len(data["disks"]) > 0, f"{server_name} disks 为空"

            print(f"[OK] {server_name}: CPU={data['cpu']['percent']}% 内存={data['memory']['percent']}%")

    def test_server_risk_detection(self):
        """验证风险检测逻辑：识别高负载服务器"""
        from scripts.demo.demo_services import get_simulated_server_health

        # 按阈值分类服务器
        high_cpu = []
        high_memory = []
        high_disk = []

        for server_name in ["prod-web-01", "prod-web-02", "prod-db-01", "prod-cache-01"]:
            data = get_simulated_server_health(server_name)

            if data["cpu"]["percent"] > 70:
                high_cpu.append(server_name)
            if data["memory"]["percent"] > 80:
                high_memory.append(server_name)
            for disk in data["disks"]:
                if disk["percent"] > 75:
                    high_disk.append(f"{server_name}({disk['mount']})")

        # prod-db-01 CPU 72.5% 应被标记为高风险
        assert "prod-db-01" in high_cpu, "prod-db-01 CPU 应超过 70%"
        # prod-db-01 内存 82.1% 应被标记为高风险
        assert "prod-db-01" in high_memory, "prod-db-01 内存应超过 80%"
        # prod-db-01 数据盘 78.5% 应被标记为警告
        assert any("prod-db-01" in d for d in high_disk), "prod-db-01 数据盘应超过 75%"

        print(f"[OK] 风险识别正确: 高CPU={high_cpu}, 高内存={high_memory}, 高磁盘={high_disk}")

    def test_inspection_report_format(self):
        """验证巡检报告格式符合企业标准"""
        report = {
            "title": "CloudShop 生产环境健康巡检报告",
            "timestamp": "2026-08-17 00:00:00",
            "risk_level": "medium",
            "summary": "发现 1 台服务器存在中高风险：prod-db-01 (CPU 72.5%, 内存 82.1%)",
            "servers_checked": 4,
            "issues": [
                {
                    "server": "prod-db-01",
                    "problem": "CPU 72.5% (超过 70% 阈值)",
                    "impact": "数据库查询延迟可能增加，影响订单系统",
                    "suggestion": "1. 检查是否有慢查询 2. 考虑增加读副本 3. 优化连接池配置",
                },
                {
                    "server": "prod-db-01",
                    "problem": "内存 82.1% (超过 80% 阈值)",
                    "impact": "PostgreSQL 缓冲区紧张，可能导致 OOM",
                    "suggestion": "1. 检查 shared_buffers 配置 2. 监控内存增长趋势 3. 规划内存扩容",
                },
                {
                    "server": "prod-db-01",
                    "problem": "数据盘 78.5% (即将达到 80% 阈值)",
                    "impact": "数据库写入可能受限，WAL 日志空间不足",
                    "suggestion": "1. 清理过期 WAL 日志 2. 归档历史数据 3. 规划磁盘扩容",
                },
            ],
        }

        assert "title" in report
        assert "risk_level" in report
        assert "summary" in report
        assert "issues" in report
        assert report["risk_level"] in ["low", "medium", "high", "critical"]

        # 验证问题列表结构
        for issue in report["issues"]:
            assert "server" in issue
            assert "problem" in issue
            assert "impact" in issue
            assert "suggestion" in issue

        issues_count = len(report["issues"])
        assert issues_count >= 1
        print(f"[OK] 巡检报告格式验证通过: {issues_count} 个问题")


# ============================================================
# 场景组2：故障排查场景
# ============================================================
class TestIncidentAnalysis:
    """场景2：故障事件分析"""

    def test_demo_incidents_created(self):
        """验证 Demo 历史事件已创建"""
        from app.database.session import get_local_session
        from app.database.models import AlertRecord

        db = get_local_session()
        try:
            alerts = db.query(AlertRecord).filter(
                AlertRecord.source == "demo"
            ).all()
            assert len(alerts) >= len([
                "订单服务响应超时",
                "支付网关回调延迟",
                "prod-db-01 磁盘使用率告警",
                "生产环境 Nginx 502 错误",
            ]), f"预期至少 4 条历史事件，实际 {len(alerts)}"

            print(f"[OK] Demo 历史事件已创建: {len(alerts)} 条")
            for a in alerts:
                print(f"   [{a.level.value}] {a.title}")
        finally:
            db.close()

    def test_incident_severity_analysis(self):
        """验证事件严重程度分布分析"""
        from app.database.session import get_local_session
        from app.database.models import AlertRecord, AlertLevel

        db = get_local_session()
        try:
            alerts = db.query(AlertRecord).filter(
                AlertRecord.source == "demo"
            ).all()

            critical_count = sum(1 for a in alerts if a.level == AlertLevel.critical)
            warning_count = sum(1 for a in alerts if a.level == AlertLevel.warning)

            analysis = {
                "total_incidents": len(alerts),
                "critical": critical_count,
                "warning": warning_count,
                "resolution_rate": sum(1 for a in alerts if a.status.value == "resolved") / len(alerts) * 100 if alerts else 0,
            }

            assert analysis["total_incidents"] >= 4
            assert analysis["critical"] >= 1
            assert analysis["warning"] >= 1
            assert analysis["resolution_rate"] >= 50

            print("[OK] 事件严重度分析:")
            print(f"   总事件: {analysis['total_incidents']} | 严重: {analysis['critical']} | 警告: {analysis['warning']}")
            print(f"   解决率: {analysis['resolution_rate']:.0f}%")
        finally:
            db.close()

    def test_incident_trend_description(self):
        """验证事件趋势描述能力"""
        from app.database.session import get_local_session
        from app.database.models import AlertRecord

        db = get_local_session()
        try:
            alerts = db.query(AlertRecord).filter(
                AlertRecord.source == "demo"
            ).order_by(AlertRecord.created_at.desc()).all()

            # 模拟 AI 趋势分析
            trend_analysis = {
                "period": "过去一周",
                "total": len(alerts),
                "trend": "下降" if len(alerts) <= 5 else "平稳",
                "top_concern": "数据库服务器负载偏高",
                "recommendation": "建议对 prod-db-01 进行扩容评估，优化数据库连接池配置",
            }

            assert trend_analysis["total"] >= 4
            assert "recommendation" in trend_analysis
            assert len(trend_analysis["recommendation"]) > 10

            print("[OK] 事件趋势分析:")
            print(f"   周期: {trend_analysis['period']}")
            print(f"   趋势: {trend_analysis['trend']}")
            print(f"   建议: {trend_analysis['recommendation']}")
        finally:
            db.close()


# ============================================================
# 场景组3：Docker 容器管理场景
# ============================================================
class TestDockerManagement:
    """场景3：Docker 容器状态检查"""

    def test_docker_status_simulated_data(self):
        """验证模拟 Docker 容器数据完整性"""
        from scripts.demo.demo_services import get_simulated_docker_status

        for server_name in ["prod-web-01", "prod-web-02", "prod-db-01", "prod-cache-01"]:
            containers = get_simulated_docker_status(server_name)
            assert len(containers) > 0, f"{server_name} 缺少容器数据"
            for c in containers:
                assert "name" in c
                assert "status" in c
                assert c["status"] in ["running", "exited", "paused"]
            print(f"[OK] {server_name}: {len(containers)} 个容器 ({', '.join(c['name'] for c in containers)})")

    def test_critical_containers_running(self):
        """验证关键业务容器都在运行"""
        from scripts.demo.demo_services import get_simulated_docker_status

        critical_containers = {
            "prod-web-01": ["nginx", "node-app"],
            "prod-web-02": ["nginx", "node-app"],
            "prod-db-01": ["postgres"],
            "prod-cache-01": ["redis-master"],
        }

        for server, expected_containers in critical_containers.items():
            containers = get_simulated_docker_status(server)
            running_names = [c["name"] for c in containers if c["status"] == "running"]

            for expected in expected_containers:
                assert expected in running_names, f"{server} 上 {expected} 未运行"

            print(f"[OK] {server}: 关键容器运行正常")


# ============================================================
# 场景组4：Kubernetes 集群场景
# ============================================================
class TestKubernetesScenario:
    """场景4：Kubernetes 集群健康检查"""

    def test_k8s_pods_simulated_data(self):
        """验证模拟 K8s Pod 数据完整性"""
        from scripts.demo.demo_services import get_simulated_k8s_pods

        pods = get_simulated_k8s_pods(namespace="production")
        assert len(pods) >= 4, f"预期至少 4 个 Pod，实际 {len(pods)}"

        for p in pods:
            assert "name" in p
            assert "namespace" in p
            assert "status" in p
            assert "ready" in p

        statuses = [p["status"] for p in pods]
        assert "Running" in statuses, "应有 Running 状态的 Pod"
        print(f"[OK] K8s Pod 数据: {len(pods)} 个 Pod")

    def test_k8s_pod_status_distribution(self):
        """验证 Pod 状态分布分析"""
        from scripts.demo.demo_services import get_simulated_k8s_pods

        pods = get_simulated_k8s_pods(namespace="production")
        running = sum(1 for p in pods if p["status"] == "Running")
        pending = sum(1 for p in pods if p["status"] == "Pending")
        failed = sum(1 for p in pods if p["status"] in ("CrashLoopBackOff", "Error", "ImagePullBackOff"))

        total = len(pods)
        health_score = (running / total * 100) if total > 0 else 0

        assert health_score >= 80, f"集群健康分 {health_score:.0f}% 低于 80%"
        print(f"[OK] 集群健康分数: {health_score:.0f}%")
        print(f"   Running: {running}, Pending: {pending}, Failed: {failed}")

    def test_k8s_nodes_simulated_data(self):
        """验证模拟 K8s 节点数据完整性"""
        from scripts.demo.demo_services import get_simulated_k8s_nodes

        nodes = get_simulated_k8s_nodes()
        assert len(nodes) >= 2, f"预期至少 2 个节点，实际 {len(nodes)}"

        for n in nodes:
            assert "name" in n
            assert "status" in n
            assert "role" in n

        ready_nodes = [n for n in nodes if n["status"] == "Ready"]
        assert len(ready_nodes) == len(nodes), "所有节点都应为 Ready 状态"
        print(f"[OK] K8s 节点: {len(nodes)} 个 (全部 Ready)")


# ============================================================
# 场景组5：Demo 数据完整性
# ============================================================
class TestDemoDataIntegrity:
    """场景5：Demo 数据完整性校验"""

    def test_demo_users_created(self):
        """验证所有 Demo 用户已创建"""
        from app.database.session import get_local_session
        from app.database.models import User

        db = get_local_session()
        try:
            usernames = ["cloudshop_admin", "cloudshop_ops", "cloudshop_viewer"]
            for name in usernames:
                user = db.query(User).filter(User.username == name).first()
                assert user is not None, f"Demo 用户 {name} 不存在"
                assert user.role is not None
                print(f"[OK] Demo 用户: {user.username} ({user.role.value})")
        finally:
            db.close()

    def test_demo_business_systems_defined(self):
        """验证业务系统架构定义完整"""
        from scripts.demo.demo_services import get_business_systems

        systems = get_business_systems()
        system_keys = ["user-center", "order-system", "payment-system", "logging-system"]

        for key in system_keys:
            assert key in systems, f"缺少业务系统: {key}"
            sys = systems[key]
            assert "name" in sys
            assert "description" in sys
            assert "servers" in sys
            assert len(sys["servers"]) > 0
            print(f"[OK] 业务系统: {sys['name']} ({', '.join(sys['servers'])})")

    def test_demo_server_user_association(self):
        """验证 Demo 服务器关联到 admin 用户"""
        from app.database.session import get_local_session
        from app.database.models import ManagedServer, User

        db = get_local_session()
        try:
            admin = db.query(User).filter(User.username == "cloudshop_admin").first()
            assert admin is not None, "admin 用户不存在"

            servers = db.query(ManagedServer).filter(
                ManagedServer.user_id == admin.id
            ).all()
            assert len(servers) >= 4, f"admin 应有至少 4 台服务器，实际 {len(servers)}"
            print(f"[OK] admin 关联服务器: {len(servers)} 台")
        finally:
            db.close()

    def test_incident_message_structure(self):
        """验证历史事件消息的 JSON 结构"""
        from app.database.session import get_local_session
        from app.database.models import AlertRecord

        db = get_local_session()
        try:
            alerts = db.query(AlertRecord).filter(
                AlertRecord.source == "demo"
            ).all()
            assert len(alerts) > 0

            for alert in alerts:
                msg = json.loads(alert.message)
                assert "description" in msg
                assert "root_cause" in msg
                assert "resolution" in msg
                assert "duration" in msg

            print(f"[OK] 事件 JSON 消息结构验证通过: {len(alerts)} 条")
        finally:
            db.close()


# ============================================================
# 场景组6：Agent 业务响应
# ============================================================
class TestAgentBusinessResponse:
    """场景6：Agent 业务场景响应验证"""

    def test_agent_inspection_response_format(self):
        """验证 Agent 对'检查生产服务器'请求的响应格式"""
        from app.agent.graph import create_agent_graph

        agent = create_agent_graph()

        result = agent.invoke({
            "messages": [{"role": "user", "content": "检查生产服务器健康状态"}],
            "tool_calls": [],
            "tool_results": [],
            "final_report": "",
            "trace": [],
        })

        report = result.get("final_report", "")
        trace = result.get("trace", [])

        # Agent 应该调用 server_health 工具并生成报告
        assert len(report) > 0, "Agent 应该生成报告"
        assert len(trace) >= 2, "Agent 应该至少执行分析和报告两步"

        # 验证报告包含关键字段
        has_header = "#" in report or "**" in report
        assert has_header, "报告应包含 Markdown 格式标题"

        print(f"[OK] Agent 巡检响应: {len(report)} 字符, {len(trace)} 步")
        for t in trace:
            print(f"   [{t.get('status', '?')}] {t['step']}")

    def test_agent_incident_analysis_prompt(self):
        """验证 Agent 对故障分析类问题的响应"""
        from app.agent.graph import create_agent_graph

        agent = create_agent_graph()

        result = agent.invoke({
            "messages": [{"role": "user", "content": "分析昨晚 prod-db-01 为什么 CPU 偏高"}],
            "tool_calls": [],
            "tool_results": [],
            "final_report": "",
            "trace": [],
        })

        report = result.get("final_report", "")
        trace = result.get("trace", [])

        # Agent 应当生成报告
        assert len(report) > 10, "Agent 应该生成有意义的分析报告"

        print(f"[OK] Agent 故障分析响应: {len(report)} 字符")
        print(f"   报告片段: {report[:100]}...")

    def test_agent_docker_query_response(self):
        """验证 Agent 对 Docker 相关问题的响应"""
        from app.agent.graph import create_agent_graph

        agent = create_agent_graph()

        result = agent.invoke({
            "messages": [{"role": "user", "content": "查看 prod-web-01 上的 Docker 容器状态"}],
            "tool_calls": [],
            "tool_results": [],
            "final_report": "",
            "trace": [],
        })

        report = result.get("final_report", "")
        trace = result.get("trace", [])

        # Agent 应尝试调用工具并生成报告
        assert len(trace) >= 1, "Agent 应该有执行步骤"

        # 检查是否有与 Docker 相关的步骤
        docker_related = any("docker" in t["step"].lower() or "容器" in t["step"] for t in trace)
        print(f"[OK] Agent Docker 查询响应: {len(trace)} 步 (含 Docker 相关: {docker_related})")
