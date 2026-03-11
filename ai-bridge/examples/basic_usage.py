#!/usr/bin/env python3
"""
AI-Bridge 基础使用示例
Basic usage examples for AI-Bridge

这个文件展示了如何直接使用 AI-Bridge 的 Python API，
而不是通过 MCP 协议。适合快速测试和脚本自动化场景。
"""

import asyncio
import sys
sys.path.insert(0, '../src')

from aibridge.core.manager import AdapterManager
from aibridge.core.protocol import Request, Target, RequestOptions


async def example_browser_automation():
    """浏览器自动化示例"""
    print("\n=== 浏览器自动化示例 ===\n")
    
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
            value="AI-Bridge 自动化框架",
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


async def example_feishu_message():
    """飞书发送消息示例"""
    print("\n=== 飞书消息示例 ===\n")
    
    from aibridge.adapters.im.feishu import FeishuAdapter, FeishuConfig
    
    # 配置飞书应用凭证 (需要替换为真实值)
    config = FeishuConfig(
        app_id="your_app_id",
        app_secret="your_app_secret"
    )
    adapter = FeishuAdapter(config)
    
    try:
        # 连接飞书
        connected = await adapter.connect()
        if not connected:
            print("✗ 飞书连接失败，请检查凭证")
            return
        print("✓ 飞书已连接")
        
        # 发送消息到群聊
        result = await adapter.execute(
            action="send_message",
            target=Target(name="oc_xxx"),  # 群聊 chat_id
            value="Hello from AI-Bridge! 🚀",
            options={}
        )
        print(f"✓ 消息发送结果: {result}")
        
    finally:
        await adapter.disconnect()
        print("✓ 飞书已断开")


async def example_office_word():
    """Word 文档操作示例"""
    print("\n=== Word 文档示例 ===\n")
    
    from aibridge.adapters.office.word import WordAdapter, WordConfig
    
    config = WordConfig(visible=True)
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
            value="AI-Bridge 自动化报告\n\n这是一份由 AI-Bridge 自动生成的文档。",
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


async def example_adapter_manager():
    """使用 AdapterManager 统一管理示例"""
    print("\n=== AdapterManager 统一管理示例 ===\n")
    
    from aibridge.adapters.browser.chrome import ChromeAdapter, ChromeConfig
    
    manager = AdapterManager()
    
    # 注册适配器
    chrome_config = ChromeConfig(headless=True)
    manager.register(ChromeAdapter(chrome_config))
    print("✓ 注册 Chrome 适配器")
    
    # 列出所有适配器
    adapters = manager.list_adapters()
    print(f"✓ 已注册适配器: {[a.info.name for a in adapters]}")
    
    # 获取特定适配器
    chrome = manager.get("chrome")
    if chrome:
        await chrome.connect()
        print("✓ 通过 Manager 获取并连接 Chrome")
        
        # 执行操作
        result = await manager.execute(
            app="chrome",
            action="goto",
            target=None,
            value="https://github.com",
            options={}
        )
        print(f"✓ 打开 GitHub: {result}")
        
        await chrome.disconnect()
    
    print("✓ 示例完成")


async def example_mcp_server():
    """启动 MCP Server 示例"""
    print("\n=== MCP Server 示例 ===\n")
    
    from aibridge.core.server import AIBridgeServer
    from aibridge.core.manager import AdapterManager
    from aibridge.adapters.browser.chrome import ChromeAdapter, ChromeConfig
    
    # 创建管理器并注册适配器
    manager = AdapterManager()
    manager.register(ChromeAdapter(ChromeConfig(headless=True)))
    
    # 创建 MCP Server
    server = AIBridgeServer(manager)
    
    # 获取可用工具列表
    tools = server.get_tools()
    print("✓ MCP 工具列表:")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description'][:50]}...")
    
    # 模拟工具调用
    result = await server.handle_tool_call(
        name="aibridge_interact",
        arguments={
            "app": "chrome",
            "action": "goto",
            "value": "https://www.bing.com"
        }
    )
    print(f"✓ 工具调用结果: {result}")
    
    # 如果要启动真正的 MCP Server (会阻塞):
    # await server.run_stdio()


def main():
    """运行所有示例"""
    print("=" * 50)
    print("AI-Bridge 基础使用示例")
    print("=" * 50)
    
    # 选择要运行的示例
    examples = {
        "1": ("浏览器自动化", example_browser_automation),
        "2": ("飞书消息", example_feishu_message),
        "3": ("Word 文档", example_office_word),
        "4": ("AdapterManager", example_adapter_manager),
        "5": ("MCP Server", example_mcp_server),
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
