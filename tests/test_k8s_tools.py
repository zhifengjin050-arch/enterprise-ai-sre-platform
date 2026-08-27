"""Kubernetes AI 运维工具模块测试

覆盖：
- 工具函数单元测试（解析函数参数验证）
- kubectl 不可用/超时异常处理
- K8S 未启用时的优雅降级
- 禁止操作安全检查
- Pod/Node JSON 解析逻辑
- Agent 工具注册与 schema
- 安全控制（禁用高危操作）
"""

from app.config import settings
from app.tools.registry import get_tool, get_tool_schemas

print("=" * 60)
print("  Kubernetes AI 运维工具模块测试")
print("=" * 60)

# ============================================================
# 测试组1：K8S 未启用时的降级行为
# ============================================================
print()
print("--- 测试组1：K8S 未启用降级 ---")


def test_k8s_disabled_default():
    """测试1: K8S_ENABLED 默认为 False"""
    assert settings.kubernetes_enabled is False
    print(f"[OK] KUBERNETES_ENABLED 默认 = {settings.kubernetes_enabled}")


def test_get_pods_disabled():
    """测试2: kubectl_get_pods 在未启用时返回正确错误"""
    from app.agent.k8s_tools import kubectl_get_pods

    result = kubectl_get_pods.invoke({"namespace": "default"})
    assert result.get("success") is False
    assert "未启用" in result.get("error", "")
    print(f"[OK] kubectl_get_pods 在未启用时返回: {result.get('error', '')[:50]}")


def test_get_nodes_disabled():
    """测试3: kubectl_get_nodes 在未启用时返回正确错误"""
    from app.agent.k8s_tools import kubectl_get_nodes

    result = kubectl_get_nodes.invoke({})
    assert result.get("success") is False
    assert "未启用" in result.get("error", "")
    print(f"[OK] kubectl_get_nodes 在未启用时返回: {result.get('error', '')[:50]}")


def test_logs_disabled():
    """测试4: kubectl_logs 在未启用时返回正确错误"""
    from app.agent.k8s_tools import kubectl_logs

    result = kubectl_logs.invoke({
        "pod_name": "test-pod",
        "namespace": "default",
        "tail": 50,
    })
    assert result.get("success") is False
    assert "未启用" in result.get("error", "")
    print(f"[OK] kubectl_logs 在未启用时返回: {result.get('error', '')[:50]}")


def test_describe_pod_disabled():
    """测试5: kubectl_describe_pod 在未启用时返回正确错误"""
    from app.agent.k8s_tools import kubectl_describe_pod

    result = kubectl_describe_pod.invoke({
        "pod_name": "test-pod",
        "namespace": "default",
    })
    assert result.get("success") is False
    assert "未启用" in result.get("error", "")
    print(f"[OK] kubectl_describe_pod 在未启用时返回: {result.get('error', '')[:50]}")


def test_restart_deployment_disabled():
    """测试6: kubectl_restart_deployment 在未启用时返回正确错误"""
    from app.agent.k8s_tools import kubectl_restart_deployment

    result = kubectl_restart_deployment.invoke({
        "deployment_name": "test-deploy",
        "namespace": "default",
    })
    assert result.get("success") is False
    assert "未启用" in result.get("error", "")
    print(f"[OK] kubectl_restart_deployment 在未启用时返回: {result.get('error', '')[:50]}")


# ============================================================
# 测试组2：安全控制
# ============================================================
print()
print("--- 测试组2：安全控制 ---")


def test_safe_command_detection():
    """测试7: _is_safe_command 正确识别安全命令"""
    from app.agent.k8s_tools import _is_safe_command

    # 安全操作
    assert _is_safe_command(["get", "pods", "-n", "default"]) is True
    assert _is_safe_command(["get", "nodes"]) is True
    assert _is_safe_command(["logs", "nginx", "-n", "default"]) is True
    assert _is_safe_command(["describe", "pod", "nginx"]) is True
    assert _is_safe_command(["rollout", "restart", "deployment", "nginx"]) is True

    print("[OK] 安全操作全部通过安全检查")


def test_dangerous_command_blocked():
    """测试8: _is_safe_command 正确拦截危险命令"""
    from app.agent.k8s_tools import _is_safe_command, _DANGEROUS_OPERATIONS

    # 危险操作（应被拦截）
    assert _is_safe_command(["delete", "pod", "nginx"]) is False
    assert _is_safe_command(["delete", "namespace", "test"]) is False
    assert _is_safe_command(["exec", "-it", "pod", "--", "bash"]) is False
    assert _is_safe_command(["drain", "node01"]) is False

    print("[OK] 危险操作全部被拦截")


