#!/usr/bin/env python3
"""
AI-Bridge v3.0 基础使用示例
Basic usage examples for AI-Bridge

这个文件展示了如何直接使用 AI-Bridge 的 Python API，
而不是通过 MCP 协议。适合快速测试和脚本自动化场景。

v3.0 战略定位: MCP + A2A 双协议网关 + CLI 工具适配器
"""

import asyncio
import sys
sys.path.insert(0, '../src')

from aibridge.core.manager import AdapterManager
from aibridge.core.protocol import Request, Target, RequestOptions


async def example_browser_automation():
    """浏览器自动化示例 (Direct Adapter)"""
    print("\n=== 浏览器自动化示例 (Direct Adapter) ===\n")
    
    from aibridge.adapters.browser.chrome import ChromeAdapter, ChromeConfig
    
    # 创建适配器
    config = ChromeConfig(headless=False)
    adapter = ChromeAdapter(config)
    
    try:
        # 连接浏览器
        await adapter.connect()
        print("✓ 浏览器已启动")
        
        # 打开网页
        result = await adapter.execute(
            action="goto",
            target=None,
            value="https://www.baidu.com",
            options={}
        )
        print(f"✓ 打开百度: {result}")
        
        # 等待页面加载
        await asyncio.sleep(1)
        
        # 在搜索框输入
        result = await adapter.execute(
            action="type",
            target=Target(css="#kw"),
            value="AI-Bridge MCP 协议网关",
            options={}
        )
        print(f"✓ 输入搜索内容: {result}")
        
        # 点击搜索按钮
        result = await adapter.execute(
            action="click",
            target=Target(css="#su"),
            value=None,
            options={}
        )
        print(f"✓ 点击搜索: {result}")
        
        # 等待结果
        await asyncio.sleep(2)
        
        # 截图
        result = await adapter.execute(
            action="screenshot",
            target=None,
            value=None,
            options={"path": "baidu_search.png"}
        )
        print(f"✓ 截图保存: {result}")
        
    finally:
        await adapter.disconnect()
        print("✓ 浏览器已关闭")


async def example_gateway_browser():
    """v3.0 协议网关 - 浏览器连接器示例"""
    print("\n=== v3.0 协议网关 - Browser Connector ===\n")
    
    from aibridge.connectors.mcp import BrowserConnector, BrowserConnectorConfig
    from aibridge.connectors.mcp.browser import BrowserBackend
    
    # 创建配置 (自动选择可用后端)
    config = BrowserConnectorConfig(
        name="browser",
        backend=BrowserBackend.AUTO,
        headless=True,
        viewport_width=1280,
        viewport_height=720,
    )
    
    print(f"✓ 浏览器连接器配置:")
    print(f"  - 后端: {config.backend.value}")
    print(f"  - 无头模式: {config.headless}")
    print(f"  - 视口: {config.viewport_width}x{config.viewport_height}")
    
    # 创建连接器
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


async def example_office_word():
    """Word 文档操作示例"""
    print("\n=== Word 文档示例 ===\n")
    
    from aibridge.adapters.office.word import WordAdapter
    from aibridge.core.adapter_config import OfficeConfig
    
    config = OfficeConfig(visible=True)
    adapter = WordAdapter(config)
    
    try:
        # 连接 Word
        await adapter.connect()
        print("✓ Word 已启动")
        
        # 创建新文档
        result = await adapter.execute(
            action="create",
            target=None,
            value=None,
            options={}
        )
        print(f"✓ 新建文档: {result}")
        
        # 写入内容
        result = await adapter.execute(
            action="write",
            target=None,
            value="AI-Bridge v3.0 协议网关报告\n\n这是一份由 AI-Bridge 自动生成的文档。",
            options={}
        )
        print(f"✓ 写入内容: {result}")
        
        # 保存文档
        result = await adapter.execute(
            action="save",
            target=None,
            value="ai_bridge_report.docx",
            options={}
        )
        print(f"✓ 保存文档: {result}")
        
    finally:
        await adapter.disconnect()
        print("✓ Word 已关闭")


async def example_a2a_gateway():
    """v3.0 A2A Gateway Agent 协作示例"""
    print("\n=== v3.0 A2A Gateway Agent 协作 ===\n")
    
    from aibridge.gateway import (
        A2AGateway,
        AgentCard,
        A2ATask,
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
            ),
        ]
    )
    await gateway.register_agent(web_agent)
    print(f"✓ 注册 Agent: {web_agent.name}")
    
    # 列出所有 Agent
    agents = await gateway.list_agents()
    print(f"✓ 已注册的 Agent: {[a.name for a in agents]}")
    
    # 创建任务
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
    
    # 模拟任务完成
    task.complete({"results": ["Result 1", "Result 2"]})
    print(f"\n✓ 任务完成，结果: {task.result}")


async def example_mcp_registry():
    """v3.0 MCP Registry 示例"""
    print("\n=== v3.0 MCP Registry ===\n")
    
    from aibridge.gateway import MCPRegistry, MCPServerConfig
    from aibridge.gateway.mcp_registry import MCPTransport
    
    # 创建注册中心
    registry = MCPRegistry()
    
    # 注册一个 MCP Server（示例配置）
    config = MCPServerConfig(
        name="example-server",
        transport=MCPTransport.STDIO,
        command="echo",
        args=["hello"],
        auto_start=False,
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


def main():
    """运行所有示例"""
    print("=" * 60)
    print("  AI-Bridge v3.0 基础使用示例")
    print("  战略定位: MCP + A2A 双协议网关 + CLI 工具适配器")
    print("=" * 60)
    
    # 选择要运行的示例
    examples = {
        "1": ("浏览器自动化 (Direct Adapter)", example_browser_automation),
        "2": ("v3.0 Browser Connector", example_gateway_browser),
        "3": ("Word 文档", example_office_word),
        "4": ("v3.0 A2A Gateway", example_a2a_gateway),
        "5": ("v3.0 MCP Registry", example_mcp_registry),
    }
    
    print("\n可用示例:")
    for key, (name, _) in examples.items():
        print(f"  {key}. {name}")
    print("  a. 运行所有示例")
    print("  q. 退出")
    
    choice = input("\n请选择示例 (1-5/a/q): ").strip().lower()
    
    if choice == 'q':
        return
    elif choice == 'a':
        for key, (name, func) in examples.items():
            try:
                asyncio.run(func())
            except Exception as e:
                print(f"✗ {name} 出错: {e}")
    elif choice in examples:
        name, func = examples[choice]
        try:
            asyncio.run(func())
        except Exception as e:
            print(f"✗ {name} 出错: {e}")
    else:
        print("无效选择")


if __name__ == "__main__":
    main()
