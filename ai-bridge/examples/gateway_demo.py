"""
AI-Bridge v3.0 协议网关示例

演示 MCP + A2A 双协议网关的使用方式。

运行方式：
    python -m examples.gateway_demo

注意：需要先安装 browser-use 或其他 MCP Server
    npm install -g @anthropic-ai/browser-use-mcp
"""

import asyncio
import logging
from typing import Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def demo_mcp_registry():
    """
    演示 1: MCP Registry 基础使用
    
    展示如何注册和管理 MCP Server
    """
    print("\n" + "=" * 60)
    print("演示 1: MCP Registry 基础使用")
    print("=" * 60)
    
    from aibridge.gateway import MCPRegistry, MCPServerConfig
    from aibridge.gateway.mcp_registry import MCPTransport
    
    # 创建注册中心
    registry = MCPRegistry()
    
    # 注册一个 MCP Server（示例配置）
    config = MCPServerConfig(
        name="example-server",
        transport=MCPTransport.STDIO,
        command="echo",  # 示例命令
        args=["hello"],
        auto_start=False,  # 不自动启动（因为这只是演示）
    )
    
    proxy = await registry.register(config)
    print(f"✓ 注册 MCP Server: {config.name}")
    
    # 列出已注册的 Server
    servers = await registry.list_servers()
    print(f"✓ 已注册的 Server: {servers}")
    
    # 获取状态
    status = registry.get_server_status()
    print(f"✓ Server 状态: {status}")
    
    # 注销
    await registry.unregister("example-server")
    print(f"✓ 注销 MCP Server: example-server")


async def demo_a2a_gateway():
    """
    演示 2: A2A Gateway Agent 协作
    
    展示如何注册 Agent 和发送任务
    """
    print("\n" + "=" * 60)
    print("演示 2: A2A Gateway Agent 协作")
    print("=" * 60)
    
    from aibridge.gateway import (
        A2AGateway,
        AgentCard,
        A2ATask,
        TaskStatus,
    )
    from aibridge.gateway.a2a_gateway import AgentCapability
    
    # 创建 A2A 网关
    gateway = A2AGateway()
    
    # 注册 Web 搜索 Agent
    web_agent = AgentCard(
        agent_id="web-search-agent",
        name="Web Search Agent",
        description="专门负责网页搜索和信息提取",
        capabilities=[
            AgentCapability(
                name="search",
                description="在网上搜索信息",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    }
                }
            ),
            AgentCapability(
                name="extract",
                description="从网页提取结构化数据",
            ),
        ]
    )
    await gateway.register_agent(web_agent)
    print(f"✓ 注册 Agent: {web_agent.name}")
    
    # 注册数据处理 Agent
    data_agent = AgentCard(
        agent_id="data-processor-agent",
        name="Data Processor Agent",
        description="专门负责数据处理和分析",
        capabilities=[
            AgentCapability(
                name="analyze",
                description="分析数据",
            ),
            AgentCapability(
                name="transform",
                description="转换数据格式",
            ),
        ]
    )
    await gateway.register_agent(data_agent)
    print(f"✓ 注册 Agent: {data_agent.name}")
    
    # 列出所有 Agent
    agents = await gateway.list_agents()
    print(f"✓ 已注册的 Agent: {[a.name for a in agents]}")
    
    # 发现具备 "search" 能力的 Agent
    search_agents = await gateway.discover_agents("search")
    print(f"✓ 具备 'search' 能力的 Agent: {[a.name for a in search_agents]}")
    
    # 创建并发送任务
    task = A2ATask(
        from_agent="orchestrator",
        to_agent="web-search-agent",
        capability="search",
        input_data={"query": "AI-Bridge MCP gateway"},
    )
    
    print(f"\n创建任务:")
    print(f"  - Task ID: {task.task_id}")
    print(f"  - From: {task.from_agent}")
    print(f"  - To: {task.to_agent}")
    print(f"  - Capability: {task.capability}")
    print(f"  - Input: {task.input_data}")
    
    # 模拟任务完成
    task.complete({"results": ["Result 1", "Result 2"]})
    print(f"\n✓ 任务完成，结果: {task.result}")