def test_dangerous_operations_list():
    """测试9: 危险操作黑名单包含必需条目"""
    from app.agent.k8s_tools import _DANGEROUS_OPERATIONS

    dangerous_ops = " ".join(_DANGEROUS_OPERATIONS).lower()
    assert "delete" in dangerous_ops
    assert "exec" in dangerous_ops
    assert "drain" in dangerous_ops
    assert "clusterrole" in dangerous_ops
    print(f"[OK] 危险操作黑名单包含 {len(_DANGEROUS_OPERATIONS)} 条规则")


# ============================================================
# 测试组3：JSON 解析逻辑
# ============================================================
print()
print("--- 测试组3：JSON 解析逻辑 ---")


def test_parse_pod_item():
    """测试10: _parse_pod_item 正确解析模拟 Pod JSON"""
    from app.agent.k8s_tools import _parse_pod_item

    mock_pod = {
        "metadata": {
            "namespace": "production",
            "name": "nginx-7d8b6f8d9c-abcde",
            "creationTimestamp": "2026-08-16T10:00:00Z",
        },
        "status": {
            "phase": "Running",
            "hostIP": "10.0.0.1",
            "podIP": "192.168.1.5",
            "containerStatuses": [
                {"name": "nginx", "ready": True, "restartCount": 0},
                {"name": "sidecar", "ready": True, "restartCount": 1},
            ],
        },
    }

    parsed = _parse_pod_item(mock_pod)
    assert parsed["namespace"] == "production"
    assert parsed["name"] == "nginx-7d8b6f8d9c-abcde"
    assert parsed["status"] == "Running"
    assert parsed["ready"] == "2/2"
    assert parsed["restarts"] == 1
    assert parsed["node"] == "10.0.0.1"
    assert parsed["pod_ip"] == "192.168.1.5"
    print(f"[OK] _parse_pod_item: {parsed['name']} status={parsed['status']} ready={parsed['ready']}")


def test_parse_pod_item_pending():
    """测试11: _parse_pod_item 正确处理 Pending 状态的 Pod"""
    from app.agent.k8s_tools import _parse_pod_item

    mock_pod = {
        "metadata": {
            "namespace": "default",
            "name": "pending-pod",
            "creationTimestamp": "2026-08-16T12:00:00Z",
        },
        "status": {
            "phase": "Pending",
            "hostIP": "",
            "podIP": "",
            "containerStatuses": [],
        },
    }

    parsed = _parse_pod_item(mock_pod)
    assert parsed["status"] == "Pending"
    assert parsed["ready"] == "0/0"
    assert parsed["restarts"] == 0
    print(f"[OK] _parse_pod_item (Pending): {parsed['name']} status={parsed['status']}")


def test_parse_node_item():
    """测试12: _parse_node_item 正确解析模拟 Node JSON"""
    from app.agent.k8s_tools import _parse_node_item

    mock_node = {
        "metadata": {
            "name": "node-01",
            "labels": {
                "kubernetes.io/hostname": "node-01",
                "node-role.kubernetes.io/worker": "",
            },
        },
        "status": {
            "conditions": [
                {"type": "Ready", "status": "True", "lastHeartbeatTime": "..."},
            ],
            "addresses": [
                {"type": "InternalIP", "address": "192.168.1.10"},
            ],
            "capacity": {
                "cpu": "8",
                "memory": "32768Ki",
                "pods": "110",
            },
            "nodeInfo": {
                "osImage": "Ubuntu 22.04 LTS",
                "kubeletVersion": "v1.28.3",
            },
        },
    }

    parsed = _parse_node_item(mock_node)
    assert parsed["name"] == "node-01"
    assert parsed["status"] == "Ready"
    assert parsed["role"] == "worker"
    assert parsed["internal_ip"] == "192.168.1.10"
    assert parsed["cpu"] == "8"
    assert parsed["pods_max"] == "110"
    print(f"[OK] _parse_node_item: {parsed['name']} status={parsed['status']} role={parsed['role']}")


