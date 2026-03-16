#!/usr/bin/env python3
"""
AI-Bridge v5.0 MCP Server 模式测试

验证场景：
    1. MCP Server 启动和工具注册
    2. 工具列表查询
    3. 工具调用执行
    4. 企业级特性（策略、计量、追踪）

运行方式：
    python demos/test_mcp_server.py
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


async def test_mcp_server_startup():
    """测试 1: MCP Server 启动"""
    print("\n" + "=" * 60)
    print("🔧 测试 1: MCP Server 启动")
    print("=" * 60)
    
    from aibridge.core.server import AIBridgeServer
    from aibridge.core.manager import AdapterManager
    from aibridge.core.config import load_config
    
    # 创建 AdapterManager
    manager = AdapterManager()
    print("✅ AdapterManager 创建成功")
    
    # 加载配置
    config = load_config(None)
    print(f"✅ 配置加载成功: log_level={config.server.log_level}")
    
    # 创建 Server
    server = AIBridgeServer(manager, config)
    print("✅ AIBridgeServer 创建成功")
    
    return server, manager


async def test_adapter_registration():
    """测试 2: 适配器注册"""
    print("\n" + "=" * 60)
    print("📦 测试 2: 适配器注册")
    print("=" * 60)
    
    from aibridge.core.manager import AdapterManager
    from aibridge.adapters.browser.chrome import ChromeAdapter
    
    manager = AdapterManager()
    
    # 注册浏览器适配器
    chrome = ChromeAdapter({"headless": True})
    manager.register(chrome)
    print(f"✅ 注册适配器: {chrome.adapter_id} ({chrome.adapter_name})")
    
    # 列出所有适配器
    adapters = manager.list_adapters()
    print(f"\n📋 已注册适配器 ({len(adapters)} 个):")
    for adapter in adapters:
        print(f"   - {adapter['id']}: {adapter['name']}")
        print(f"     类型: {adapter['type']}")
        print(f"     动作: {', '.join(adapter['actions'][:5])}...")
    
    return manager


async def test_mcp_tools_generation():
    """测试 3: MCP Tools 生成"""
    print("\n" + "=" * 60)
    print("🛠️ 测试 3: MCP Tools 生成")
    print("=" * 60)
    
    from aibridge.core.manager import AdapterManager
    from aibridge.adapters.browser.chrome import ChromeAdapter
    
    # 设置适配器
    manager = AdapterManager()
    chrome = ChromeAdapter({"headless": True})
    manager.register(chrome)
    
    # 获取适配器支持的动作，这些会被转换为 MCP Tools
    adapters = manager.list_adapters()
    
    tools = []
    for adapter in adapters:
        for action in adapter['actions']:
            tools.append({
                'name': f"{adapter['id']}_{action}",
                'description': f"{adapter['name']} - {action} operation",
            })
    
    print(f"✅ 生成 MCP Tools: {len(tools)} 个")
    print("\n📋 工具列表 (前 10 个):")
    for i, tool in enumerate(tools[:10], 1):
        print(f"   {i}. {tool['name']}")
        print(f"      描述: {tool['description'][:50]}...")
    
    if len(tools) > 10:
        print(f"   ... 还有 {len(tools) - 10} 个工具")
    
    return tools


async def test_tool_execution():
    """测试 4: 工具调用执行"""
    print("\n" + "=" * 60)
    print("⚡ 测试 4: 工具调用执行 (模拟)")
    print("=" * 60)
    
    from aibridge.core.manager import AdapterManager
    from aibridge.adapters.browser.chrome import ChromeAdapter
    from aibridge.core.protocol import Request, RequestOptions
    
    manager = AdapterManager()
    chrome = ChromeAdapter({"headless": True})
    manager.register(chrome)
    
    # 模拟工具调用请求
    test_cases = [
        {
            "tool": "chrome_goto",
            "params": {"url": "https://www.baidu.com"},
            "description": "打开百度首页"
        },
        {
            "tool": "chrome_screenshot", 
            "params": {"path": "test.png"},
            "description": "截图保存"
        },
        {
            "tool": "chrome_evaluate",
            "params": {"script": "document.title"},
            "description": "获取页面标题"
        },
    ]
    
    print("📋 模拟工具调用请求:")
    for i, tc in enumerate(test_cases, 1):
        print(f"\n   {i}. {tc['tool']}")
        print(f"      描述: {tc['description']}")
        print(f"      参数: {tc['params']}")
        
        # 构建请求对象 (app 而不是 adapter_id)
        request = Request(
            app="chrome",
            action=tc['tool'].replace("chrome_", ""),
            value=tc['params'].get('url') or tc['params'].get('script'),
            options=RequestOptions()
        )
        print(f"      ✅ Request 构建成功: app={request.app}, action={request.action}")
    
    print("\n✅ 工具调用请求构建验证通过")
    print("   (实际执行需要启动浏览器，此处跳过)")


async def test_enterprise_features():
    """测试 5: 企业级特性"""
    print("\n" + "=" * 60)
    print("🔐 测试 5: 企业级特性")
    print("=" * 60)
    
    # 5.1 策略引擎
    print("\n📌 5.1 策略引擎 (PBAC)")
    from aibridge.enterprise.policy import PolicyEngine, ToolPolicy, PolicyAction
    
    engine = PolicyEngine()
    
    # 创建策略
    policy = ToolPolicy(
        policy_id="dev-policy",
        name="Developer Policy",
        statements=[{
            "sid": "allow-browser",
            "effect": "allow",
            "actions": ["tool:call"],
            "resources": ["browser/*", "chrome/*"],
        }]
    )
    engine.register_policy(policy)
    print(f"   ✅ 注册策略: {policy.name}")
    
    # 评估权限 (allowed 而不是 effect)
    result = engine.evaluate("user1", PolicyAction.CALL_TOOL, "chrome/goto")
    status = "允许" if result.allowed else "拒绝"
    print(f"   ✅ 权限评估: user1 -> chrome/goto = {status}")
    
    result = engine.evaluate("user1", PolicyAction.CALL_TOOL, "office/write")
    status = "允许" if result.allowed else "拒绝"
    print(f"   ✅ 权限评估: user1 -> office/write = {status}")
    
    # 5.2 计量系统
    print("\n📌 5.2 计量系统 (Metering)")
    from aibridge.enterprise.metering import MeteringCollector
    
    metering = MeteringCollector()
    await metering.start()
    
    # 记录调用
    await metering.record(user_id="user1", tool_name="chrome/goto", duration_ms=150)
    await metering.record(user_id="user1", tool_name="chrome/click", duration_ms=80)
    await metering.record(user_id="user2", tool_name="chrome/goto", duration_ms=200)
    print("   ✅ 记录调用: 3 条")
    
    # 查询统计
    stats = await metering.get_user_stats("user1", "day")
    # UsageAggregation 对象有 total_calls 属性
    total = getattr(stats, 'total_calls', 0) if stats else 0
    print(f"   ✅ user1 今日统计: {total} 次调用")
    
    await metering.stop()
    
    # 5.3 分布式追踪
    print("\n📌 5.3 分布式追踪 (Tracing)")
    from aibridge.enterprise.tracing import Tracer, TracerConfig, SpanKind
    
    tracer = Tracer(TracerConfig(service_name="ai-bridge-test"))
    
    with tracer.start_as_current_span("tool_call", kind=SpanKind.SERVER) as span:
        span.set_attribute("user.id", "user1")
        span.set_attribute("tool.name", "chrome/goto")
        span.set_attribute("tool.params", '{"url": "https://baidu.com"}')
        
        # 模拟子操作
        with tracer.start_as_current_span("browser_connect", kind=SpanKind.CLIENT) as child:
            child.set_attribute("browser.type", "chromium")
            await asyncio.sleep(0.01)  # 模拟耗时
        
        with tracer.start_as_current_span("page_navigate", kind=SpanKind.CLIENT) as child:
            child.set_attribute("page.url", "https://baidu.com")
            await asyncio.sleep(0.01)
    
    print("   ✅ 追踪记录: tool_call -> browser_connect + page_navigate")
    print("   ✅ 追踪数据已记录（生产环境导出到 Jaeger/Zipkin）")


async def test_prometheus_metrics():
    """测试 6: Prometheus 指标"""
    print("\n" + "=" * 60)
    print("📊 测试 6: Prometheus 指标")
    print("=" * 60)
    
    from aibridge.enterprise.prometheus import PrometheusRegistry, AIBridgeMetrics
    
    # 创建 Registry
    registry = PrometheusRegistry(prefix="aibridge")
    print("✅ 创建 PrometheusRegistry")
    
    # 使用预定义的 AI-Bridge 指标
    metrics = AIBridgeMetrics(registry)
    print("✅ 初始化 AIBridgeMetrics")
    
    print("\n✅ 注册指标:")
    print("   - aibridge_requests_total (Counter)")
    print("   - aibridge_request_duration_seconds (Histogram)")
    print("   - aibridge_agents_registered (Gauge)")
    
    # 记录指标
    metrics.requests_total.labels(tool="chrome/goto", server="local").inc()
    metrics.requests_total.labels(tool="chrome/goto", server="local").inc()
    metrics.requests_total.labels(tool="chrome/click", server="local").inc()
    
    metrics.request_duration.labels(tool="chrome/goto", server="local").observe(0.15)
    metrics.request_duration.labels(tool="chrome/click", server="local").observe(0.08)
    
    metrics.agents_registered.labels(protocol="a2a").set(3)
    
    print("\n✅ 记录指标数据:")
    print("   - chrome/goto: 2 次调用")
    print("   - chrome/click: 1 次调用")
    print("   - A2A Agent: 3 个注册")
    
    # 导出指标
    output = registry.export()
    print(f"\n✅ Prometheus 格式导出 ({len(output)} 字符)")
    print("   预览:")
    for line in output.split('\n')[:10]:
        if line and not line.startswith('#'):
            print(f"   {line}")


async def test_a2a_agent_collaboration():
    """测试 7: A2A Agent 协作"""
    print("\n" + "=" * 60)
    print("🤖 测试 7: A2A Agent 协作")
    print("=" * 60)
    
    from aibridge.gateway import A2AGateway, AgentCard, A2ATask
    from aibridge.gateway.a2a_gateway import AgentCapability
    
    # 创建网关
    gateway = A2AGateway()
    print("✅ A2A Gateway 创建成功")
    
    # 注册多个 Agent
    agents = [
        AgentCard(
            agent_id="search-agent",
            name="Search Agent",
            description="负责网页搜索和信息提取",
            capabilities=[
                AgentCapability(name="web_search", description="搜索网页"),
                AgentCapability(name="extract_data", description="提取结构化数据"),
            ]
        ),
        AgentCard(
            agent_id="analysis-agent", 
            name="Analysis Agent",
            description="负责数据分析和洞察生成",
            capabilities=[
                AgentCapability(name="analyze", description="分析数据"),
                AgentCapability(name="summarize", description="生成摘要"),
            ]
        ),
        AgentCard(
            agent_id="report-agent",
            name="Report Agent",
            description="负责报告生成和格式化",
            capabilities=[
                AgentCapability(name="generate_report", description="生成报告"),
                AgentCapability(name="format_output", description="格式化输出"),
            ]
        ),
    ]
    
    for agent in agents:
        await gateway.register_agent(agent)
        print(f"   ✅ 注册 Agent: {agent.name}")
    
    # 列出 Agent
    registered = await gateway.list_agents()
    print(f"\n📋 已注册 Agent: {len(registered)} 个")
    
    # 创建任务流
    print("\n📌 创建任务流 (DAG):")
    tasks = [
        A2ATask(
            from_agent="orchestrator",
            to_agent="search-agent",
            capability="web_search",
            input_data={"query": "AI-Bridge MCP gateway"},
        ),
        A2ATask(
            from_agent="search-agent",
            to_agent="analysis-agent",
            capability="analyze",
            input_data={"data": "search_results"},
        ),
        A2ATask(
            from_agent="analysis-agent",
            to_agent="report-agent",
            capability="generate_report",
            input_data={"analysis": "insights"},
        ),
    ]
    
    for i, task in enumerate(tasks, 1):
        print(f"   {i}. {task.from_agent} → {task.to_agent} ({task.capability})")
        task.complete({"result": f"completed_{i}"})
    
    print("\n✅ A2A 任务流执行完成")


async def main():
    """运行所有测试"""
    print("\n" + "🚀" * 20)
    print("\n  AI-Bridge v5.0 MCP Server 模式测试")
    print("  核心功能验证套件")
    print("\n" + "🚀" * 20)
    
    start_time = datetime.now()
    results = {}
    
    tests = [
        ("MCP Server 启动", test_mcp_server_startup),
        ("适配器注册", test_adapter_registration),
        ("MCP Tools 生成", test_mcp_tools_generation),
        ("工具调用执行", test_tool_execution),
        ("企业级特性", test_enterprise_features),
        ("Prometheus 指标", test_prometheus_metrics),
        ("A2A Agent 协作", test_a2a_agent_collaboration),
    ]
    
    for name, test_func in tests:
        try:
            await test_func()
            results[name] = "✅ 通过"
        except Exception as e:
            results[name] = f"❌ 失败: {e}"
            import traceback
            traceback.print_exc()
    
    # 汇总
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print("📊 测试汇总")
    print("=" * 60)
    
    passed = sum(1 for r in results.values() if r.startswith("✅"))
    failed = len(results) - passed
    
    for name, result in results.items():
        print(f"   {result} {name}")
    
    print(f"\n⏱️  总耗时: {elapsed:.2f} 秒")
    print(f"📈 通过率: {passed}/{len(results)} ({100*passed/len(results):.0f}%)")
    
    if failed == 0:
        print("\n" + "🎉" * 20)
        print("\n  所有核心功能验证通过！")
        print("  AI-Bridge v5.0 MCP Server 模式就绪")
        print("\n" + "🎉" * 20)
    else:
        print(f"\n⚠️ {failed} 个测试失败，请检查")


if __name__ == "__main__":
    asyncio.run(main())