async def demo_browser_connector():
    """
    演示 3: Browser Connector 使用
    
    展示如何使用浏览器连接器（需要安装 browser-use）
    """
    print("\n" + "=" * 60)
    print("演示 3: Browser Connector 配置")
    print("=" * 60)
    
    from aibridge.connectors.mcp import BrowserConnector, BrowserConnectorConfig
    from aibridge.connectors.mcp.browser import BrowserBackend
    
    # 创建配置
    config = BrowserConnectorConfig(
        name="browser",
        backend=BrowserBackend.AUTO,  # 自动选择可用后端
        headless=True,
        viewport_width=1280,
        viewport_height=720,
    )
    
    print(f"✓ 浏览器连接器配置:")
    print(f"  - 后端: {config.backend.value}")
    print(f"  - 无头模式: {config.headless}")
    print(f"  - 视口: {config.viewport_width}x{config.viewport_height}")
    
    # 创建连接器（不实际启动）
    connector = BrowserConnector(config)
    print(f"✓ 连接器创建成功")
    print(f"  - 状态: {connector.status.value}")
    
    # 检测可用后端
    print(f"\n检测可用的浏览器后端...")
    backend = await connector._detect_available_backend()
    if backend:
        print(f"✓ 检测到可用后端: {backend.value}")
    else:
        print("✗ 未检测到可用后端")
        print("  提示: 请安装以下任一 MCP Server:")
        print("    npm install -g @anthropic-ai/browser-use-mcp")
        print("    npm install -g @anthropic-ai/mcp-server-chrome-devtools")
        print("    npm install -g @anthropic-ai/mcp-server-playwright")


async def demo_protocol_bridge():
    """
    演示 4: Protocol Bridge MCP ↔ A2A
    
    展示如何将 MCP Server 暴露为 A2A Agent
    """
    print("\n" + "=" * 60)
    print("演示 4: Protocol Bridge MCP ↔ A2A 桥接")
    print("=" * 60)
    
    from aibridge.gateway import (
        MCPRegistry,
        A2AGateway,
        ProtocolBridge,
    )
    from aibridge.gateway.mcp_registry import MCPTransport, MCPServerConfig
    from aibridge.gateway.protocol_bridge import BridgeConfig
    
    # 创建组件
    mcp_registry = MCPRegistry()
    a2a_gateway = A2AGateway()
    
    # 创建桥接器
    bridge = ProtocolBridge(
        mcp_registry=mcp_registry,
        a2a_gateway=a2a_gateway,
        config=BridgeConfig(
            auto_expose_mcp_as_a2a=True,
            mcp_agent_prefix="mcp-",
        )
    )
    
    print(f"✓ Protocol Bridge 创建成功")
    print(f"  - MCP Agent 前缀: {bridge._config.mcp_agent_prefix}")
    
    # 获取桥接状态
    status = bridge.get_bridge_status()
    print(f"  - 桥接状态: {status}")


async def demo_service_discovery():
    """
    演示 5: Service Discovery 服务发现
    
    展示服务发现和健康检查
    """
    print("\n" + "=" * 60)
    print("演示 5: Service Discovery 服务发现")
    print("=" * 60)
    
    from aibridge.gateway import ServiceDiscovery
    from aibridge.gateway.discovery import ServiceInfo, ServiceStatus
    
    # 创建服务发现
    discovery = ServiceDiscovery()
    
    # 注册服务
    discovery.register_service(ServiceInfo(
        name="browser-mcp",
        type="mcp",
        status=ServiceStatus.HEALTHY,
        check_interval=30.0,
    ))
    
    discovery.register_service(ServiceInfo(
        name="web-agent",
        type="a2a",
        status=ServiceStatus.HEALTHY,
        check_interval=60.0,
    ))
    
    print(f"✓ 注册服务完成")
    
    # 获取所有服务
    services = discovery.get_all_services()
    for svc in services:
        print(f"  - {svc.name} ({svc.type}): {svc.status.value}")
    
    # 获取健康的服务
    healthy = discovery.get_healthy_services()
    print(f"\n✓ 健康的服务: {[s.name for s in healthy]}")
    
    # 获取状态摘要
    summary = discovery.get_status_summary()
    print(f"✓ 状态摘要: {summary['total']} 总计, {summary['healthy']} 健康")


async def main():
    """运行所有演示"""
    print("\n" + "=" * 60)
    print("  AI-Bridge v3.0 协议网关演示")
    print("  MCP + A2A 双协议统一入口")
    print("=" * 60)
    
    try:
        await demo_mcp_registry()
        await demo_a2a_gateway()
        await demo_browser_connector()
        await demo_protocol_bridge()
        await demo_service_discovery()
        
        print("\n" + "=" * 60)
        print("  所有演示完成!")
        print("=" * 60)
        print("\n下一步:")
        print("  1. 安装 MCP Server: npm install -g @anthropic-ai/browser-use-mcp")
        print("  2. 运行实际的浏览器自动化")
        print("  3. 探索 A2A 多 Agent 协作")
        
    except Exception as e:
        logger.error(f"演示出错: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