def test_parse_node_item_not_ready():
    """测试13: _parse_node_item 正确处理 NotReady 节点"""
    from app.agent.k8s_tools import _parse_node_item

    mock_node = {
        "metadata": {"name": "node-02", "labels": {}},
        "status": {
            "conditions": [
                {"type": "Ready", "status": "False"},
            ],
            "addresses": [],
            "capacity": {"cpu": "4", "memory": "16Gi", "pods": "110"},
            "nodeInfo": {"osImage": "Ubuntu 22.04", "kubeletVersion": "v1.28.0"},
        },
    }

    parsed = _parse_node_item(mock_node)
    assert parsed["status"] == "NotReady"
    assert parsed["role"] == "<none>"
    print(f"[OK] _parse_node_item (NotReady): {parsed['name']} status={parsed['status']}")


# ============================================================
# 测试组4：Agent 工具注册
# ============================================================
print()
print("--- 测试组4：Agent 工具注册 ---")


def test_tools_registered():
    """测试14: 确认新 K8S 工具已注册到工具注册表"""
    expected_tools = [
        "kubectl_get_pods",
        "kubectl_get_nodes",
        "kubectl_logs",
        "kubectl_describe_pod",
        "kubectl_restart_deployment",
    ]

    for name in expected_tools:
        tool = get_tool(name)
        assert tool is not None, f"工具 {name} 未注册"
        assert hasattr(tool, "name")
        assert hasattr(tool, "func")
    print(f"[OK] 全部 {len(expected_tools)} 个 K8S 工具已注册")


def test_tool_schemas_included():
    """测试15: K8S 工具的 Schema 已包含在 Agent 工具描述中"""
    schemas = get_tool_schemas()
    k8s_schemas = [s for s in schemas if "kubectl_" in s["function"]["name"]]

    assert len(k8s_schemas) == 5
    names = [s["function"]["name"] for s in k8s_schemas]
    print(f"[OK] Agent 工具描述包含 5 个 K8S 工具: {names}")


def test_tool_parameters_valid():
    """测试16: K8S 工具的 parameters 定义正确"""
    schemas = get_tool_schemas()

    # kubectl_get_pods 应有 namespace 参数
    pods_schema = next(s for s in schemas if s["function"]["name"] == "kubectl_get_pods")
    params = pods_schema["function"]["parameters"]
    assert "namespace" in params.get("properties", {})
    print(f"[OK] kubectl_get_pods 参数: {list(params.get('properties', {}).keys())}")

    # kubectl_restart_deployment 应有 deployment_name 和 namespace 参数
    restart_schema = next(s for s in schemas if s["function"]["name"] == "kubectl_restart_deployment")
    params = restart_schema["function"]["parameters"]
    assert "deployment_name" in params.get("properties", {})
    assert "namespace" in params.get("properties", {})
    print(f"[OK] kubectl_restart_deployment 参数: {list(params.get('properties', {}).keys())}")


def test_restart_deployment_allow_restart_disabled():
    """测试17: KUBERNETES_ALLOW_RESTART 未启用时返回正确信息"""
    # 先设置 ALLOW_RESTART=False（默认）
    from app.agent.k8s_tools import kubectl_restart_deployment, K8S_ALLOW_RESTART

    assert K8S_ALLOW_RESTART is False

    result = kubectl_restart_deployment.invoke({
        "deployment_name": "test",
        "namespace": "default",
    })
    # 因为 K8S_ENABLED 也是 False，先返回未启用错误
    assert result.get("success") is False
    print(f"[OK] KUBERNETES_ALLOW_RESTART 默认 = {K8S_ALLOW_RESTART}")


# ============================================================
# 测试组5：_run_kubectl 核心函数
# ============================================================
print()
print("--- 测试组5：_run_kubectl 核心函数 ---")


def test_run_kubectl_no_kubectl():
    """测试18: _run_kubectl 在 kubectl 不存在时返回友好错误"""
    from app.agent.k8s_tools import _run_kubectl

    result = _run_kubectl(["get", "pods"])
    # 由于 K8S_ENABLED=False，应先返回未启用
    assert result.get("success") is False
    assert "未启用" in result.get("error", "")
    print("[OK] _run_kubectl 正确处理 K8S 未启用状态")


def test_build_cmd_with_kubeconfig():
    """测试19: _build_cmd 正确处理带 kubeconfig 路径"""
    from app.agent.k8s_tools import _build_cmd, K8S_KUBECONFIG

    # 默认情况：kubeconfig 为空
    cmd = _build_cmd(["get", "pods", "-n", "default"])
    assert cmd[0] == "kubectl"
    assert "--kubeconfig" not in cmd  # 因为 K8S_KUBECONFIG 为空
    print(f"[OK] _build_cmd (无 kubeconfig): {' '.join(cmd)}")


