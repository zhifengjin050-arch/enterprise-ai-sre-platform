"""Agent 测试 — Tool Calling 流程"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def _print_separator(title: str):
    print()
    print("=" * 70)
    print(f"  测试: {title}")
    print("=" * 70)


def _run_test(question: str):
    from app.agent.graph import create_agent_graph

    graph = create_agent_graph()

    initial_state = {
        "messages": [{"role": "user", "content": question}],
        "tool_calls": [],
        "tool_results": [],
        "final_report": "",
    }

    result = graph.invoke(initial_state)

    print(f"  用户: {question}")
    print()

    tool_calls = result.get("tool_calls", [])
    if tool_calls and any(tc.get("tool") for tc in tool_calls):
        print(f"  [工具调用]")
        for tc in tool_calls:
            tool_name = tc.get("tool", "N/A")
            tool_success = tc.get("success", False)
            status = "OK" if tool_success else "FAIL"
            print(f"    -> {tool_name}() [{status}]")
            tool_result = tc.get("result", "")
            if tool_result and len(tool_result) < 200:
                print(f"       结果: {tool_result}")
            elif tool_result:
                print(f"       结果: {tool_result[:200]}...")
    else:
        print(f"  [直接回答 - 未调用工具]")

    final = result.get("final_report", "")
    if final:
        preview = final[:300]
        print(f"\n  [最终输出预览]")
        print(f"    {preview}...")
    else:
        print(f"\n  [等待第二轮总结中...]")

    return result


def test_greeting_no_tool():
    """测试1: 打招呼 -> 不应调用工具"""
    _print_separator("用户打招呼 -> 不应调用工具")
    result = _run_test("你好，请问你能做什么？")
    tool_calls = result.get("tool_calls", [])
    tool_names = [tc.get("tool", "") for tc in tool_calls if tc.get("tool")]
    assert len(tool_names) == 0, f"打招呼不应调用工具 (实际调用了: {tool_names})"
    print(f"\n  >>> 断言通过: 未调用工具 ✓")
    final = result.get("final_report", "")
    assert len(final) > 50, "直接回答应包含详细回复内容"
    print(f"  >>> 断言通过: 直接回答内容完整 ✓")


def test_server_health_tool():
    """测试2: 服务器状态 -> 应至少调用工具"""
    _print_separator("用户请求服务器状态 -> 应至少调用一个工具")
    result = _run_test("帮我检查一下服务器的健康状态")
    tool_calls = result.get("tool_calls", [])
    tool_names = [tc.get("tool", "") for tc in tool_calls if tc.get("tool")]
    assert len(tool_names) > 0, f"应调用至少一个工具 (实际调用了: {tool_names})"
    print(f"\n  >>> 断言通过: 至少一个工具被调用 ✓")


def test_docker_query():
    """测试3: 用户询问Docker相关问题 -> 应最终能给出报告"""
    _print_separator("用户查看容器日志 -> Agent 应给出报告")
    result = _run_test("帮我看看 nginx 容器的日志")
    final = result.get("final_report", "")
    assert len(final) > 50, f"应返回最终报告 (实际长度: {len(final)})"
    print(f"\n  >>> 断言通过: Agent 生成了响应报告 ✓")


if __name__ == "__main__":
    print("=" * 70)
    print("  LangGraph Tool Calling Agent 测试")
    print("=" * 70)

    test_greeting_no_tool()
    test_server_health_tool()
    test_docker_query()

    print()
    print("=" * 70)
    print("  全部测试通过！")
    print("=" * 70)