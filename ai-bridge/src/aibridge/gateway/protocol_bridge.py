"""
协议桥接器

实现 MCP ↔ A2A 协议互转：
- 将 MCP Tool 暴露为 A2A Agent 能力
- 让 A2A Agent 可以调用 MCP Tool
- 统一的调用接口
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .mcp_registry import MCPRegistry, ToolSchema
from .a2a_gateway import (
    A2AGateway, 
    AgentCard, 
    AgentCapability, 
    A2ATask, 
    TaskStatus
)

logger = logging.getLogger(__name__)


@dataclass
class BridgeConfig:
    """桥接配置"""
    auto_expose_mcp_as_a2a: bool = True  # 自动将 MCP Tool 暴露为 A2A 能力
    mcp_agent_prefix: str = "mcp-"       # MCP 转 A2A 时的 Agent ID 前缀


class ProtocolBridge:
    """
    协议桥接器
    
    连接 MCP 和 A2A 两个协议世界，实现互操作：
    
    1. MCP → A2A: 将 MCP Server 的 Tool 暴露为 A2A Agent 的能力
       - 每个 MCP Server 对应一个虚拟 A2A Agent
       - MCP Tool 对应 A2A Capability
       
    2. A2A → MCP: 让 A2A 任务可以调用 MCP Tool
       - A2A 任务路由到对应的 MCP Server
       - 结果转换回 A2A 格式
    
    使用示例：
    ```python
    mcp_registry = MCPRegistry()
    a2a_gateway = A2AGateway()
    bridge = ProtocolBridge(mcp_registry, a2a_gateway)
    
    # 将所有 MCP Server 暴露为 A2A Agent
    await bridge.expose_all_mcp_as_a2a()
    
    # 现在可以通过 A2A 协议调用 MCP Tool
    task = A2ATask(
        from_agent="orchestrator",
        to_agent="mcp-browser-use",  # 虚拟 Agent
        capability="navigate",
        input_data={"url": "https://example.com"}
    )
    handle = await a2a_gateway.send_task(task)
    ```
    """
    
    def __init__(
        self, 
        mcp_registry: MCPRegistry, 
        a2a_gateway: A2AGateway,
        config: Optional[BridgeConfig] = None
    ):
        self._mcp = mcp_registry
        self._a2a = a2a_gateway
        self._config = config or BridgeConfig()
        self._mcp_agents: Dict[str, str] = {}  # mcp_server_name -> a2a_agent_id
    
    def mcp_to_a2a_capability(self, tool: ToolSchema) -> AgentCapability:
        """
        将 MCP Tool 转换为 A2A 能力描述
        
        Args:
            tool: MCP Tool Schema
            
        Returns:
            AgentCapability: A2A 能力描述
        """
        return AgentCapability(
            name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema,
            output_schema=None,  # MCP 通常不定义输出 schema
        )
    
    def mcp_server_to_a2a_agent(self, server_name: str, tools: List[ToolSchema]) -> AgentCard:
        """
        将 MCP Server 转换为 A2A Agent
        
        Args:
            server_name: MCP Server 名称
            tools: Server 提供的工具列表
            
        Returns:
            AgentCard: A2A Agent 名片
        """
        agent_id = f"{self._config.mcp_agent_prefix}{server_name}"
        
        return AgentCard(
            agent_id=agent_id,
            name=f"MCP: {server_name}",
            description=f"A2A Agent bridged from MCP Server '{server_name}'",
            capabilities=[self.mcp_to_a2a_capability(tool) for tool in tools],
            metadata={
                "bridge_type": "mcp_to_a2a",
                "mcp_server": server_name,
            }
        )
    
    async def expose_mcp_as_a2a(self, server_name: str) -> Optional[AgentCard]:
        """
        将指定 MCP Server 暴露为 A2A Agent
        
        Args:
            server_name: MCP Server 名称
            
        Returns:
            创建的 AgentCard，如果 Server 不存在则返回 None
        """
        proxy = await self._mcp.get(server_name)
        if not proxy:
            logger.warning(f"MCP Server {server_name} not found")
            return None
        
        if not proxy.is_connected:
            logger.warning(f"MCP Server {server_name} is not connected")
            return None
        
        # 获取工具列表
        tools = await proxy.list_tools()
        
        # 创建虚拟 Agent
        agent_card = self.mcp_server_to_a2a_agent(server_name, tools)
        
        # 注册到 A2A Gateway
        await self._a2a.register_agent(agent_card)
        
        # 记录映射
        self._mcp_agents[server_name] = agent_card.agent_id
        
        logger.info(f"Exposed MCP Server {server_name} as A2A Agent {agent_card.agent_id}")
        return agent_card
    
    async def expose_all_mcp_as_a2a(self) -> List[AgentCard]:
        """
        将所有 MCP Server 暴露为 A2A Agent
        
        Returns:
            创建的 AgentCard 列表
        """
        cards = []
        for server_name in await self._mcp.list_servers():
            card = await self.expose_mcp_as_a2a(server_name)
            if card:
                cards.append(card)
        return cards
    
    def a2a_task_to_mcp_call(self, task: A2ATask) -> Dict[str, Any]:
        """
        将 A2A 任务转换为 MCP 调用参数
        
        Args:
            task: A2A 任务
            
        Returns:
            MCP 调用参数 {"server": str, "tool": str, "params": dict}
        """
        # 检查是否是 MCP 桥接的 Agent
        agent_id = task.to_agent
        if not agent_id.startswith(self._config.mcp_agent_prefix):
            raise ValueError(f"Agent {agent_id} is not a bridged MCP agent")
        
        # 提取 MCP Server 名称
        server_name = agent_id[len(self._config.mcp_agent_prefix):]
        
        return {
            "server": server_name,
            "tool": task.capability,
            "params": task.input_data,
        }
    
    async def route_a2a_to_mcp(self, task: A2ATask) -> Any:
        """
        将 A2A 任务路由到 MCP Server 执行
        
        Args:
            task: A2A 任务
            
        Returns:
            执行结果
        """
        # 转换参数
        mcp_call = self.a2a_task_to_mcp_call(task)
        
        # 调用 MCP Tool
        result = await self._mcp.call_tool(
            mcp_call["server"],
            mcp_call["tool"],
            mcp_call["params"]
        )
        
        return result
    
    async def execute_task(self, task: A2ATask) -> Any:
        """
        执行任务（自动判断路由）
        
        Args:
            task: A2A 任务
            
        Returns:
            执行结果
        """
        # 检查目标 Agent 是否是 MCP 桥接的
        if task.to_agent.startswith(self._config.mcp_agent_prefix):
            # 路由到 MCP
            return await self.route_a2a_to_mcp(task)
        else:
            # 原生 A2A Agent，使用 A2A Gateway
            handle = await self._a2a.send_task(task)
            return await handle.wait_for_completion()
    
    def get_bridge_status(self) -> Dict[str, Any]:
        """获取桥接状态"""
        return {
            "mcp_agents": self._mcp_agents,
            "config": {
                "auto_expose": self._config.auto_expose_mcp_as_a2a,
                "prefix": self._config.mcp_agent_prefix,
            }
        }