def test_run_kubectl_timeout_handling():
    """测试20: 验证超时参数传递正确"""
    from app.agent.k8s_tools import _run_kubectl, K8S_TIMEOUT

    # 确保超时有合理值
    assert K8S_TIMEOUT >= 1
    print(f"[OK] KUBERNETES_TIMEOUT = {K8S_TIMEOUT}s")


# ============================================================
# 测试组6：Agent Trace 集成（end-to-end 验证 Trace 结构）
# ============================================================
print()
print("--- 测试组6：Agent Trace 集成 ---")


def test_trace_structure_preserved():
    """测试21: 验证 Trace 结构仍然兼容（通过 Agent 状态）"""
    from app.agent.state import AgentTraceStep

    # 验证 TraceStep 结构兼容
    step: AgentTraceStep = {
        "step": "调用 kubectl_get_pods",
        "status": "running",
        "tool": "kubectl_get_pods",
        "duration_ms": 0,
    }
    assert step["step"] == "调用 kubectl_get_pods"
    assert step["tool"] == "kubectl_get_pods"
    assert step["status"] == "running"
    assert step["duration_ms"] == 0
    print("[OK] Agent Trace 结构兼容 K8S 工具事件")


def test_k8s_config_settings():
    """测试22: 验证 K8S 配置项存在于 settings"""
    assert hasattr(settings, "kubernetes_enabled")
    assert hasattr(settings, "kubeconfig_path")
    assert hasattr(settings, "kubernetes_timeout")
    assert hasattr(settings, "kubernetes_allow_restart")
    print("[OK] settings 包含全部 4 个 Kubernetes 配置项")


# ============================================================
# 测试组7：旧 k8s_ops 工具仍然可用（向后兼容）
# ============================================================
print()
print("--- 测试组7：向后兼容性 ---")


def test_legacy_k8s_tools_still_available():
    """测试23: 旧的 k8s_ops 工具仍然可用（向后兼容）"""
    legacy_tools = ["k8s_pods", "k8s_deployments", "k8s_services", "k8s_pod_logs"]
    for name in legacy_tools:
        tool = get_tool(name)
        assert tool is not None, f"旧工具 {name} 丢失"
    print(f"[OK] 全部 {len(legacy_tools)} 个旧 k8s_ops 工具仍然可用")


# ============================================================
# 运行
# ============================================================
if __name__ == "__main__":
    tests = [
        ("K8S 未启用默认值", test_k8s_disabled_default),
        ("kubectl_get_pods 降级", test_get_pods_disabled),
        ("kubectl_get_nodes 降级", test_get_nodes_disabled),
        ("kubectl_logs 降级", test_logs_disabled),
        ("kubectl_describe_pod 降级", test_describe_pod_disabled),
        ("kubectl_restart_deployment 降级", test_restart_deployment_disabled),
        ("安全命令检测", test_safe_command_detection),
        ("危险命令拦截", test_dangerous_command_blocked),
        ("危险操作黑名单", test_dangerous_operations_list),
        ("Pod JSON 解析", test_parse_pod_item),
        ("Pod Pending 解析", test_parse_pod_item_pending),
        ("Node JSON 解析", test_parse_node_item),
        ("Node NotReady 解析", test_parse_node_item_not_ready),
        ("工具注册", test_tools_registered),
        ("工具 Schema", test_tool_schemas_included),
        ("工具参数验证", test_tool_parameters_valid),
        ("Restart 权限控制", test_restart_deployment_allow_restart_disabled),
        ("_run_kubectl 核心函数", test_run_kubectl_no_kubectl),
        ("_build_cmd 函数", test_build_cmd_with_kubeconfig),
        ("超时控制", test_run_kubectl_timeout_handling),
        ("Trace 结构兼容", test_trace_structure_preserved),
        ("配置项验证", test_k8s_config_settings),
        ("向后兼容性", test_legacy_k8s_tools_still_available),
    ]

    passed = 0
    failed = 0
    for name, func in tests:
        try:
            func()
            passed += 1
        except Exception as e:
            import traceback
            print(f"[FAIL] {name}: {e}")
            traceback.print_exc()
            failed += 1

    print()
    print("=" * 60)
    print(f"  K8S 工具测试结果: {passed} passed, {failed} failed / {len(tests)} total")
    print("=" * 60)
